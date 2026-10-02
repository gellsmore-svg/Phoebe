"""Actual disposable Engine/venv checks; never select existing containers.
Run as cello. Container OOM fixture is capped at 64 MiB; no host exhaustion.
"""
import copy
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from support_evidence.model import clean
from support_evidence.policy import validate_manifest
from support_evidence.supervisor import run_probe
from support_evidence.diagnose import diagnose
from support_evidence.knowledge import attachment
from support_evidence.bundle import export_bundle, replay

ROOT=Path(__file__).resolve().parents[1]
PREFIX="phoebe-docker-venv-"+uuid.uuid4().hex[:10]
OUT=ROOT/'.harness'/PREFIX;OUT.mkdir(parents=True)
SOCKET=Path('/var/run/docker.sock').resolve()
created=[];results=[];snapshots={}

def command(*args):
    return subprocess.run(list(args),check=True,capture_output=True,text=True,timeout=45).stdout.strip()
def engine(*args): return command('docker',*args)
def start(kind,*args,image='alpine:3',cmd=('sleep','120')):
    name=PREFIX+'-'+kind;created.append(name)
    return engine('run','-d','--name',name,'--label','support-evidence.harness='+PREFIX,'--memory','64m','--cpus','.5','--pids-limit','32','--network','none',*args,image,*cmd)
def wait_health(identity,status):
    end=time.monotonic()+12
    while time.monotonic()<end:
        data=json.loads(engine('inspect',identity))[0]
        if data['State'].get('Health',{}).get('Status')==status:return
        time.sleep(.2)
    raise AssertionError('fixture health convergence')
def probe(op,target,expected,identity=None):
    return {'schema_version':1,'kind':'probe','id':'probe:'+op,'subject':'service:'+('container' if op.startswith('docker') else 'venv'),'instance_id':identity,'operation':op,'predicate':op,'target':str(target),'vantage':'local:cello-harness','namespace':'current','route':str(target),'timeout':4,'interval':30,'freshness':60,'cost':'bounded','side_effect':'read_only','expected':expected}
def case(name,p,want,reason=None,paths=()):
    manifest={'schema_version':1,'scope':name,'agent_vantage':p['vantage'],'allowed_targets':[p['target']],'allowed_addresses':{},'allowed_paths':[str(Path(p['target']).resolve()),*map(str,paths)],'allowed_units':[],'probes':[p],'entities':[],'assertions':[],'impact_contract':name}
    validate_manifest(manifest);record=clean(run_probe(p,manifest))
    assert record['predicate_status']==want,(name,record)
    if reason:assert record['value'].get('reason')==reason,(name,record)
    report=diagnose([record],time.time(),name);knowledge=attachment(report,[record])
    bundle=OUT/(name+'.json');export_bundle(bundle,[record],report,knowledge=knowledge)
    assert replay(bundle,with_knowledge=True)==(report,[record],knowledge)
    if want=='PASS':assert not report['findings']
    results.append({'name':name,'collector':record['collector_status'],'predicate':want,'reason':record['value'].get('reason'),'bundle_replay':True,'guidance_documents':sum(len(e['documents']) for e in knowledge['context']['entries']),'reference':'actual local disposable fixture'})
    snapshots[name]=bundle

