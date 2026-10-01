"""Nginx route and optional stub_status contracts; bodies never become evidence."""
import re
from .common import CollectionStatus

OPERATIONS = {"nginx_http", "nginx_stub_status"}
STATUS = re.compile(rb"Active connections: ([0-9]{1,20})\s+server accepts handled requests\s+([0-9]{1,20}) ([0-9]{1,20}) ([0-9]{1,20})\s+Reading: ([0-9]{1,20}) Writing: ([0-9]{1,20}) Waiting: ([0-9]{1,20})\s*")

def status_result(status_code, body, expected):
    if status_code in {401, 403}:
        raise CollectionStatus("DENIED", "nginx_status_permission", status_code=status_code)
    if status_code != 200:
        raise CollectionStatus("UNAVAILABLE", "nginx_status_unavailable", status_code=status_code)
    match = STATUS.fullmatch(body)
    if match is None:
        raise CollectionStatus("ERROR", "nginx_status_malformed", status_code=status_code)
    active, accepts, handled, requests, reading, writing, waiting = map(int, match.groups())
    if handled > accepts or max(reading, writing, waiting) > active:
        raise CollectionStatus("ERROR", "nginx_status_inconsistent", status_code=status_code)
    value = dict(zip(["active_connections", "accepts", "handled", "requests", "reading", "writing", "waiting"], [active, accepts, handled, requests, reading, writing, waiting]))
    value["status_code"] = status_code
    # Cumulative counters are metadata; never diagnose current drops from their gap.
    if "max_active_connections" not in expected:
        raise CollectionStatus("UNAVAILABLE", "nginx_status_threshold_missing", **value)
    ok = active <= expected["max_active_connections"]
    return {**value, **({"reason": "nginx_active_threshold"} if not ok else {})}, ok

def route_reason(code):
    return {502: "nginx_bad_gateway", 504: "nginx_gateway_timeout", 503: "nginx_service_unavailable", 429: "nginx_rate_limited", 403: "nginx_route_forbidden", 404: "nginx_route_missing", 413: "nginx_body_limit"}.get(code, "nginx_http_status")
