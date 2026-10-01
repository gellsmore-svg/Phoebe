"""Real PostgreSQL 18/Nginx 1.28 checks in uniquely owned disposable containers.

Threshold edge cases measure actual counters; they do not simulate exhaustion,
wraparound or complete replication failures. No production resources are selected.
"""
import copy
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
import psycopg
import run as fixture
from support_evidence.bundle import export_bundle, replay
from support_evidence.diagnose import diagnose, render
from support_evidence.knowledge import attachment, render_context
from support_evidence.model import clean, canonical
from support_evidence.supervisor import run_probe

ROOT=Path(__file__).resolve().parents[1]
results=[];snapshots={};admin=None;locker=None;waiter=None
APP_CODE='''import http.server,json,time
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  if self.path=="/slow":time.sleep(1)
  self.send_response(200);self.end_headers()
  try:self.wfile.write(json.dumps({"ok":self.path!="/wrong"}).encode())
  except BrokenPipeError:pass
http.server.ThreadingHTTPServer(("0.0.0.0",8080),Handler).serve_forever()
'''

def url_status(url):
    try:
        with urlopen(url,timeout=2) as response:return response.status
    except HTTPError as error:return error.code

def wait_status(url,status):
    def check():
        if url_status(url)!=status:raise ValueError('fixture has not converged')
    fixture.wait_for(check,10)

def case(name,probes,expected,notes='actual disposable service observation',reason=None):
    manifest=fixture.manifest(probes,{'localhost':['127.0.0.1','::1']})
    records=[clean(run_probe(p,manifest)) for p in probes]
    actual=[(r['collector_status'],r['predicate_status']) for r in records]
    report=diagnose(records,time.time(),name);knowledge=attachment(report,records)
    path=fixture.OUT/(name+'.json');export_bundle(path,records,report,knowledge=knowledge)
    regenerated,retained,embedded=replay(path,with_knowledge=True)
    ok=actual==expected and regenerated==report and embedded==knowledge
    if reason:ok=ok and records[0]['value'].get('reason')==reason
    if any(r['predicate_status']!='PASS' for r in records):ok=ok and bool(knowledge['context']['entries'])
    (fixture.OUT/(name+'.txt')).write_text(render(report,records)+render_context(knowledge['context']))
    snapshots[name]=(path,report)
    results.append({'case':name,'passed':ok,'observed':[{'collector':r['collector_status'],'predicate':r['predicate_status'],'reason':r['value'].get('reason')} for r in records],'notes':notes,'embedded_rag_replay':regenerated==report and embedded==knowledge})
    print(name+': '+('PASS' if ok else 'FAIL')+' '+str(actual),flush=True)
    return records

