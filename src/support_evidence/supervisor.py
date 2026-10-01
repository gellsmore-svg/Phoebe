"""Trusted-worker isolation: deadline, output cap and process-group cancellation."""
import json
import os
import selectors
import signal
import subprocess
import sys
import time
from .model import canonical, observation, validate

class WorkerError(Exception): pass

def supervise(argv, request, timeout, env=None, output_limit=65536):
    start=time.monotonic()
    proc=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env=env)
    sel=selectors.DefaultSelector(); data=bytearray(); total=0
    try:
        payload=(canonical(request)+"\n").encode()
        if len(payload)>65536:raise WorkerError("request_too_large")
        # Requests are small; the bundled worker immediately reads stdin. A trusted
        # arbitrary plugin must obey the same protocol; non-reading input is also bounded.
        os.set_blocking(proc.stdin.fileno(),False)
        pending=memoryview(payload)
        sel.register(proc.stdin,selectors.EVENT_WRITE,"input")
        for stream in [proc.stdout,proc.stderr]:
            os.set_blocking(stream.fileno(),False);sel.register(stream,selectors.EVENT_READ,"stdout" if stream==proc.stdout else "stderr")
        while sel.get_map():
            remaining=timeout-(time.monotonic()-start)
            if remaining<=0:raise WorkerError("worker_timeout")
            for key,_ in sel.select(min(remaining,0.05)):
                if key.data=="input":
                    try:n=os.write(key.fd,pending)
                    except BrokenPipeError:n=len(pending)
                    pending=pending[n:]
                    if not pending:sel.unregister(key.fileobj);key.fileobj.close()
                    continue
                chunk=os.read(key.fd,8192)
                if not chunk:sel.unregister(key.fileobj);continue
                total+=len(chunk)
                if total>output_limit:raise WorkerError("worker_output_limit")
                if key.data=="stdout":data.extend(chunk)
        remaining=timeout-(time.monotonic()-start)
        if remaining<=0:raise WorkerError("worker_timeout")
        if proc.wait(timeout=remaining)!=0:raise WorkerError("worker_crash")
        try:return json.loads(data)
        except (ValueError,UnicodeDecodeError):raise WorkerError("worker_invalid_json") from None
    except subprocess.TimeoutExpired:raise WorkerError("worker_timeout") from None
    finally:
        # Kill descendants even after a parent exits successfully.
        try:os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        proc.wait(timeout=0.25)
        sel.close()
        for stream in [proc.stdin,proc.stdout,proc.stderr]:
            if not stream.closed:stream.close()

def run_probe(probe,manifest):
    # Restrict inherited variables to runtime basics plus the one explicit secret ref.
    env={k:v for k,v in os.environ.items() if k in {"PATH","LANG","LC_ALL","PYTHONPATH","HOME","SSL_CERT_FILE","SSL_CERT_DIR","XDG_RUNTIME_DIR"}}
    ref=probe.get("credential_ref")
    if ref and ref in os.environ:env[ref]=os.environ[ref]
    try:
        result=supervise([sys.executable,"-m","support_evidence.worker"],{"probe":probe,"deadline_at":time.time()+probe["timeout"]-.1,"policy":{k:manifest.get(k) for k in ["allowed_targets","allowed_addresses","allowed_paths","allowed_units","agent_vantage"]}},probe["timeout"],env)
        validate(result)
        for k in ["subject","instance_id","operation","predicate","route","vantage"]:
            if result.get(k)!=probe.get(k):raise WorkerError("worker_scope_mismatch")
        return result
    except (WorkerError,ValueError) as e:
        reason=str(e) if isinstance(e,WorkerError) else "worker_invalid_contract"
        return observation(probe,collector="TIMEOUT" if reason=="worker_timeout" else "ERROR",value={"reason":reason},method="supervisor")
