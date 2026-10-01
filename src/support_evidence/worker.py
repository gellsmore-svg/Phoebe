"""One registered read-only probe per process; no target-controlled execution."""
import hashlib
import http.client
import json
import math
import os
import socket
import ssl
import subprocess
import sys
import time
from .model import canonical, observation
from .policy import resolve, allowed_path

class TargetFailure(Exception):
    def __init__(self,reason):self.reason=reason

def secret(probe):
    ref=probe.get("credential_ref")
    if not ref or ref not in os.environ:raise PermissionError("credential_unavailable")
    data=json.loads(os.environ[ref])
    if set(data)-{"username","password","database","auth_source","ca_file"}:raise PermissionError("credential_fields_denied")
    return data

def network(probe,m):
    host,port,path,scheme,ip=resolve(probe["target"],m)
    op=probe["operation"];budget=max(0.01,probe["timeout"]-0.2)
    if op=="dns":return {"addresses_count":1}
    if op.startswith("mongodb") or op.startswith("postgresql"):
        return database(probe,m,host,port,ip,budget)
    s=socket.create_connection((ip,port),timeout=budget)
    try:
        if op=="tls" or scheme=="https":
            try:s=ssl.create_default_context().wrap_socket(s,server_hostname=host)
            except ssl.SSLCertVerificationError as e:
                code=e.verify_code
                raise TargetFailure("tls_expired" if code==10 else "tls_hostname_mismatch" if code==62 else "tls_verification_failed") from None
            if op=="tls":
                days=(ssl.cert_time_to_seconds(s.getpeercert()["notAfter"])-time.time())/86400
                if days<probe["expected"].get("min_valid_days",0):raise TargetFailure("tls_expiry_budget")
                return {"valid_days":round(days,2)}
        if op=="http":
            # Manual pinned socket prevents a second DNS lookup. Redirects are never followed.
            conn=http.client.HTTPConnection(host,port,timeout=budget);conn.sock=s
            conn.request("GET",path,headers={"Host":host+(":"+str(port) if port not in (80,443) else ""),"User-Agent":"support-evidence/0.1","Connection":"close"})
            response=conn.getresponse(); body=response.read(65537)
            if len(body)>65536:raise TargetFailure("http_response_over_budget")
            value={"status_code":response.status}
            if response.status!=probe["expected"].get("status",200):
                value["reason"]="http_status"
                return value,False
            expected=probe["expected"]
            match=True
            if "sha256" in expected:match=hashlib.sha256(body).hexdigest()==expected["sha256"]
            if "json_key" in expected:
                try:match=json.loads(body).get(expected["json_key"])==expected.get("json_value")
                except (ValueError,AttributeError):match=False
            value["oracle_match"]=match
            if not match:value["reason"]="oracle_mismatch"
            return value,match
        return {}
    finally:s.close()

def database(probe,m,host,port,ip,budget):
    creds=secret(probe);op=probe["operation"]
    if op.startswith("mongodb"):
        from pymongo import MongoClient
        from pymongo.errors import OperationFailure, PyMongoError
        opts={"host":ip,"port":port,"username":creds["username"],"password":creds["password"],"authSource":creds.get("auth_source","admin"),"directConnection":True,"serverSelectionTimeoutMS":int(budget*1000),"connectTimeoutMS":int(budget*1000),"socketTimeoutMS":int(budget*1000),"maxPoolSize":1,"retryReads":False}
        # TLS deployments require literal-address certificates in this MVP. Never disable verification.
        if creds.get("ca_file"):opts.update(tls=True,tlsCAFile=str(allowed_path(creds["ca_file"],m)))
        try:
            with MongoClient(**opts) as client:
                if op=="mongodb_ping":client.admin.command("ping");return {}
                with __import__("pymongo").timeout(budget):
                    row=client[creds.get("database","support")].support_probe.find_one({"_id":1},{"_id":1},max_time_ms=max(1,int(budget*1000)))
                return {"rows_present":row is not None},row is not None
        except OperationFailure as e:
            raise TargetFailure("authentication" if e.code in {13,18} else "database_operation") from None
        except PyMongoError:raise TargetFailure("database_deadline_or_connection") from None
    import psycopg
    try:
        with psycopg.connect(host=host,hostaddr=ip,port=port,user=creds["username"],password=creds["password"],dbname=creds.get("database","support"),connect_timeout=max(1,math.ceil(budget)),options="-c default_transaction_read_only=on -c statement_timeout="+str(int(budget*1000)),sslmode="verify-full" if creds.get("ca_file") else "disable",**({"sslrootcert":str(allowed_path(creds["ca_file"],m))} if creds.get("ca_file") else {})) as conn:
            if op=="postgresql_connect":return {}
            count=conn.execute("SELECT count(*) FROM public.support_probe WHERE id = 1").fetchone()[0]
            return {"rows_present":count>0},count>0
    except psycopg.Error as e:
        raise TargetFailure("authentication" if e.sqlstate and e.sqlstate.startswith("28") else "database_operation") from None

