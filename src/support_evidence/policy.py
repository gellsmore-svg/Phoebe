"""Explicit destination policy and pinned resolution. No redirect or shell support."""
import ipaddress
import json
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit
from .model import validate

OPERATIONS={"dns","tcp","unix","tls","http","systemd","filesystem","host","mongodb_ping","mongodb_read","postgresql_connect","postgresql_read"}
FORBIDDEN=(ipaddress.ip_network("169.254.0.0/16"),ipaddress.ip_network("fe80::/10"),ipaddress.ip_network("0.0.0.0/8"),ipaddress.ip_network("100.100.100.200/32"))

def read_json(path, limit=8*1024*1024):
    with open(path,"rb") as f: raw=f.read(limit+1)
    if len(raw)>limit: raise ValueError("input exceeds size budget")
    return json.loads(raw)

def validate_manifest(m):
    if set(m)-{"schema_version","agent_vantage","scope","allowed_targets","allowed_addresses","allowed_paths","allowed_units","probes","entities","assertions","impact_contract","changes","budget"}:raise ValueError("unknown manifest fields")
    if m.get("schema_version")!=1:raise ValueError("unsupported manifest schema")
    if not isinstance(m.get("agent_vantage"),str):raise ValueError("agent vantage required")
    if len(m.get("probes",[]))>32:raise ValueError("check count budget exceeded")
    ids=set()
    for p in m.get("probes",[]):
        validate(p)
        if p["id"] in ids:raise ValueError("duplicate probe ID")
        ids.add(p["id"])
        if p["operation"] not in OPERATIONS:raise ValueError("unregistered operation")
        if p["vantage"]!=m["agent_vantage"]:raise ValueError("probe vantage requires execution by that agent")
        if p["namespace"]!="current":raise ValueError("unsupported network namespace")
        if p["target"] not in m.get("allowed_targets",[]):raise ValueError("target not explicitly allowlisted")
        if p["operation"] in {"filesystem","unix"}:allowed_path(p["target"],m)
        if p["operation"]=="systemd":
            if p["target"] not in m.get("allowed_units",[]) or not re.fullmatch(r"[A-Za-z0-9_.@:-]+\.service",p["target"]):raise ValueError("unit denied")
        if p.get("credential_ref") and not re.fullmatch(r"SUPPORT_[A-Z0-9_]+",p["credential_ref"]):raise ValueError("credential reference denied")
    if sum(p["timeout"] for p in m.get("probes",[]))>60:raise ValueError("nominal work budget exceeded")
    if len(m.get("entities",[]))+len(m.get("assertions",[]))>5000:raise ValueError("topology budget")
    for r in m.get("entities",[])+m.get("assertions",[]):validate(r)
    return m

def allowed_path(target,m):
    path=Path(target)
    if not path.is_absolute() or str(path.resolve()) not in m.get("allowed_paths",[]):raise ValueError("path denied or symbolic link changed")
    return path

def destination(target):
    if "://" in target:
        u=urlsplit(target)
        if u.scheme not in {"http","https","tcp","tls","mongodb","postgresql"} or u.username or u.password or u.query or u.fragment:raise ValueError("unsafe target syntax")
        if not u.hostname:raise ValueError("target hostname required")
        if any(c in target for c in "\r\n\x00"):raise ValueError("unsafe target")
        port=u.port or {"http":80,"https":443,"mongodb":27017,"postgresql":5432,"tcp":0,"tls":443}[u.scheme]
        if not 1<=port<=65535:raise ValueError("port required")
        return u.hostname,port,u.path or "/",u.scheme
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,253}",target):raise ValueError("invalid hostname")
    return target,0,"/","dns"

def resolve(target,m):
    if target not in m.get("allowed_targets",[]):raise PermissionError("target denied")
    host,port,path,scheme=destination(target)
    permitted=m.get("allowed_addresses",{}).get(host,[])
    if not permitted:raise PermissionError("hostname has no approved addresses")
    answers=socket.getaddrinfo(host,port or None,type=socket.SOCK_STREAM)
    addresses=sorted({a[4][0] for a in answers})
    if not addresses:raise socket.gaierror("no address")
    for addr in addresses:
        ip=ipaddress.ip_address(addr)
        if getattr(ip,"ipv4_mapped",None):ip=ip.ipv4_mapped
        if ip.is_multicast or ip.is_unspecified or any(ip.version==net.version and ip in net for net in FORBIDDEN):raise PermissionError("special destination denied")
        if str(ip) not in permitted:raise PermissionError("DNS address differs from approved set")
    # Subsequent connection uses this literal address; TLS uses the original hostname.
    return host,port,path,scheme,addresses[0]