def main():
    global admin,locker,waiter
    if os.getuid()==0:raise SystemExit('Run as cello')
    fixture.OUT.mkdir(parents=True,mode=0o700)
    before=set(fixture.docker('ps','-a','--format','{{.Names}}').splitlines())
    try:
        for kind in ['pg','nginx','app']:
            if not fixture.command(['docker','image','inspect',fixture.IMAGES[kind]],check=False):
                if kind=='app':fixture.docker('build','-f',str(ROOT/'harness/Dockerfile'),'-t',fixture.IMAGES['app'],str(ROOT),timeout=240)
                else:fixture.docker('pull',fixture.IMAGES[kind],timeout=180)
        fixture.docker('network','create','--label','support-evidence.harness='+fixture.PREFIX,fixture.PREFIX)
        fixture.start('pg','-p','127.0.0.1::5432','-e','POSTGRES_USER=admin','-e','POSTGRES_PASSWORD='+fixture.CREDS['pg_admin'],'-e','POSTGRES_DB=support')
        fixture.start('app','--network-alias','app','-p','127.0.0.1::8080','--cap-drop','ALL',command_args=('python','-u','-c',APP_CODE))
        def connect():return psycopg.connect(host='127.0.0.1',port=fixture.ports['pg'],user='admin',password=fixture.CREDS['pg_admin'],dbname='support',autocommit=True,connect_timeout=1)
        def ready():
            with connect():pass
        fixture.wait_for(ready);admin=connect()
        admin.execute('CREATE TABLE public.support_probe(id integer PRIMARY KEY)');admin.execute('INSERT INTO public.support_probe VALUES(1)')
        admin.execute("CREATE USER reader WITH PASSWORD 'disposable-read-only'")
        admin.execute("CREATE USER observer WITH PASSWORD 'disposable-read-only'")
        admin.execute('GRANT SELECT ON public.support_probe TO reader, observer');admin.execute('GRANT pg_read_all_stats TO observer')
        os.environ['SUPPORT_PG']=canonical({'username':'reader','password':fixture.CREDS['reader'],'database':'support'})
        os.environ['SUPPORT_PG_STATS']=canonical({'username':'observer','password':fixture.CREDS['reader'],'database':'support'})
        os.environ['SUPPORT_PG_BAD']=canonical({'username':'reader','password':'disposable-wrong','database':'support'})
        target='postgresql://127.0.0.1:'+str(fixture.ports['pg'])
        def pg(op,expected=None,ref='SUPPORT_PG_STATS'):
            return fixture.probe(op,target,subject='database:pg',expected=expected,ref=ref)
        read=pg('postgresql_read',ref='SUPPORT_PG');connection=pg('postgresql_connect',ref='SUPPORT_PG')
        case('pg-functional-control',[connection,read],[('OK','PASS')]*2)
        case('pg-authentication-rejected',[pg('postgresql_connect',ref='SUPPORT_PG_BAD')],[('OK','FAIL')],notes='real driver authentication rejection; libpq may omit SQLSTATE')
        activity=pg('postgresql_activity',{'max_idle_transactions':0,'max_transaction_seconds':30})
        case('pg-restricted-statistics',[pg('postgresql_activity',{'max_idle_transactions':0},ref='SUPPORT_PG')],[('DENIED','UNKNOWN')],reason='postgresql_statistics_visibility')
        case('pg-monitoring-control',[activity,pg('postgresql_locks',{'max_blocked_sessions':0}),pg('postgresql_headroom',{'min_connection_headroom':1}),pg('postgresql_role',{'role':'primary'}),pg('postgresql_vacuum',{'max_xid_age':1000000000})],[('OK','PASS')]*5)
        case('pg-role-mismatch',[pg('postgresql_role',{'role':'standby'})],[('OK','FAIL')],reason='postgresql_role_mismatch')
        case('pg-missing-declared-replica',[pg('postgresql_replication',{'role':'primary','min_standbys':1,'max_replay_bytes':0})],[('OK','FAIL')],notes='declared replica absent in this primary-only fixture',reason='postgresql_standbys_missing')
        case('pg-headroom-contract-edge',[pg('postgresql_headroom',{'min_connection_headroom':100000})],[('OK','FAIL')],notes='actual headroom against intentionally unattainable minimum; no exhaustion injected',reason='postgresql_headroom_threshold')
        case('pg-xid-contract-edge',[pg('postgresql_vacuum',{'max_xid_age':0})],[('OK','FAIL')],notes='actual frozen-XID age against zero limit; no wraparound injected',reason='postgresql_xid_age_threshold')
        locker=connect();locker.autocommit=False;locker.execute('LOCK TABLE public.support_probe IN ACCESS EXCLUSIVE MODE')
        case('pg-connected-blocked-read',[connection,read],[('OK','PASS'),('OK','FAIL')])
        bounded=copy.deepcopy(read);bounded['expected']={'lock_timeout_ms':200}
        case('pg-lock-deadline',[bounded],[('OK','FAIL')],reason='postgresql_lock_unavailable')
        waiter=connect();waiter.autocommit=False
        import threading
        errors=[]
        def wait_read():
            try:waiter.execute('SELECT count(*) FROM public.support_probe')
            except psycopg.Error:errors.append('interrupted')
        thread=threading.Thread(target=wait_read,daemon=True);thread.start()
        fixture.wait_for(lambda:admin.execute("SELECT 1 / CASE WHEN count(*) > 0 THEN 1 ELSE 0 END FROM pg_stat_activity WHERE wait_event_type='Lock'").fetchone())
        case('pg-observed-blocker',[pg('postgresql_locks',{'max_blocked_sessions':0}),pg('postgresql_activity',{'max_idle_transactions':0})],[('OK','FAIL')]*2,notes='real held table lock, blocked reader and idle transaction')
        locker.rollback();locker.close();locker=None;thread.join(timeout=3);waiter.rollback();waiter.close();waiter=None
        admin.execute('REVOKE SELECT ON public.support_probe FROM reader')
        case('pg-denied-fixture-contract',[read],[('OK','FAIL')],reason='postgresql_permission')
        admin.execute('GRANT SELECT ON public.support_probe TO reader');admin.execute('ALTER TABLE public.support_probe RENAME TO missing_fixture')
        case('pg-missing-fixture',[read],[('OK','FAIL')],reason='postgresql_fixture_missing')
        admin.execute('ALTER TABLE public.missing_fixture RENAME TO support_probe')
        conf=fixture.OUT/'nginx.conf'
        def config(upstream):
            conf.write_text('events {}\nhttp {server {listen 8080 default_server; server_name _; return 404;} server {listen 8080; server_name localhost; location = /status {stub_status;} location = /denied {return 403;} location = /bad-status {return 200 "discard-this-body";} location / {proxy_read_timeout 200ms; proxy_pass '+upstream+';}}}\n')
        upstream='http://'+fixture.names['app']+':8080';config(upstream)
        fixture.start('nginx','-p','127.0.0.1::8080','--mount','type=bind,src='+str(conf)+',dst=/etc/nginx/nginx.conf,readonly')
        proxy='http://localhost:'+str(fixture.ports['nginx']);app='http://127.0.0.1:'+str(fixture.ports['app'])
        wait_status(proxy+'/orders',200)
        route=fixture.probe('nginx_http',proxy+'/orders',subject='proxy:nginx',expected={'status':200,'json_key':'ok','json_value':True})
        status=fixture.probe('nginx_stub_status',proxy+'/status',subject='proxy:nginx',expected={'max_active_connections':100})
        case('nginx-route-status-control',[route,status],[('OK','PASS')]*2)
        case('nginx-wrong-host',[fixture.probe('nginx_http',proxy.replace('localhost','127.0.0.1')+'/orders',expected={'status':200})],[('OK','FAIL')],reason='nginx_route_missing')
        wrong=copy.deepcopy(route);wrong['target']=proxy+'/wrong'
        case('nginx-functional-oracle',[wrong],[('OK','FAIL')],reason='oracle_mismatch')
        denied=copy.deepcopy(status);denied['target']=proxy+'/denied'
        case('nginx-status-permission',[denied],[('DENIED','UNKNOWN')],reason='nginx_status_permission')
        malformed=copy.deepcopy(status);malformed['target']=proxy+'/bad-status'
        case('nginx-malformed-status',[malformed],[('ERROR','UNKNOWN')],reason='nginx_status_malformed')
        edge=copy.deepcopy(status);edge['expected']={'max_active_connections':0}
        case('nginx-client-contract-edge',[edge],[('OK','FAIL')],notes='actual client count includes the probe; no saturation injected',reason='nginx_active_threshold')
        slow=copy.deepcopy(route);slow['target']=proxy+'/slow'
        direct=fixture.probe('http',app+'/slow',expected={'status':200,'json_key':'ok','json_value':True})
        case('nginx-upstream-inactivity',[slow,direct],[('OK','FAIL'),('OK','PASS')],reason='nginx_gateway_timeout')
        config('http://'+fixture.names['app']+':65530');fixture.docker('exec',fixture.names['nginx'],'nginx','-s','reload');wait_status(proxy+'/orders',502)
        direct=fixture.probe('http',app+'/orders',expected={'status':200,'json_key':'ok','json_value':True})
        case('nginx-upstream-refusal',[route,direct,status],[('OK','FAIL'),('OK','PASS'),('OK','PASS')],reason='nginx_bad_gateway')
        config(upstream);fixture.docker('exec',fixture.names['nginx'],'nginx','-s','reload');wait_status(proxy+'/orders',200)
        conf.write_text('events {}\nhttp { invalid_directive; }\n')
        rejected=subprocess.run(['docker','exec',fixture.names['nginx'],'nginx','-s','reload'],capture_output=True,timeout=5)
        if rejected.returncode==0:raise RuntimeError('invalid fixture reload unexpectedly accepted')
        case('nginx-rejected-reload-old-route',[route],[('OK','PASS')],notes='actual invalid reload command rejected; previous route continues serving')
        for name,dest in [('pg-connected-blocked-read','incident-postgresql-module.json'),('nginx-upstream-refusal','incident-nginx-module.json')]:
            (ROOT/'examples'/dest).write_text(snapshots[name][0].read_text())
    finally:
        if locker:locker.rollback();locker.close()
        if waiter:waiter.cancel();waiter.close()
        if admin:admin.close()
        for name in reversed(fixture.created):fixture.docker('rm','-f',name,check=False)
        fixture.docker('network','rm',fixture.PREFIX,check=False)
        after=set(fixture.docker('ps','-a','--format','{{.Names}}').splitlines())
        preserved=before<=after and not any(n.startswith(fixture.PREFIX) for n in after)
        data={'tested_at':time.time(),'versions':{'postgresql':'18','nginx':'1.28-alpine'},'actual_service_cases':len(results),'cases':results,'existing_containers_preserved_and_owned_resources_removed':preserved,'simulation_notes':'NULL replication, version rejection, SQLSTATE variants and masked statistics beyond ordinary denial use unit doubles; no replicated standby, exhaustion or wraparound was injected.'}
        (ROOT/'docs/service-module-results.json').write_text(json.dumps(data,indent=2)+'\n')
        print('Owned fixtures removed; existing containers preserved:',preserved,flush=True)
    return 0 if results and all(r['passed'] for r in results) and preserved else 1

if __name__=='__main__':raise SystemExit(main())