def execute(probe,m):
    start=time.monotonic();value={};status="PASS";collector="OK"
    try:
        op=probe["operation"]
        if op in {"dns","tcp","tls","http","mongodb_ping","mongodb_read","postgresql_connect","postgresql_read"}:result=network(probe,m)
        elif op=="unix":
            path=allowed_path(probe["target"],m)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:s.settimeout(probe["timeout"]-0.1);s.connect(str(path))
            result={}
        elif op=="filesystem":
            v=os.statvfs(allowed_path(probe["target"],m));result={"free_bytes":v.f_bavail*v.f_frsize,"free_inodes":v.f_favail}
            status="PASS" if result["free_bytes"]>=probe["expected"].get("min_free_bytes",1) and result["free_inodes"]>=probe["expected"].get("min_free_inodes",1) else "FAIL"
        elif op=="host":
            info=dict(line.split(":",1) for line in open("/proc/meminfo"))
            result={"load1":os.getloadavg()[0],"available_bytes":int(info["MemAvailable"].strip().split()[0])*1024}
            status="PASS" if result["load1"]<=probe["expected"].get("max_load",1e9) and result["available_bytes"]>=probe["expected"].get("min_available_bytes",0) else "FAIL"
        elif op=="systemd":
            if probe["target"] not in m.get("allowed_units",[]):raise PermissionError()
            r=subprocess.run(["systemctl","show",probe["target"],"--no-pager","--property=LoadState,ActiveState,SubState,Result,NRestarts,MainPID"],capture_output=True,timeout=max(.1,probe["timeout"]-.2))
            if r.returncode:raise PermissionError()
            fields=dict(line.split("=",1) for line in r.stdout.decode().splitlines() if "=" in line)
            if fields.get("LoadState") in {None,"not-found","error","masked"}:result={"state":"unit_unavailable"};status="UNKNOWN"
            else:
                result={"state":fields.get("ActiveState","unknown"),"service_result":fields.get("Result","unknown"),"restart_count":int(fields.get("NRestarts",0)),"pid":int(fields.get("MainPID",0))}
                status="PASS" if result["state"]=="active" else "FAIL"
        else:raise ValueError("unsupported_operation")
        if isinstance(result,tuple):value,ok=result;status="PASS" if ok else "FAIL"
        else:value=result
    except PermissionError:collector="DENIED";status="UNKNOWN";value={"reason":"policy_or_permission_denied"}
    except (ImportError,FileNotFoundError):collector="UNAVAILABLE";status="UNKNOWN";value={"reason":"prerequisite_unavailable"}
    except TargetFailure as e:status="FAIL";value={"reason":e.reason}
    except socket.gaierror:status="FAIL";value={"reason":"dns_resolution"}
    except (socket.timeout,TimeoutError):status="FAIL";value={"reason":"operation_deadline"}
    except (ConnectionError,OSError):status="FAIL";value={"reason":"operation_connection"}
    except Exception:collector="ERROR";status="UNKNOWN";value={"reason":"collector_exception"}
    value["duration_ms"]=round((time.monotonic()-start)*1000,3)
    return observation(probe,status,collector,value)

def main():
    request=json.loads(sys.stdin.buffer.readline(65537));result=execute(request["probe"],request["policy"])
    print(canonical(result))

if __name__=="__main__":main()