before=set(engine('ps','-aq').splitlines())
try:
    case('docker-daemon',probe('docker_daemon',SOCKET,{}),'PASS')
    healthy=start('healthy','--health-cmd','test -f /etc/alpine-release','--health-interval','1s','--health-retries','1');wait_health(healthy,'healthy')
    unhealthy=start('unhealthy','--health-cmd','false','--health-interval','1s','--health-retries','1');wait_health(unhealthy,'unhealthy')
    plain=start('plain')
    contract={'container_state':'running','max_restarts':0}
    case('docker-running',probe('docker_container',SOCKET,contract,healthy),'PASS')
    case('docker-healthy',probe('docker_health',SOCKET,{},healthy),'PASS')
    case('docker-unhealthy',probe('docker_health',SOCKET,{},unhealthy),'FAIL','docker_unhealthy')
    case('docker-no-health',probe('docker_health',SOCKET,{},plain),'UNKNOWN','docker_health_not_configured')
    case('docker-resources-control',probe('docker_resources',SOCKET,{'min_memory_headroom_bytes':1,'min_pids_headroom':1},healthy),'PASS')
    case('docker-resource-threshold',probe('docker_resources',SOCKET,{'min_memory_headroom_bytes':64*1024*1024+1},healthy),'FAIL','docker_resource_threshold')
    engine('pause',plain);case('docker-paused',probe('docker_container',SOCKET,contract,plain),'FAIL','docker_state_mismatch');engine('unpause',plain)
    engine('restart',plain);case('docker-manual-restart',probe('docker_container',SOCKET,contract,plain),'PASS')
    looping=start('looping','--restart','on-failure:5',cmd=('sh','-c','sleep 3; exit 1'))
    end=time.monotonic()+15
    while time.monotonic()<end:
        info=json.loads(engine('inspect',looping))[0]
        if info['RestartCount']>0 and info['State']['Status']=='running': break
        time.sleep(.1)
    else:raise AssertionError('restart fixture convergence')
    case('docker-restart-threshold',probe('docker_container',SOCKET,contract,looping),'FAIL','docker_restart_threshold')
    engine('stop','-t','1',plain);case('docker-stopped',probe('docker_container',SOCKET,contract,plain),'FAIL','docker_state_mismatch')
    engine('rm',plain);case('docker-missing',probe('docker_container',SOCKET,contract,plain),'FAIL','docker_container_missing');created.remove(PREFIX+'-plain')
    oom=start('oom',image='support-evidence-fixture:0.1.0',cmd=('python','-c','import time; time.sleep(.1); bytearray(256*1024*1024)'))
    engine('wait',oom);case('docker-oom',probe('docker_container',SOCKET,contract,oom),'FAIL','docker_oom_recorded')
    env=OUT/'environment';command(sys.executable,'-m','venv',str(env))
    cfg={key.strip():value.strip() for key,value in (line.split('=',1) for line in (env/'pyvenv.cfg').read_text().splitlines() if '=' in line)}
    home=Path(cfg['home'].strip()).resolve();exe=(env/'bin/python').resolve();version=cfg['version'].strip();minor='.'.join(version.split('.')[:2])
    case('venv-layout',probe('venv_layout',env,{'python_version':minor}),'PASS',paths=[home,exe])
    case('venv-isolation',probe('venv_isolation',env,{'isolated':True}),'PASS')
    case('venv-scripts',probe('venv_scripts',env,{}),'PASS')
    case('venv-dependencies',probe('venv_dependencies',env,{'requirements':['pip']}),'PASS')
    case('venv-version-mismatch',probe('venv_layout',env,{'python_version':'3.13' if minor!='3.13' else '3.14'}),'FAIL','venv_version_mismatch',paths=[home,exe])
    case('venv-missing-dependency',probe('venv_dependencies',env,{'requirements':['phoebe-deliberately-absent>=1']}),'FAIL','venv_dependencies_missing')
    moved=OUT/'moved';env.rename(moved)
    case('venv-moved-scripts',probe('venv_scripts',moved,{}),'FAIL','venv_script_path_mismatch')
    cfgpath=moved/'pyvenv.cfg';original=cfgpath.read_text();cfgpath.write_text(original.replace('include-system-site-packages = false','include-system-site-packages = true'))
    case('venv-isolation-mismatch',probe('venv_isolation',moved,{'isolated':True}),'FAIL','venv_isolation_mismatch')
    case('venv-external-packages',probe('venv_dependencies',moved,{'requirements':['pip']}),'UNKNOWN','venv_system_packages_unmeasured')
    cfgpath.write_text(original);(moved/'bin/python').unlink()
    case('venv-broken-interpreter',probe('venv_layout',moved,{'python_version':minor}),'FAIL','venv_interpreter_missing',paths=[home,exe])
    cfgpath.write_text('version = invalid\n');case('venv-malformed-cfg',probe('venv_isolation',moved,{'isolated':True}),'UNKNOWN','venv_configuration_malformed')
    cfgpath.unlink();case('venv-missing-cfg',probe('venv_isolation',moved,{'isolated':True}),'FAIL','venv_configuration_missing')
    result={'run_id':PREFIX,'cases':results,'count':len(results),'all_passed':True,'user':os.getuid(),'existing_containers_preserved':before<=set(engine('ps','-aq').splitlines()),'limitations':['local Linux Engine only; no remote/rootless deployment integration','venv tests use trusted local Python creation; product never executes the target interpreter','memory threshold and bounded container OOM; no host exhaustion or production fault injection','no native imports, ABI, actual service interpreter, Windows venv or filesystem-wide atomic snapshot validation']}
    (ROOT/'docs/docker-venv-validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    for name,case_name in [('docker','docker-unhealthy'),('venv','venv-missing-dependency')]:
        (ROOT/'examples'/('incident-'+name+'-module.json')).write_bytes(snapshots[case_name].read_bytes())
    print(json.dumps(result))
finally:
    for name in reversed(created):subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=20)
    assert before<=set(engine('ps','-aq').splitlines()),'existing container disappeared during validation'
