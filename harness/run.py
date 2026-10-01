"""Real disposable Docker injection. All names have a unique owned prefix.
Run as cello. Never select or mutate existing containers/services.
"""
import copy
import json
import os
import platform
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.request import urlopen
import pymongo
import psycopg
from support_evidence.model import canonical,observation
from support_evidence.policy import validate_manifest
from support_evidence.supervisor import run_probe
from support_evidence.diagnose import diagnose,render
from support_evidence.bundle import export_bundle
from support_evidence.discovery import assertion
from support_evidence.discovery import nginx_metadata
from pymongo import monitoring
import threading

ROOT=Path(__file__).resolve().parents[1]
PREFIX='support-evidence-'+uuid.uuid4().hex[:10]
OUT=ROOT/'.harness'/PREFIX
IMAGES={'app':'support-evidence-fixture:0.1.0','mongo':'mongo:8.0','pg':'postgres:18','nginx':'nginx:1.28-alpine','blackbox':'prom/blackbox-exporter:v0.28.0','storage':'support-evidence-fixture:0.1.0'}
CREDS={'mongo_admin':'disposable-admin-only','pg_admin':'disposable-admin-only','reader':'disposable-read-only'}
created=[];results=[];ports={};names={};blocker=None

def command(args,check=True,timeout=120):
    r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if check and r.returncode:raise RuntimeError('command failed: '+args[0]+' '+args[1]+'\n'+r.stderr[-2000:])
    return r.stdout.strip()

def docker(*args,**kwargs):return command(['docker',*args],**kwargs)

def start(kind,*args,command_args=()):
    name=PREFIX+'-'+kind;names[kind]=name
    args=list(args)
    for i,value in enumerate(args):
        if value.startswith('127.0.0.1::'):
            with socket.socket() as reserved:
                reserved.bind(('127.0.0.1',0));port=reserved.getsockname()[1]
            args[i]='127.0.0.1:'+str(port)+':'+value.split('::')[1]
    docker('run','-d','--name',name,'--label','support-evidence.harness='+PREFIX,'--network',PREFIX,'--memory','512m','--cpus','1','--security-opt','no-new-privileges',*args,IMAGES[kind],*command_args)
    created.append(name)
    info=json.loads(docker('inspect',name))[0]
    published=info['NetworkSettings']['Ports']
    for mappings in published.values():
        if mappings:ports[kind]=int(mappings[0]['HostPort']);break
    return name

def wait_for(fn,seconds=45):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        try:fn();return
        except Exception:time.sleep(.25)
    raise RuntimeError('disposable fixture did not become ready')

def probe(op,target,subject='service:opaque',predicate=None,route=None,expected=None,ref=None,vantage='local:host'):
    p={'schema_version':1,'kind':'probe','id':'probe:'+uuid.uuid4().hex,'subject':subject,'instance_id':None,'operation':op,'predicate':predicate or op,'target':target,'vantage':vantage,'namespace':'current','route':route or op,'timeout':5 if op.startswith(('mongodb','postgresql')) else 3,'interval':30,'freshness':60,'cost':'low','side_effect':'read_only','expected':expected or {}}
    if ref:p['credential_ref']=ref
    return p

def manifest(probes,extra_addresses=None):
    return validate_manifest({'schema_version':1,'scope':PREFIX,'agent_vantage':probes[0]['vantage'],'allowed_targets':[p['target'] for p in probes],'allowed_addresses':{'127.0.0.1':['127.0.0.1'],**(extra_addresses or {})},'allowed_paths':[p['target'] for p in probes if p['operation'] in {'unix','filesystem'}],'allowed_units':[p['target'] for p in probes if p['operation']=='systemd_user'],'probes':probes,'entities':[],'assertions':[],'impact_contract':'GET /orders authoritative ok=true'})

def observe(probes):
    m=manifest(probes);return [run_probe(p,m) for p in probes]

def save_case(name,records,expected_boundaries,expected_statuses=None,notes='real disposable injection'):
    started=time.monotonic();report=diagnose(records,time.time(),'GET /orders authoritative ok=true')
    actual={f['boundary'] for f in report['findings'] if f['assessment'] in {'strong','moderate'}}
    ok=set(expected_boundaries)<=actual
    if expected_statuses:ok=ok and [r['predicate_status'] for r in records if r['kind']=='observation']==expected_statuses
    ids={r['id'] for r in records};traceable=all(set(f['supporting']+f['contradicting'])<=ids for f in report['findings'])
    export_bundle(OUT/(name+'.json'),records,report)
    (OUT/(name+'.txt')).write_text(render(report,records))
    results.append({'case':name,'passed':ok,'boundaries':sorted(actual),'expected':sorted(expected_boundaries),'evidence_traceability':traceable,'diagnosis_ms':round((time.monotonic()-started)*1000,3),'notes':notes,'false_causal_claims':0 if all('initiating cause unverified' in f['unknowns'] for f in report['findings']) else None})
    print(name+': '+('PASS' if ok else 'FAIL'),flush=True)
    return report

