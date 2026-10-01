"""Self-contained replay with integrity checks, embedded rules and no execution."""
import os
from pathlib import Path
from .diagnose import diagnose,packages
from .model import clean,canonical,digest,validate
from .policy import read_json

def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.exists():raise ValueError("output already exists; choose a new path")
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w") as f:f.write(canonical(data)+"\n")

def export_bundle(path,records,report,rule_packages=None):
    safe=[clean(r) for r in records]
    pkgs=packages() if rule_packages is None else rule_packages
    expected=diagnose(safe,report["at"],report["impact_contract"],pkgs,report["changes"])
    if expected!=report:raise ValueError("report is not derived from retained evidence/rules")
    ids={r["id"] for r in safe}
    for f in report["findings"]:
        if not set(f["supporting"]+f["contradicting"])<=ids:raise ValueError("dangling finding citation")
    payload={"schema_version":1,"records":safe,"report":report,"packages":pkgs,"integrity_algorithm":"sha256-canonical-json"}
    payload["integrity"]=digest(payload)
    if len(canonical(payload).encode())>8*1024*1024:raise ValueError("bundle size limit")
    write_json(path,payload)

def replay(path):
    data=read_json(path)
    if set(data)!={"schema_version","records","report","packages","integrity_algorithm","integrity"} or data["schema_version"]!=1:raise ValueError("bundle contract")
    if data["integrity_algorithm"]!="sha256-canonical-json":raise ValueError("unsupported bundle integrity")
    integrity=data.pop("integrity")
    if digest(data)!=integrity:raise ValueError("bundle integrity mismatch")
    records=[clean(r) for r in data["records"]]
    report=data["report"];validate(report)
    regenerated=diagnose(records,report["at"],report["impact_contract"],data["packages"],report["changes"])
    if regenerated!=report:raise ValueError("replay diverged")
    return report,records
