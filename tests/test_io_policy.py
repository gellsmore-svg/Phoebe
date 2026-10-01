import copy
import json
import socket
import sys
import time
import pytest
from support_evidence.bundle import export_bundle,replay
from support_evidence.diagnose import diagnose
from support_evidence.model import observation
from support_evidence.policy import validate_manifest,resolve,destination
from support_evidence.store import Store
from support_evidence.supervisor import supervise,WorkerError,run_probe
from support_evidence.adapters import from_prometheus,from_monitoring_plugin,from_otlp_metric
from support_evidence.cli import main

def test_immutable_atomic_store_and_quota(tmp_path,probe):
    store=Store(tmp_path/"e.sqlite",max_records=1)
    a=observation(probe,"PASS",now=100);b=observation(probe,"FAIL",now=100)
    store.ingest([a]);store.ingest([a])
    assert len(store.records())==1
    with pytest.raises(ValueError):store.ingest([b])
    assert len(store.records())==1
    b["id"]=a["id"]
    with pytest.raises(ValueError):store.ingest([b])
    assert store.health()["integrity"]=="ok"
    store.close()

def test_batch_rolls_back_on_quota(tmp_path,probe):
    s=Store(tmp_path/"e.sqlite",max_records=1)
    with pytest.raises(ValueError):s.ingest([observation(probe,"PASS",now=100),observation(probe,"FAIL",now=100)])
    assert not s.records();s.close()

def test_storage_corruption_and_future_migration_fail_closed(tmp_path,probe):
    path=tmp_path/"e.sqlite";s=Store(path);s.ingest([observation(probe,"PASS",now=100)])
    s.db.execute("UPDATE records SET hash='corrupt'");s.db.commit()
    with pytest.raises(ValueError):s.records()
    s.db.execute("PRAGMA user_version=99");s.close()
    with pytest.raises(ValueError):Store(path)

def test_bundle_exact_replay_and_tamper(tmp_path,probe):
    r=observation(probe,"FAIL",now=100);report=diagnose([r],100,"GET /orders")
    path=tmp_path/"incident.json";export_bundle(path,[r],report)
    assert replay(path)[0]==report
    bundle=json.loads(path.read_text());bundle["records"][0]["predicate_status"]="PASS";path.write_text(json.dumps(bundle))
    with pytest.raises(ValueError):replay(path)

def test_report_citations_resolve(tmp_path,probe):
    records=[observation(probe,"FAIL",now=100),observation(probe,"PASS",now=100)]
    report=diagnose(records,100);ids={r["id"] for r in records}
    assert all(set(f["supporting"]+f["contradicting"])<=ids for f in report["findings"])
    export_bundle(tmp_path/"report.json",records,report)

@pytest.mark.parametrize("target",["http://127.0.0.1:80/?token=secret","http://user:pass@127.0.0.1/","http://host/#fragment","ftp://host/file","http://host/\r\nX: injected"])
def test_unsafe_url_syntax(target):
    with pytest.raises(ValueError):destination(target)

@pytest.mark.parametrize("address",["169.254.169.254","100.100.100.200","0.0.0.0","224.0.0.1","fe80::1"])
def test_ssrf_special_addresses_denied(probe,manifest,address):
    target="http://["+address+"]/" if ":" in address else "http://"+address+"/"
    m=copy.deepcopy(manifest);m["allowed_targets"]=[target];m["allowed_addresses"]={address:[address]}
    with pytest.raises(PermissionError):resolve(target,m)

def test_rebinding_answers_must_all_be_approved(manifest,monkeypatch):
    target=manifest["allowed_targets"][0]
    monkeypatch.setattr(socket,"getaddrinfo",lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,"",("127.0.0.1",18761)),(socket.AF_INET,socket.SOCK_STREAM,6,"",("169.254.169.254",18761))])
    with pytest.raises(PermissionError):resolve(target,manifest)

def test_manifest_does_not_forge_vantage_or_run_commands(manifest):
    bad=copy.deepcopy(manifest);bad["probes"][0]["vantage"]="external"
    with pytest.raises(ValueError):validate_manifest(bad)
    bad=copy.deepcopy(manifest);bad["probes"][0]["operation"]="shell"
    with pytest.raises(ValueError):validate_manifest(bad)
    validate_manifest(manifest)

@pytest.mark.parametrize("mode",["hang","output","crash","invalid"])
def test_worker_failures_are_bounded(mode):
    code={"hang":"import time; time.sleep(60)","output":"print('x'*100000)","crash":"raise SystemExit(2)","invalid":"print('not JSON')"}[mode]
    start=time.monotonic()
    with pytest.raises(WorkerError):supervise([sys.executable,"-c",code],{},.25,output_limit=1000)
    assert time.monotonic()-start<.7

def test_worker_does_not_read_stdin_still_times_out():
    with pytest.raises(WorkerError):supervise([sys.executable,"-c","import time;time.sleep(60)"],{"data":"x"*60000},.2)

def test_timeout_kills_descendant_group(tmp_path):
    marker=tmp_path/"escaped"
    child="import time;from pathlib import Path;time.sleep(.5);Path("+repr(str(marker))+").write_text('escaped')"
    parent="import subprocess,time,sys;subprocess.Popen([sys.executable,'-c',"+repr(child)+"]);time.sleep(60)"
    with pytest.raises(WorkerError):supervise([sys.executable,"-c",parent],{},.15)
    time.sleep(.55)
    assert not marker.exists()

def test_denied_probe_is_collection_unknown(probe,manifest):
    m=copy.deepcopy(manifest);m["allowed_addresses"]={}
    r=run_probe(probe,m)
    assert r["collector_status"]=="DENIED" and r["predicate_status"]=="UNKNOWN"

@pytest.mark.parametrize("code,status",[(0,"PASS"),(1,"FAIL"),(2,"FAIL"),(3,"UNKNOWN"),(9,"UNKNOWN")])
def test_monitoring_plugin_unknown(probe,code,status):assert from_monitoring_plugin(probe,code,at=100)["predicate_status"]==status

def test_prometheus_stale_and_scrape_failure(probe):
    p={"status":"success","data":{"resultType":"vector","result":[{"value":[100,"4"]}]}}
    r=from_prometheus(probe,p,3)
    assert r["predicate_status"]=="FAIL" and not diagnose([r],1000)["findings"]
    assert from_prometheus(probe,{"status":"error"},3)["collector_status"]=="UNAVAILABLE"
    assert from_prometheus(probe,{"status":"success","data":{"result":[]}},3)["predicate_status"]=="UNKNOWN"

def test_otlp_import(probe):
    data={"resourceMetrics":[{"scopeMetrics":[{"metrics":[{"name":"probe_failure","gauge":{"dataPoints":[{"timeUnixNano":"100000000000","asInt":"1"}]}}]}]}]}
    r=from_otlp_metric(probe,data,"probe_failure",0)
    assert r["predicate_status"]=="FAIL" and r["provenance"]["method"]=="otlp_json_import"

def test_cli_offline_replay_and_unknown_exit(tmp_path,probe):
    r=observation(probe,collector="DENIED",now=time.time());s=Store(tmp_path/"e.sqlite");s.ingest([r]);s.close()
    assert main(["--store",str(tmp_path/"e.sqlite"),"report","--json"])==3
    path=tmp_path/"bundle.json";assert main(["--store",str(tmp_path/"e.sqlite"),"export",str(path)])==0
    assert main(["replay",str(path),"--json"])==0