def remote(probes,appip,kind='external'):
    m=manifest(probes,{'app':[appip]})
    request=canonical({'probes':probes,'manifest':m})
    code="import json,sys;from support_evidence.supervisor import run_probe;d=json.loads(sys.argv[1]);print(json.dumps([run_probe(p,d['manifest']) for p in d['probes']]))"
    # Execution in an independent network namespace, not a relabelled local result.
    return json.loads(docker('exec',names[kind],'python','-c',code,request,timeout=30))

def main():
    global blocker
    if os.getuid()==0:raise SystemExit('Run harness as cello, not root')
    OUT.mkdir(parents=True,mode=0o700)
    before=set(docker('ps','-a','--format','{{.Names}}').splitlines())
    try:
        print('Building isolated fixture image...',flush=True)
        docker('build','-f',str(ROOT/'harness/Dockerfile'),'-t',IMAGES['app'],str(ROOT),timeout=240)
        for kind in ['mongo','pg','nginx','blackbox']:
            print('Fetching '+IMAGES[kind],flush=True);docker('pull',IMAGES[kind],timeout=180)
        docker('network','create','--label','support-evidence.harness='+PREFIX,PREFIX)
        start('mongo','-p','127.0.0.1::27017','-e','MONGO_INITDB_ROOT_USERNAME=admin','-e','MONGO_INITDB_ROOT_PASSWORD='+CREDS['mongo_admin'],command_args=('mongod','--setParameter','enableTestCommands=1'))
        start('pg','-p','127.0.0.1::5432','-e','POSTGRES_USER=admin','-e','POSTGRES_PASSWORD='+CREDS['pg_admin'],'-e','POSTGRES_DB=support')
        start('app','--network-alias','app','-p','127.0.0.1::8080','--cap-drop','ALL')
        names['external']=PREFIX+'-external';docker('run','-d','--name',names['external'],'--label','support-evidence.harness='+PREFIX,'--network',PREFIX,'--memory','256m','--cpus','.5','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges',IMAGES['app'],'python','-c','import time;time.sleep(600)');created.append(names['external'])
        upstream='http://'+names['app']+':8080'
        conf=OUT/'nginx.conf';conf.write_text('events {}\nhttp {server {listen 8080; location / {proxy_pass '+upstream+';}}}\n')
        start('nginx','-p','127.0.0.1::8080','--mount','type=bind,src='+str(conf)+',dst=/etc/nginx/nginx.conf,readonly')
        wait_for(lambda:urlopen('http://127.0.0.1:'+str(ports['app'])+'/orders',timeout=1).read())
        def mongo_connect():
            c=pymongo.MongoClient('127.0.0.1',ports['mongo'],username='admin',password=CREDS['mongo_admin'],serverSelectionTimeoutMS=500);c.admin.command('ping');return c
        wait_for(mongo_connect);mc=mongo_connect()
        mc.support.support_probe.insert_one({'_id':1,'fixture':True})
        mc.support.command('createUser','reader',pwd=CREDS['reader'],roles=[{'role':'read','db':'support'}])
        def pg_connect():return psycopg.connect(host='127.0.0.1',port=ports['pg'],user='admin',password=CREDS['pg_admin'],dbname='support',connect_timeout=1,autocommit=True)
        wait_for(pg_connect);pg=pg_connect()
        pg.execute('CREATE TABLE support_probe(id integer PRIMARY KEY)');pg.execute('INSERT INTO support_probe VALUES(1)')
        pg.execute("CREATE USER reader WITH PASSWORD 'disposable-read-only'");pg.execute('GRANT CONNECT ON DATABASE support TO reader');pg.execute('GRANT USAGE ON SCHEMA public TO reader');pg.execute('GRANT SELECT ON support_probe TO reader')
        os.environ['SUPPORT_MONGO']=canonical({'username':'reader','password':CREDS['reader'],'database':'support','auth_source':'support'})
        os.environ['SUPPORT_PG']=canonical({'username':'reader','password':CREDS['reader'],'database':'support'})
        app_url='http://127.0.0.1:'+str(ports['app']);proxy_url='http://127.0.0.1:'+str(ports['nginx'])
        http=probe('http',proxy_url+'/orders',expected={'status':200,'json_key':'ok','json_value':True},route='/orders')
        ready=probe('http',app_url+'/ready',predicate='readiness',route='/ready',expected={'status':200})
        mongo=probe('mongodb_read','mongodb://127.0.0.1:'+str(ports['mongo']),subject='database:mongo',ref='SUPPORT_MONGO')
        mongo_ping=probe('mongodb_ping',mongo['target'],subject='database:mongo',ref='SUPPORT_MONGO')
        pgread=probe('postgresql_read','postgresql://127.0.0.1:'+str(ports['pg']),subject='database:pg',ref='SUPPORT_PG')
        pgconn=probe('postgresql_connect',pgread['target'],subject='database:pg',ref='SUPPORT_PG')
        save_case('healthy-control',observe([http,ready,mongo,pgread]),[],['PASS']*4)
        docker('exec',names['app'],'python','-c',"from pathlib import Path;Path('/tmp/fixture-mode').write_text('semantic-error')")
        save_case('green-readiness-failed-oracle',observe([ready,http]),['HTTP route/functional contract'],['PASS','FAIL'])
        no_oracle=copy.deepcopy(http);no_oracle['expected']={'status':200}
        save_case('semantic-error-without-oracle',observe([no_oracle]),[],['PASS'],notes='actual wrong business response; no supplied oracle means unknown correctness')
        docker('exec',names['app'],'python','-c',"from pathlib import Path;Path('/tmp/fixture-mode').unlink()")
        conf.write_text('events {}\nhttp {server {listen 8080; location / {proxy_pass http://'+names['app']+':65530;}}}\n');docker('exec',names['nginx'],'nginx','-s','reload');time.sleep(.3)
        save_case('wrong-nginx-upstream-port',observe([http,ready])+nginx_metadata(conf.read_text(),PREFIX,time.time()),['HTTP route/functional contract'],['FAIL','PASS'])
        conf.write_text('events {}\nhttp {server {listen 8080; location / {proxy_pass http://unix:/tmp/missing-upstream.sock:;}}}\n');docker('exec',names['nginx'],'nginx','-s','reload');time.sleep(.3)
        save_case('wrong-nginx-upstream-unix',observe([http])+nginx_metadata(conf.read_text(),PREFIX,time.time()),['HTTP route/functional contract'],['FAIL'])
        save_case('absent-unix-listener',observe([probe('unix',str(OUT/'missing.sock'))]),['listener/connectivity'],['FAIL'])
        conf.write_text('events {}\nhttp {server {listen 8080; location / {proxy_pass '+upstream+';}}}\n');docker('exec',names['nginx'],'nginx','-s','reload');time.sleep(.3)
        docker('stop',names['app']);save_case('stopped-python',observe([ready,http,probe('tcp','tcp://127.0.0.1:'+str(ports['app']),predicate='application_listener')]),['HTTP route/functional contract','listener/connectivity'],['FAIL','FAIL','FAIL']);docker('start',names['app']);wait_for(lambda:urlopen(app_url+'/orders',timeout=1).read())
        # PostgreSQL lock is held only in the disposable database. Connection still succeeds.
        locker=pg_connect();locker.autocommit=False;locker.execute('LOCK TABLE support_probe IN ACCESS EXCLUSIVE MODE')
        save_case('postgres-connection-pass-blocked-query',observe([pgconn,pgread]),['database representative operation'],['PASS','FAIL']);locker.rollback();locker.close()
        mc.admin.command('configureFailPoint','failCommand',mode={'times':1},data={'failCommands':['find'],'blockConnection':True,'blockTimeMS':7000,'appName':'support-evidence-probe'})
        save_case('mongo-ping-pass-delayed-read',observe([mongo_ping,mongo]),['database representative operation'],['PASS','FAIL'])
        mc.admin.command('configureFailPoint','failCommand',mode='off')
        # Real application-driver checkout exhaustion; no server connection metric is substituted.
        class PoolEvents(monitoring.ConnectionPoolListener):
            def __init__(self):self.started={};self.waits=[];self.timeouts=0;self.acquired=threading.Event()
            def connection_check_out_started(self,event):self.started[threading.get_ident()]=time.monotonic()
            def connection_check_out_failed(self,event):
                self.waits.append((time.monotonic()-self.started.get(threading.get_ident(),time.monotonic()))*1000)
                if event.reason=='timeout':self.timeouts+=1
            def connection_checked_out(self,event):self.acquired.set()
            def pool_created(self,event):pass
            def pool_ready(self,event):pass
            def pool_cleared(self,event):pass
            def pool_closed(self,event):pass
            def connection_created(self,event):pass
            def connection_ready(self,event):pass
            def connection_closed(self,event):pass
            def connection_checked_in(self,event):pass
        events=PoolEvents()
        application_driver=pymongo.MongoClient('127.0.0.1',ports['mongo'],username='reader',password=CREDS['reader'],authSource='support',appname='support-evidence-app',maxPoolSize=1,waitQueueTimeoutMS=400,serverSelectionTimeoutMS=1000,socketTimeoutMS=5000,event_listeners=[events],retryReads=False)
        application_driver.admin.command('ping');events.acquired.clear()
        mc.admin.command('configureFailPoint','failCommand',mode={'times':1},data={'failCommands':['find'],'blockConnection':True,'blockTimeMS':2000,'appName':'support-evidence-app'})
        def holding_read():
            try:application_driver.support.support_probe.find_one({'_id':1})
            except pymongo.errors.PyMongoError:pass
        holder=threading.Thread(target=holding_read);holder.start()
        if not events.acquired.wait(2):raise RuntimeError('pool fixture failed to acquire connection')
        try:application_driver.support.support_probe.find_one({'_id':1})
        except pymongo.errors.WaitQueueTimeoutError:pass
        driver_wait=probe('driver_checkout_wait',mongo['target'],subject='service:application-driver',predicate='checkout_wait_over_budget',route='driver_checkout')
        driver_timeout=copy.deepcopy(driver_wait);driver_timeout['operation']='driver_checkout_timeout';driver_timeout['predicate']='checkout_timeout_present'
        event_time=time.time()
        a=observation(driver_wait,'FAIL' if max(events.waits or [0])>=350 else 'PASS',value={'checkout_wait_ms':max(events.waits or [0])},method='application_driver_events',now=event_time)
        b=observation(driver_timeout,'FAIL' if events.timeouts else 'PASS',value={'checkout_timeouts':events.timeouts},method='application_driver_events',now=event_time)
        a['dependence_group']=b['dependence_group']='application:driver-pool-events'
        save_case('instrumented-application-driver-checkout',[a,b],['application driver checkout'],['FAIL','FAIL'])
        holder.join(5);application_driver.close();mc.admin.command('configureFailPoint','failCommand',mode='off')
        mc.support.command('updateUser','reader',pwd='revoked-fixture-password')
        save_case('mongo-revoked-credentials',observe([mongo]),['database representative operation'],['FAIL'])
        mc.support.command('updateUser','reader',pwd=CREDS['reader'])
        pg.execute("ALTER USER reader WITH PASSWORD 'revoked-fixture-password'")
        save_case('postgres-revoked-credentials',observe([pgread]),['database representative operation'],['FAIL'])
        pg.execute("ALTER USER reader WITH PASSWORD 'disposable-read-only'")
        docker('stop',names['mongo']);save_case('stopped-mongo',observe([mongo_ping,mongo]),['database reachability/authentication','database representative operation'],['FAIL','FAIL']);docker('start',names['mongo']);wait_for(mongo_connect)
        appip=json.loads(docker('inspect',names['app']))[0]['NetworkSettings']['Networks'][PREFIX]['IPAddress']
        remote_http=probe('http','http://app:8080/orders',expected={'status':200,'json_key':'ok','json_value':True},vantage='external:container',route='/orders')
        save_case('external-independent-vantage',remote([remote_http],appip),[],['PASS'])
        denied_remote=copy.deepcopy(remote_http);denied_remote['target']='http://app:65530/orders'
        save_case('external-failure-local-pass',observe([ready])+remote([denied_remote],appip),['HTTP route/functional contract'],['PASS','FAIL'])
        start('storage','--tmpfs','/volume:rw,size=65536,nr_inodes=64,uid=1000,gid=1000','--cap-drop','ALL')
        fs=probe('filesystem','/volume',subject='storage:fixture',expected={'min_free_bytes':1,'min_free_inodes':0},vantage='external:volume')
        fill="from pathlib import Path; p=Path('/volume/fill'); f=p.open('wb'); f.write(b'x'*65536); f.close()"
        docker('exec',names['storage'],'python','-c',fill)
        save_case('bounded-volume-capacity-exhaustion',remote([fs],appip,'storage'),['filesystem capacity/inodes'],['FAIL'])
        docker('exec',names['storage'],'python','-c',"from pathlib import Path;Path('/volume/fill').unlink()")
        fill="from pathlib import Path\nfor i in range(100):\n try:Path('/volume/f'+str(i)).touch()\n except OSError:break"
        docker('exec',names['storage'],'python','-c',fill)
        fs['expected']={'min_free_bytes':0,'min_free_inodes':1}
        save_case('bounded-volume-inode-exhaustion',remote([fs],appip,'storage'),['filesystem capacity/inodes'],['FAIL'])
        bad_dns=probe('dns','missing.support-evidence.invalid');m=manifest([bad_dns]);m['allowed_addresses'][bad_dns['target']]=['127.0.0.1']
        save_case('dns-failure',[run_probe(bad_dns,m)],['DNS resolution'],['FAIL'])
        # Two independent real faults remain separate boundaries, never a forced cause.
        locker=pg_connect();locker.autocommit=False;locker.execute('LOCK TABLE support_probe IN ACCESS EXCLUSIVE MODE');docker('stop',names['app'])
        save_case('two-simultaneous-faults',observe([ready,pgread]),['HTTP route/functional contract','database representative operation'],['FAIL','FAIL']);locker.rollback();locker.close();docker('start',names['app'])
        # Temporal topology cases are synthetic assertions, explicitly labelled.
        a=assertion('service:opaque','database:mongo','DEPENDS_ON','INTENDED',time.time()-1)
        b=assertion('service:opaque','database:new','CONNECTS_TO','OBSERVED',time.time()-1)
        save_case('topology-drift-fixture',[a,b],[],notes='contract fixture; not an observed trace capture')
        # Existing-tool baseline on the same active wrong-port HTTP target.
        config=OUT/'blackbox.yml';config.write_text('modules:\n  http_fixture:\n    prober: http\n    timeout: 3s\n    http:\n      valid_status_codes: [200]\n      follow_redirects: false\n')
        start('blackbox','-p','127.0.0.1::9115','--mount','type=bind,src='+str(config)+',dst=/etc/blackbox_exporter/config.yml,readonly')
        target='http://'+names['app']+':65530/orders'
        wait_for(lambda:urlopen('http://127.0.0.1:'+str(ports['blackbox'])+'/',timeout=1).read())
        import urllib.parse
        metrics=urlopen('http://127.0.0.1:'+str(ports['blackbox'])+'/probe?module=http_fixture&target='+urllib.parse.quote(target,safe=''),timeout=5).read().decode()
        (OUT/'blackbox-control.prom').write_text(metrics)
        comparison={'existing_tool':'Blackbox Exporter v0.28.0','target':target,'raw_status_detects_failure':'probe_success 0' in metrics,'incremental_report_features':['retained evidence IDs','operation/vantage scope','unknown cause','bounded next check','offline replay'],'operator_benefit':'not yet measured','coroot':'not installed; comparative study pending'}
        (OUT/'comparison.json').write_text(json.dumps(comparison,indent=2))
        mc.close();pg.close()
    except Exception as e:
        blocker=str(e);print('HARNESS ERROR: '+blocker,flush=True)
    finally:
        for name in reversed(created):docker('rm','-f','-v',name,check=False)
        docker('network','rm',PREFIX,check=False)
        after=set(docker('ps','-a','--format','{{.Names}}').splitlines())
        summary={'schema_version':1,'prefix':PREFIX,'environment':{'python':platform.python_version(),'kernel':platform.release(),'platform':platform.platform()},'images':IMAGES,'image_ids':{k:json.loads(docker('image','inspect',v))[0]['Id'] for k,v in IMAGES.items()},'image_digests':{k:json.loads(docker('image','inspect',v))[0].get('RepoDigests',[]) for k,v in IMAGES.items()},'cases':results,'blocker':blocker,'cleanup_complete':not any(n.startswith(PREFIX) for n in after),'unrelated_containers_preserved':before<=after,'ground_truth_location':'harness only, not incident evidence','limitations':['Coroot comparison pending','unfamiliar operator study pending','no production performance claim']}
        (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print('Results: '+str(OUT/'summary.json'),flush=True)
    return 0 if not blocker and all(r['passed'] for r in results) else 1

if __name__=='__main__':raise SystemExit(main())
