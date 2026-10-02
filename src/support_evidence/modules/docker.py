"""Fixed read-only Engine API requests over one explicitly approved Unix socket.

Inspect bodies may contain secrets; only closed numeric/state aggregates escape.
No CLI, context discovery, logs, exec, writes, redirects or remote daemon access.
"""
import http.client
import json
import re
import socket
import stat
import time
from .common import CollectionStatus, validate_local_probe

OPERATIONS = {"docker_daemon", "docker_container", "docker_health", "docker_resources"}
MIN_API, MAX_API = (1, 24), (1, 47)

def integer(value):
    if type(value) is not int or not 0 <= value <= 2**63-1:
        raise CollectionStatus("ERROR", "docker_response_malformed")
    return value

def api_version(value):
    if not isinstance(value, str) or not re.fullmatch(r"1\.[0-9]{1,3}", value):
        raise CollectionStatus("ERROR", "docker_version_malformed")
    return tuple(map(int, value.split(".")))

class Client:
    def __init__(self, path, deadline):
        self.path, self.deadline = path, deadline
        self.identity = path.stat()
        if not stat.S_ISSOCK(self.identity.st_mode):
            raise CollectionStatus("UNAVAILABLE", "docker_socket_not_socket")

    def get(self, route, limit=1048576):
        if not re.fullmatch(r"/version|/v1\.[0-9]{2}/containers/[a-f0-9]{64}/(?:json|stats\?stream=false)",route):
            raise PermissionError("docker_endpoint_policy")
        current = self.path.stat()
        if (current.st_dev, current.st_ino) != (self.identity.st_dev, self.identity.st_ino):
            raise CollectionStatus("ERROR", "docker_socket_changed")
        remaining = max(.01, self.deadline-time.monotonic())
        conn = http.client.HTTPConnection("localhost", timeout=remaining)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(remaining); sock.connect(str(self.path)); conn.sock = sock
            conn.request("GET", route, headers={"Host":"localhost", "Connection":"close"})
            response = conn.getresponse(); raw = response.read(limit+1)
            if len(raw) > limit: raise CollectionStatus("ERROR", "docker_response_budget")
            if response.status in {401,403}: raise CollectionStatus("DENIED", "docker_api_permission")
            if response.status == 404 and "/containers/" in route and route.endswith("/json"):
                return None
            if response.status != 200:
                raise CollectionStatus("UNAVAILABLE", "docker_api_unavailable", status_code=response.status)
            try: data = json.loads(raw)
            except (ValueError, RecursionError): raise CollectionStatus("ERROR", "docker_response_malformed") from None
            if not isinstance(data, dict): raise CollectionStatus("ERROR", "docker_response_malformed")
            return data
        finally:
            conn.close(); sock.close()

def state_result(data, identity, expected):
    if data.get("Id") != identity:
        raise CollectionStatus("ERROR", "docker_identity_mismatch")
    state = data.get("State")
    if not isinstance(state, dict): raise CollectionStatus("ERROR", "docker_response_malformed")
    name = state.get("Status")
    states = {"created", "running", "paused", "restarting", "removing", "exited", "dead"}
    if name not in states or any(type(state.get(k)) is not bool for k in ["Running","Paused","Restarting","OOMKilled","Dead"]):
        raise CollectionStatus("ERROR", "docker_response_malformed")
    if (name in {"running","paused","restarting"}) != state["Running"] or (name == "paused") != state["Paused"] or (name == "restarting") != state["Restarting"] or (name == "dead") != state["Dead"]:
        raise CollectionStatus("ERROR", "docker_state_inconsistent")
    value = {"state":name, "oom_killed":state["OOMKilled"], "exit_code":integer(state.get("ExitCode")), "restart_count":integer(data.get("RestartCount"))}
    reason = "docker_oom_recorded" if state["OOMKilled"] else "docker_state_mismatch" if name != expected.get("container_state","running") else "docker_restart_threshold" if value["restart_count"] > expected.get("max_restarts",2**63-1) else None
    if reason: value["reason"] = reason
    return value, reason is None

