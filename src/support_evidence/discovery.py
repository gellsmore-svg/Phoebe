"""Bounded read-only Linux discovery; names and ports do not infer technologies."""
import hashlib
import re
import socket
import subprocess
import time
from pathlib import Path
from .model import digest, provenance, validate
from .policy import allowed_path


def entity(id,kind,scope,attributes,technology="unknown",instance=None,method="linux_discovery"):
    return validate({"schema_version":1,"kind":"entity","id":id,"scope":scope,"logical_id":id,"instance_id":instance,"entity_kind":kind,"technology":technology,"attributes":attributes,"provenance":provenance(method)})

def assertion(source,target,relation,view,at,method="linux_discovery"):
    return validate({"schema_version":1,"kind":"assertion","id":"assertion:"+digest([source,target,relation,view,at])[:24],"source":source,"target":target,"relation":relation,"view":view,"valid_from":at,"valid_until":at+300 if view=="DISCOVERED" else None,"received_at":at,"provenance":provenance(method),"evidence_ids":[],"criticality":"unknown","condition":"UNKNOWN","synchrony":"unknown","status":"assertion"})

def process_identity(scope,boot,pid,start_ticks):return "process:"+digest([scope,boot,pid,start_ticks])[:32]

def nginx_metadata(text,scope,at):
    # Structural subset only: no config dump, include traversal or executable parsing.
    stripped=re.sub(r"#[^\n]*","",text)
    records=[]
    for match in list(re.finditer(r"\b(?:proxy_pass|server)\s+(http[s]?://[A-Za-z0-9_.:/-]+|unix:/[A-Za-z0-9_./-]+|[A-Za-z0-9_.-]+:[0-9]+)\s*;",stripped))[:128]:
        target=match.group(1);id="endpoint:"+digest([scope,target])[:24]
        records.append(entity(id,"endpoint",scope,{"listener":target},method="nginx_safe_subset"))
        records.append(assertion("service:nginx",id,"PROXIES_TO","INTENDED",at,"nginx_safe_subset"))
    return records

def discover(manifest=None,proc_root="/proc"):
    m=manifest or {};scope=m.get("scope",socket.gethostname());at=time.time();records=[]
    coverage={"processes":"partial","listeners":"partial","systemd":"unknown","nginx":"not_requested","namespace":"current","technology_identity":"not_inferred_from_names_or_ports"}
    root=Path(proc_root)
    boot=(root/"sys/kernel/random/boot_id").read_text().strip() if (root/"sys/kernel/random/boot_id").exists() else "unknown_boot"
    host="host:"+digest(scope)[:24];records.append(entity(host,"host",scope,{"host.name":scope,"boot_id":boot}))
    processes=sorted((p for p in root.iterdir() if p.name.isdigit()),key=lambda p:int(p.name))
    denied=0
    for path in processes[:512]:
        try:
            stat=(path/"stat").read_text();tail=stat[stat.rfind(")")+2:].split();start=int(tail[19]);pid=int(path.name)
            id=process_identity(scope,boot,pid,start)
            records += [entity(id,"process",scope,{"process.pid":pid,"process.start_ticks":start,"boot_id":boot},instance=id),assertion(id,host,"RUNS_ON","DISCOVERED",at)]
        except (OSError,ValueError,IndexError):denied+=1
    coverage["process_denials"]=denied;coverage["process_truncated"]=len(processes)>512
    count=0
    for name in ["tcp","tcp6","unix"]:
        try:lines=(root/"net"/name).read_text().splitlines()[1:]
        except OSError:continue
        for line in lines:
            if count>=512:break
            cols=line.split()
            if name=="unix":
                if len(cols)<8 or cols[3]!="00010000":continue
                listener=cols[-1]
            else:
                if len(cols)<4 or cols[3]!="0A":continue
                listener=name+":"+cols[1] # raw kernel address avoids endian/identity guesses
            id="listener:"+digest([scope,boot,listener])[:24]
            records += [entity(id,"endpoint",scope,{"listener":listener}),assertion(id,host,"RUNS_ON","DISCOVERED",at)]
            count+=1
    try:
        r=subprocess.run(["systemctl","list-units","--type=service","--all","--no-legend","--no-pager","--plain"],capture_output=True,timeout=3)
        if r.returncode==0:
            coverage["systemd"]="inventory_only; use named state probes"
            for line in r.stdout.decode().splitlines()[:256]:
                unit=line.split()[0]
                if re.fullmatch(r"[A-Za-z0-9_.@:-]+\.service",unit):records.append(entity("unit:"+unit,"service",scope,{"unit":unit},technology="systemd"))
    except (OSError,subprocess.TimeoutExpired):coverage["systemd"]="unavailable"
    for path in m.get("allowed_paths",[]):
        if path.endswith(".conf"):
            try:
                text=allowed_path(path,m).read_text()
                if len(text.encode())>65536:raise ValueError("config size budget")
                records += nginx_metadata(text,scope,at);coverage["nginx"]="safe subset; includes, variables and generated configs unresolved"
            except (OSError,ValueError):coverage["nginx"]="collection_failed"
    records += m.get("entities",[])+m.get("assertions",[])
    return {"schema_version":1,"records":records,"coverage":coverage,"created_at":at}
