"""Local CLI. All network actions require an explicit validated manifest."""
import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from . import __version__
from .knowledge import attachment,render_context,retrieve,refresh_sources
from .adapters import from_monitoring_plugin,from_prometheus,from_otlp_metric
from .bundle import export_bundle,replay,write_json
from .diagnose import diagnose,render,packages,NEXT_CHECKS
from .discovery import discover
from .model import canonical,clean
from .policy import read_json,validate_manifest
from .store import Store
from .supervisor import run_probe

def parser():
    p=argparse.ArgumentParser(description="Evidence-scoped local operational diagnosis")
    p.add_argument("--version",action="version",version=__version__)
    p.add_argument("--store",default=str(Path.home()/".local/state/support-evidence/evidence.sqlite"))
    sub=p.add_subparsers(dest="command",required=True)
    d=sub.add_parser("discover");d.add_argument("--manifest");d.add_argument("--json",action="store_true")
    c=sub.add_parser("check");c.add_argument("manifest");c.add_argument("--json",action="store_true");c.add_argument("--export");c.add_argument("--rag",action="store_true")
    for name in ["diagnose","report"]:
        d=sub.add_parser(name);d.add_argument("--impact",default="unspecified operation");d.add_argument("--at",type=float);d.add_argument("--json",action="store_true");d.add_argument("--rag",action="store_true")
    d=sub.add_parser("ingest");d.add_argument("file")
    d=sub.add_parser("import-monitoring");d.add_argument("manifest");d.add_argument("probe_id");d.add_argument("file");d.add_argument("--format",choices=["prometheus","monitoring-plugin","otlp-json"],required=True);d.add_argument("--threshold",type=float,default=0);d.add_argument("--metric",default="")
    d=sub.add_parser("export");d.add_argument("file");d.add_argument("--impact",default="unspecified operation");d.add_argument("--at",type=float);d.add_argument("--rag",action="store_true")
    d=sub.add_parser("replay");d.add_argument("file");d.add_argument("--json",action="store_true")
    sub.add_parser("health");sub.add_parser("coverage");sub.add_parser("plugins")
    d=sub.add_parser("prune");d.add_argument("--before",type=float,required=True)
    d=sub.add_parser("knowledge");ks=d.add_subparsers(dest="knowledge_command",required=True)
    k=ks.add_parser("search");k.add_argument("service",choices=["postgres","postgresql","nginx","docker","venv"]);k.add_argument("query");k.add_argument("--json",action="store_true")
    k=ks.add_parser("refresh");k.add_argument("--output",required=True)
    return p

def main(argv=None):
    args=parser().parse_args(argv);store=None;knowledge=None
    try:
        if args.command=="replay":
            report,records,knowledge=replay(args.file,with_knowledge=True)
            print(canonical({"report":report,"knowledge":knowledge["context"]} if knowledge else report) if args.json else render(report,records)+(render_context(knowledge["context"]) if knowledge else ""),end="\n" if args.json else "");return 0
        if args.command=="knowledge":
            if args.knowledge_command=="refresh":
                if Path(args.output).exists():raise ValueError("output already exists")
                result=refresh_sources();write_json(args.output,result)
                fetched=sum(source["status"]=="fetched" for source in result["sources"])
                print(str(args.output)+": "+str(fetched)+"/"+str(len(result["sources"]))+" sources fetched; reviewed summaries unchanged")
                return 0 if fetched==len(result["sources"]) else 3
            hits=retrieve(args.service,args.query)
            print(canonical(hits) if args.json else "\n".join("["+h["card"]["id"]+"] "+h["card"]["summary"]+"\nSource: "+h["card"]["source"]["url"] for h in hits) or "No matching documentation; abstain.");return 0
        if args.command=="plugins":
            print(canonical({"packages":packages(),"registered_next_checks":NEXT_CHECKS,"execution":"trusted bundled workers only; no remediation"}));return 0
        store=Store(args.store)
        if args.command=="health":print(canonical(store.health()));return 0
        if args.command=="prune":print(canonical({"pruned":store.prune(args.before)}));return 0
        if args.command=="ingest":
            data=read_json(args.file);records=data if isinstance(data,list) else data["records"]
            print(canonical({"ingested":store.ingest(records)}));return 0
        if args.command=="import-monitoring":
            m=validate_manifest(read_json(args.manifest));probe=next(p for p in m["probes"] if p["id"]==args.probe_id);data=read_json(args.file)
            if args.format=="prometheus":obs=from_prometheus(probe,data,args.threshold)
            elif args.format=="otlp-json":obs=from_otlp_metric(probe,data,args.metric,args.threshold)
            else:obs=from_monitoring_plugin(probe,data["exit_code"],at=data.get("event_at"))
            store.ingest([obs]);print(canonical(obs));return 0
        if args.command=="discover":
            m=validate_manifest(read_json(args.manifest)) if args.manifest else None
            result=discover(m);store.ingest(result["records"]);print(canonical(result));return 0
        if args.command=="check":
            m=validate_manifest(read_json(args.manifest));records=m.get("entities",[])+m.get("assertions",[])
            for probe in m["probes"]:records.append(run_probe(probe,m))
            store.ingest(records);records=[clean(r) for r in records]
            report=diagnose(records,time.time(),m.get("impact_contract","unspecified operation"),changes=m.get("changes",[]))
            if args.rag:knowledge=attachment(report,records)
            if args.export:export_bundle(args.export,records,report,knowledge=knowledge)
        else:
            records=store.records();at=getattr(args,"at",None) or time.time()
            report=diagnose(records,at,getattr(args,"impact","unspecified operation"))
            if args.command=="coverage":print(canonical({"coverage":report["coverage"],"topology":report["topology"],"collector_health":report["collector_health"]}));return 0
            if getattr(args,"rag",False):knowledge=attachment(report,records)
            if args.command=="export":export_bundle(args.file,records,report,knowledge=knowledge);print(args.file);return 0
        print(canonical({"report":report,"knowledge":knowledge["context"]} if knowledge else report) if args.json else render(report,records)+(render_context(knowledge["context"]) if knowledge else ""),end="\n" if args.json else "")
        return 1 if any(f["assessment"] in {"strong","moderate"} for f in report["findings"]) else 3 if report["coverage"]["fresh_applicable"]==0 or report["findings"] or any("collection_or_predicate_unknown" in u or "stale" in u or "clock_skew" in u or "unsupported_failure" in u for u in report["unknowns"]) else 0
    except (ValueError,OSError,KeyError,StopIteration,sqlite3.Error):
        print("support-evidence: operation failed validation, policy, storage or input checks; no target-health conclusion",file=sys.stderr);return 3
    finally:
        if store:store.close()

if __name__=="__main__":raise SystemExit(main())