def health_result(data, value):
    health = data["State"].get("Health")
    if health is None: raise CollectionStatus("UNAVAILABLE", "docker_health_not_configured")
    if not isinstance(health,dict) or health.get("Status") not in {"starting","healthy","unhealthy"}:
        raise CollectionStatus("ERROR", "docker_health_malformed")
    if health["Status"] == "starting": raise CollectionStatus("UNAVAILABLE", "docker_health_starting")
    value = dict(value, healthy=health["Status"]=="healthy", health_failures=integer(health.get("FailingStreak")))
    if not value["healthy"]: value["reason"] = "docker_unhealthy"
    return value, value["healthy"]

def resource_result(data, stats, value, expected):
    if stats.get("id") != data["Id"]: raise CollectionStatus("ERROR", "docker_identity_mismatch")
    config = data.get("HostConfig")
    if not isinstance(config,dict): raise CollectionStatus("ERROR", "docker_response_malformed")
    value = dict(value); failed = False
    for field, limit_key, bucket, usage_key, prefix in [
        ("min_memory_headroom_bytes","Memory","memory_stats","usage","memory"),
        ("min_pids_headroom","PidsLimit","pids_stats","current","pids")]:
        if field not in expected: continue
        limit = config.get(limit_key)
        if limit in {None,0,-1}: raise CollectionStatus("UNAVAILABLE", "docker_resource_limit_unknown")
        limit = integer(limit)
        counters = stats.get(bucket)
        if not isinstance(counters,dict): raise CollectionStatus("UNAVAILABLE", "docker_statistics_unavailable")
        used = counters.get(usage_key)
        if used is None: raise CollectionStatus("UNAVAILABLE", "docker_statistics_unavailable")
        used = integer(used); headroom = limit-used
        value.update({prefix+"_limit":limit, prefix+"_used":used, prefix+"_headroom":headroom})
        failed |= headroom < expected[field]
    if failed: value["reason"] = "docker_resource_threshold"
    return value, not failed

def collect(probe, manifest):
    validate_local_probe(probe,manifest)
    from ..policy import allowed_path
    path = allowed_path(probe["target"], manifest).resolve()
    try:
        client = Client(path, probe["_deadline"])
        version = client.get("/version",32768)
        maximum = api_version(version.get("ApiVersion")); minimum = api_version(version.get("MinAPIVersion","1.24"))
        selected = min(MAX_API, maximum)
        if maximum < minimum or selected < max(MIN_API, minimum):
            raise CollectionStatus("UNAVAILABLE", "docker_api_version_unsupported")
        if version.get("Os") != "linux": raise CollectionStatus("UNAVAILABLE", "docker_platform_unsupported")
        if probe["operation"] == "docker_daemon": return {"api_version_num":selected[1]}
        prefix = "/v%d.%d/containers/%s" % (*selected, probe["instance_id"])
        data = client.get(prefix+"/json")
        if data is None: return {"reason":"docker_container_missing"}, False
        value, ok = state_result(data, probe["instance_id"], probe["expected"])
        if not ok or probe["operation"] == "docker_container": return value, ok
        if probe["operation"] == "docker_health": return health_result(data,value)
        if not isinstance(data["State"].get("StartedAt"),str) or not data["State"]["StartedAt"]:
            raise CollectionStatus("ERROR", "docker_response_malformed")
        stats = client.get(prefix+"/stats?stream=false",262144)
        # Reject exit/restart races: counters must belong to the same lifetime.
        after = client.get(prefix+"/json")
        if after is None or after.get("RestartCount") != data.get("RestartCount") or after.get("State",{}).get("StartedAt") != data["State"].get("StartedAt") or after.get("State",{}).get("Status") != "running" or after.get("HostConfig",{}).get("Memory") != data.get("HostConfig",{}).get("Memory") or after.get("HostConfig",{}).get("PidsLimit") != data.get("HostConfig",{}).get("PidsLimit"):
            raise CollectionStatus("UNAVAILABLE", "docker_container_changed")
        return resource_result(data,stats,value,probe["expected"])
    except PermissionError: raise CollectionStatus("DENIED", "docker_socket_permission") from None
    except (FileNotFoundError, ConnectionError): return {"reason":"docker_daemon_unreachable"}, False
    except (socket.timeout, TimeoutError): raise CollectionStatus("TIMEOUT", "docker_api_deadline") from None
    except (OSError, http.client.HTTPException): raise CollectionStatus("UNAVAILABLE", "docker_api_connection") from None
