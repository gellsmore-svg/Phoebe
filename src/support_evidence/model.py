"""Versioned contracts. Incoming metadata is data, never instructions."""
import hashlib
import json
import math
import re
import time
import uuid
from importlib.resources import files
from jsonschema import Draft202012Validator

SCHEMA = json.loads(files("support_evidence").joinpath("schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA)
SAFE_VALUE_KEYS = {"status_code", "duration_ms", "reason", "free_bytes", "free_inodes", "load1", "available_bytes", "rows_present", "oracle_match", "valid_days", "state", "restart_count", "pid", "sample", "value", "threshold", "checkout_wait_ms", "checkout_timeouts", "connections", "addresses_count", "exit_code", "service_result", "uptime_ticks", "bytes", "error_code"}
SAFE_VALUE_KEYS |= {"oom_killed", "healthy", "health_failures", "api_version_num", "memory_limit", "memory_used", "memory_headroom", "pids_limit", "pids_used", "pids_headroom", "python_version_num", "interpreter_present", "system_site_packages", "distributions", "missing_dependencies", "dependency_conflicts", "metadata_complete", "python_scripts", "stale_script_paths"}
SAFE_VALUE_KEYS |= {'masked_sessions', 'idle_transactions', 'blocked_sessions', 'server_version_num', 'standbys', 'requests', 'active_sessions', 'accepts', 'statistics_visible', 'reading', 'oldest_transaction_seconds', 'waiting', 'in_recovery', 'oldest_xid_age', 'lock_waiters', 'handled', 'active_connections', 'max_connections', 'connection_headroom', 'writing', 'reserved_connections', 'replay_backlog_bytes'}
SAFE_ATTR_KEYS = {"host.name", "service.name", "service.namespace", "service.instance.id", "service.version", "process.pid", "process.start_ticks", "boot_id", "listener", "unit", "schema_url", "maturity", "build_id", "owner", "version_source"}
SECRET = re.compile(r"(?i)(password|passwd|secret|token|authorization|private.?key|credential|api.?key)")
UNSAFE_TEXT = re.compile(r"(?i)(bearer\s+\S+|[a-z][a-z0-9+.-]*://[^\s/]*@|(?:password|token|secret|api_key)\s*[=:]\s*\S+|-----BEGIN .*PRIVATE KEY)")

def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False)

def digest(data):
    return hashlib.sha256(canonical(data).encode()).hexdigest()

def identifier(kind):
    return kind + ":" + uuid.uuid4().hex

def provenance(method, source="local", version="1"):
    return {"source": source, "method": method, "version": version}

def validate(record):
    limit=8*1024*1024 if record.get("kind")=="incident" else 65536
    if len(canonical(record).encode()) > limit:
        raise ValueError("record size budget exceeded")
    errors = sorted(VALIDATOR.iter_errors(record), key=lambda e: str(e.path))
    if errors:
        # Do not echo the untrusted record or JSON Schema error, which includes values.
        raise ValueError("invalid " + str(record.get("kind", "record"))[:32] + " contract")
    if record["kind"] == "observation":
        if record["collector_status"] != "OK" and record["predicate_status"] != "UNKNOWN":
            raise ValueError("collection failure requires UNKNOWN predicate")
        if record["event_at"] < 0 or record["received_at"] < 0:
            raise ValueError("invalid event time")
    if record["kind"] == "assertion":
        if record["valid_until"] is not None and record["valid_until"] < record["valid_from"]:
            raise ValueError("inverted validity interval")
        if record["relation"] == "FAILURE_PROPAGATES_TO" and record["status"] not in {"hypothesis", "validated_mechanism"}:
            raise ValueError("propagation requires a labelled mechanism or hypothesis")
    return record

def clean(record):
    """Drop arbitrary payloads. Metadata allowlist supplements secret-pattern rejection."""
    record = json.loads(canonical(record))
    if record.get("kind") == "observation":
        record["value"] = {k:v for k,v in record["value"].items() if k in SAFE_VALUE_KEYS and isinstance(v,(int,float,bool,type(None)))} | {k:v for k,v in record["value"].items() if k in {"reason", "state", "service_result", "error_code"} and isinstance(v,str) and re.fullmatch(r"[a-zA-Z0-9_.:-]{1,64}",v)}
        record["redaction"] = "metadata_only"
    if record.get("kind") == "entity":
        record["attributes"] = {k:v for k,v in record["attributes"].items() if k in SAFE_ATTR_KEYS}
    def visit(value, key=""):
        if isinstance(value, dict):
            return {k:visit(v,k) for k,v in value.items() if not SECRET.search(k) or k == "credential_ref"}
        if isinstance(value,list): return [visit(v) for v in value]
        if isinstance(value,str):
            if UNSAFE_TEXT.search(value): raise ValueError("secret-bearing metadata rejected")
            if any(ord(c) < 32 for c in value): raise ValueError("control characters in metadata")
        return value
    record=visit(record)
    if record.get("kind")=="observation":
        record.pop("integrity",None);record["integrity"]=digest(record)
    return validate(record)

def observation(probe, status="UNKNOWN", collector="OK", value=None, method="probe", now=None):
    now = time.time() if now is None else now
    r = {"schema_version":1,"kind":"observation","id":identifier("obs"),"subject":probe["subject"],"instance_id":probe.get("instance_id"),"operation":probe["operation"],"predicate":probe["predicate"],"route":probe["route"],"vantage":probe["vantage"],"event_at":now,"received_at":now,"freshness":probe["freshness"],"value":value or {},"units":"metadata","provenance":provenance(method),"evidence_ids":[],"collector_status":collector,"predicate_status":status,"coverage":"point","sampling":1,"dependence_group":"agent:"+probe["vantage"],"redaction":"metadata_only","reliability":"direct","retention":"retained"}
    r = clean(r)
    r["integrity"] = digest(r)
    return validate(r)

def freshness(obs, at):
    if obs["event_at"] > at + 2 or obs["event_at"] > obs["received_at"] + 2:
        return "clock_skew"
    if at < obs["event_at"] or at - obs["event_at"] > obs["freshness"]:
        return "stale"
    return "fresh"

def scope(obs):
    return tuple(obs.get(k) for k in ["subject","instance_id","operation","predicate","route","vantage"])
