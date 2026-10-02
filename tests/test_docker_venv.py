import copy
import json
import os
import socketserver
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler
import pytest
from support_evidence.worker import execute
from support_evidence.supervisor import run_probe
from support_evidence.policy import validate_manifest
from support_evidence.modules import docker
from support_evidence.modules.common import CollectionStatus
from support_evidence.model import observation
from support_evidence.diagnose import diagnose, packages
from support_evidence.knowledge import attachment, retrieve
from support_evidence.bundle import export_bundle, replay

ID="a"*64

def local(probe,manifest,path,op,expected,identity=None):
    p=copy.deepcopy(probe);p.update(operation=op,predicate=op,target=str(path),route=str(path),expected=expected,instance_id=identity)
    m=copy.deepcopy(manifest);m.update(probes=[p],allowed_targets=[str(path)],allowed_paths=[str(path.resolve())])
    return p,m

def state(status="running",**changes):
    data={"Id":ID,"RestartCount":0,"State":{"Status":status,"Running":status in {"running","paused","restarting"},"Paused":status=="paused","Restarting":status=="restarting","OOMKilled":False,"Dead":status=="dead","ExitCode":0,"StartedAt":"2026-10-02T00:00:00Z"},"HostConfig":{"Memory":100,"PidsLimit":10},"Config":{"Env":["password=never-retain"]}}
    data['State'].update(changes);return data

@pytest.fixture
def api(tmp_path):
    routes={"/version":(200,{"ApiVersion":"1.55","MinAPIVersion":"1.44","Os":"linux"})}
    seen=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.path)
            status,body=routes.get(self.path,(404,{"message":"private-error"}))
            if callable(body): body=body()
            raw=body if isinstance(body,bytes) else json.dumps(body).encode()
            self.send_response(status);self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
        def log_message(self,*args): pass
    class Server(socketserver.UnixStreamServer): pass
    path=tmp_path/'docker.sock';server=Server(str(path),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try: yield path,routes,seen
    finally: server.shutdown();server.server_close();thread.join()

def test_fixed_api_identity_privacy_and_no_context(probe,manifest,api,monkeypatch):
    path,routes,seen=api;routes['/v1.47/containers/'+ID+'/json']=(200,state())
    monkeypatch.setenv('DOCKER_HOST','tcp://private-secret:2375')
    p,m=local(probe,manifest,path,'docker_container',{'container_state':'running','max_restarts':0},ID)
    validate_manifest(m);result=run_probe(p,m)
    assert result['predicate_status']=='PASS'
    assert seen==['/version','/v1.47/containers/'+ID+'/json']
    assert 'never-retain' not in json.dumps(result) and 'private-secret' not in json.dumps(result)

@pytest.mark.parametrize('response,collector,reason',[(401,'DENIED','docker_api_permission'),(403,'DENIED','docker_api_permission'),(500,'UNAVAILABLE','docker_api_unavailable')])
def test_api_gaps_are_unknown(probe,manifest,api,response,collector,reason):
    path,routes,_=api;routes['/version']=(response,b'password=secret-api-body')
    p,m=local(probe,manifest,path,'docker_daemon',{})
    result=execute(p,m);assert result['predicate_status']=='UNKNOWN' and result['collector_status']==collector and result['value']['reason']==reason
    assert 'secret-api-body' not in str(result)

@pytest.mark.parametrize('payload,reason',[(b'[]','docker_response_malformed'),(b'not-json','docker_response_malformed'),(b'x'*32769,'docker_response_budget'),({'ApiVersion':'bad'},'docker_version_malformed'),({'ApiVersion':'1.55','MinAPIVersion':'1.48','Os':'linux'},'docker_api_version_unsupported'),({'ApiVersion':'1.47','Os':'windows'},'docker_platform_unsupported')],ids=['array','invalid-json','oversized','bad-version','unsupported-api','windows'])
def test_bad_daemon_data_abstains(probe,manifest,api,payload,reason):
    path,routes,_=api;routes['/version']=(200,payload)
    p,m=local(probe,manifest,path,'docker_daemon',{})
    result=execute(p,m);assert result['predicate_status']=='UNKNOWN' and result['value']['reason']==reason

@pytest.mark.parametrize('status,reason',[('paused','docker_state_mismatch'),('restarting','docker_state_mismatch'),('exited','docker_state_mismatch'),('dead','docker_state_mismatch')])
def test_state_contracts(status,reason):
    value,ok=docker.state_result(state(status),ID,{'container_state':'running','max_restarts':0})
    assert not ok and value['reason']==reason

def test_oom_and_exit_code_do_not_collapse():
    value,ok=docker.state_result(state('exited',ExitCode=137),ID,{'container_state':'exited','max_restarts':0})
    assert ok and not value['oom_killed']
    value,ok=docker.state_result(state('exited',OOMKilled=True),ID,{'container_state':'exited','max_restarts':0})
    assert not ok and value['reason']=='docker_oom_recorded'
    data=state();data['RestartCount']=4
    assert docker.state_result(data,ID,{'max_restarts':3})[0]['reason']=='docker_restart_threshold'

@pytest.mark.parametrize('change',[{'Id':'b'*64},{'RestartCount':True},{'State':{}},{'State':dict(state()['State'],Running=False)}])
def test_inconsistent_state_unknown(change):
    data=state();data.update(change)
    with pytest.raises(CollectionStatus):docker.state_result(data,ID,{})

@pytest.mark.parametrize('health,known',[(None,None),({'Status':'starting','FailingStreak':0},None),({'Status':'healthy','FailingStreak':0},True),({'Status':'unhealthy','FailingStreak':2,'Log':[{'Output':'secret'}]},False)])
def test_health_distinct_from_running(health,known):
    data=state()
    if health is not None:data['State']['Health']=health
    if known is None:
        with pytest.raises(CollectionStatus):docker.health_result(data,{})
    else:
        value,ok=docker.health_result(data,{})
        assert ok==known and 'secret' not in str(value)

def test_resources_missing_limits_and_race(probe,manifest,api):
    path,routes,_=api;route='/v1.47/containers/'+ID
    data=state();stats={'id':ID,'memory_stats':{'usage':95},'pids_stats':{'current':3}}
    value,ok=docker.resource_result(data,stats,{}, {'min_memory_headroom_bytes':6,'min_pids_headroom':2})
    assert not ok and value['memory_headroom']==5 and value['pids_headroom']==7
    data['HostConfig']['Memory']=0
    with pytest.raises(CollectionStatus):docker.resource_result(data,stats,{}, {'min_memory_headroom_bytes':0})
    calls=[]
    def changing():
        calls.append(1);d=state();d['RestartCount']=len(calls)-1;return d
    routes[route+'/json']=(200,changing);routes[route+'/stats?stream=false']=(200,stats)
    p,m=local(probe,manifest,path,'docker_resources',{'min_pids_headroom':1},ID)
    result=execute(p,m);assert result['predicate_status']=='UNKNOWN' and result['value']['reason']=='docker_container_changed'

def environment(tmp_path):
    env=tmp_path/'env';(env/'bin').mkdir(parents=True);(env/'lib/python3.12/site-packages').mkdir(parents=True)
    (env/'pyvenv.cfg').write_text('home = /usr/bin\nversion = 3.12.3\ninclude-system-site-packages = false\n')
    (env/'bin/python').write_text('#!/bin/sh\ntouch '+str(tmp_path/'executed')+'\n');(env/'bin/python').chmod(0o755)
    (env/'bin/pip').write_text('#!'+str(env/'bin/python')+'\nprint("not executed")\n')
    return env

def dist(env,name,version='1.0',requires=(),python=None):
    path=env/'lib/python3.12/site-packages'/(name+'-'+version+'.dist-info');path.mkdir()
    fields=['Metadata-Version: 2.3','Name: '+name,'Version: '+version,*['Requires-Dist: '+r for r in requires], *(['Provides-Extra: feature'] if any('extra' in r for r in requires) else [])]
    if python:fields.append('Requires-Python: '+python)
    (path/'METADATA').write_text('\n'.join(fields)+'\n\n');return path

@pytest.mark.parametrize('op,expected',[('venv_layout',{'python_version':'3.12'}),('venv_isolation',{'isolated':True}),('venv_dependencies',{'requirements':['app>=1']}),('venv_scripts',{})])
def test_static_pass_never_executes_target(probe,manifest,tmp_path,op,expected):
    env=environment(tmp_path);dist(env,'app');p,m=local(probe,manifest,env,op,expected);m['allowed_paths'].append('/usr/bin')
    validate_manifest(m);result=run_probe(p,m)
    assert result['predicate_status']=='PASS' and not (tmp_path/'executed').exists()

@pytest.mark.parametrize('requires,expected,reason',[(('dep>=2',),['app'],'venv_dependencies_missing'),((),['app>=2'],'venv_dependency_conflict'),(('dep; sys_platform == "win32"',),['app'],'venv_dependency_scope_unknown'),(('dep @ https://example.com/wheel',),['app'],'venv_dependency_scope_unknown')])
def test_dependency_boundaries(probe,manifest,tmp_path,requires,expected,reason):
    env=environment(tmp_path);dist(env,'app',requires=requires)
    p,m=local(probe,manifest,env,'venv_dependencies',{'requirements':expected});result=execute(p,m)
    assert result['value']['reason']==reason
    assert result['predicate_status']==('UNKNOWN' if 'scope_unknown' in reason else 'FAIL')

def test_recursive_extras_cycles_python_markers(probe,manifest,tmp_path):
    env=environment(tmp_path);dist(env,'app',requires=['dep[feature]>=1']);dist(env,'dep',requires=['app','leaf; extra == "feature"','absent; python_version < "3.11"'])
    p,m=local(probe,manifest,env,'venv_dependencies',{'requirements':['app']})
    result=execute(p,m);assert result['value']['missing_dependencies']==1
    dist(env,'leaf');assert execute(p,m)['predicate_status']=='PASS'

def test_requires_python_duplicate_and_hooks(probe,manifest,tmp_path):
    env=environment(tmp_path);path=dist(env,'app',python='>=3.13')
    p,m=local(probe,manifest,env,'venv_dependencies',{'requirements':['app']})
    assert execute(p,m)['value']['reason']=='venv_dependency_conflict'
    (path/'METADATA').write_text('Metadata-Version: 2.3\nName: app\nVersion: 1.0\n')
    hook=env/'lib/python3.12/site-packages/evil.pth';hook.write_text('import os; os.system("touch '+str(tmp_path/'executed')+'")')
    assert execute(p,m)['predicate_status']=='UNKNOWN' and not (tmp_path/'executed').exists()
    hook.unlink();dist(env,'App','2.0')
    assert execute(p,m)['value']['reason']=='venv_duplicate_distribution'

@pytest.mark.parametrize('change,reason',[('isolation','venv_isolation_mismatch'),('version','venv_version_mismatch'),('scripts','venv_script_path_mismatch'),('cfg','venv_configuration_malformed'),('metadata','venv_metadata_malformed'),('symlink','venv_metadata_unsafe_path')])
def test_environment_failures(probe,manifest,tmp_path,change,reason):
    env=environment(tmp_path);path=dist(env,'app');op='venv_layout';expected={'python_version':'3.12'}
    if change=='isolation':op='venv_isolation';expected={'isolated':True};(env/'pyvenv.cfg').write_text((env/'pyvenv.cfg').read_text().replace('false','true'))
    if change=='version':expected={'python_version':'3.13'}
    if change=='scripts':op='venv_scripts';expected={};(env/'bin/pip').write_text('#!/old/env/bin/python\n')
    if change=='cfg':(env/'pyvenv.cfg').write_text('version = bad\n')
    if change in {'metadata','symlink'}:
        op='venv_dependencies';expected={'requirements':['app']};(path/'METADATA').unlink()
        if change=='metadata':(path/'METADATA').write_text('Name: app\n')
        else:(path/'METADATA').symlink_to('/etc/passwd')
    p,m=local(probe,manifest,env,op,expected);m['allowed_paths'].append('/usr/bin')
    result=execute(p,m);assert result['value']['reason']==reason and not (tmp_path/'executed').exists()

@pytest.mark.parametrize('op,expected,identity',[('docker_container',{'container_state':'running','max_restarts':0},'short'),('docker_resources',{},ID),('docker_container',{},ID),('venv_layout',{},None),('venv_dependencies',{'requirements':['app @ https://example.com/a']},None),('venv_isolation',{},None)])
def test_explicit_contract_required(probe,manifest,tmp_path,op,expected,identity):
    p,m=local(probe,manifest,tmp_path/'target',op,expected,identity)
    with pytest.raises(ValueError):validate_manifest(m)

@pytest.mark.parametrize('service,reason,op',[('docker','docker_unhealthy','docker_health'),('venv','venv_dependencies_missing','venv_dependencies')])
def test_new_guidance_and_exact_replay(probe,manifest,tmp_path,service,reason,op):
    p,_=local(probe,manifest,tmp_path/'target',op,{},ID if service=='docker' else None)
    record=observation(p,'FAIL',value={'reason':reason},now=100);report=diagnose([record],100)
    assert report['findings'] and retrieve(service,reason)[0]['card']['service']==service
    knowledge=attachment(report,[record]);export_bundle(tmp_path/'bundle.json',[record],report,knowledge=knowledge)
    regenerated,records,context=replay(tmp_path/'bundle.json',with_knowledge=True)
    assert regenerated==report and context==knowledge

@pytest.mark.parametrize('name',['incident-postgresql-module.json','incident-nginx-module.json'])
def test_frozen_02_guidance_replay(name):
    report,_,context=replay(Path(__file__).resolve().parents[1]/'examples'/name,with_knowledge=True)
    assert report['engine_version']=='0.2.0' and context['context']['retrieval_version']=='bm25-1'


def test_denied_socket_and_deadline(probe,manifest,api):
    import time
    path,routes,_=api
    p,m=local(probe,manifest,path,'docker_daemon',{})
    path.chmod(0)
    assert run_probe(p,m)['collector_status']=='DENIED'
    path.chmod(0o600)
    def delayed():time.sleep(1);return {'ApiVersion':'1.47','Os':'linux'}
    routes['/version']=(200,delayed);p['timeout']=.3
    started=time.monotonic();result=run_probe(p,m)
    assert result['predicate_status']=='UNKNOWN' and time.monotonic()-started<1

def test_venv_nonregular_budget_and_unsupported_extra(probe,manifest,tmp_path):
    env=environment(tmp_path);path=dist(env,'app')
    p,m=local(probe,manifest,env,'venv_dependencies',{'requirements':['app[unknown]']})
    assert execute(p,m)['predicate_status']=='UNKNOWN'
    (path/'METADATA').write_bytes(b'x'*262145)
    assert execute(p,m)['value']['reason']=='venv_metadata_budget'
    (path/'METADATA').unlink();os.mkfifo(path/'METADATA')
    assert execute(p,m)['value']['reason']=='venv_metadata_not_regular'

def test_target_routes_do_not_share_support(probe,manifest,tmp_path):
    first,_=local(probe,manifest,tmp_path/'first','venv_dependencies',{'requirements':['app']})
    second,_=local(probe,manifest,tmp_path/'second','venv_dependencies',{'requirements':['app']})
    fail=observation(first,'FAIL',value={'reason':'venv_dependencies_missing'},now=100)
    passed=observation(second,'PASS',now=100)
    findings=diagnose([fail,passed],100)['findings']
    assert len(findings)==1 and not findings[0]['contradicting']


def test_nondirectory_environment_fails_structure(probe,manifest,tmp_path):
    target=tmp_path/'file';target.write_text('untrusted')
    p,m=local(probe,manifest,target,'venv_layout',{'python_version':'3.12'})
    result=execute(p,m)
    assert result['predicate_status']=='FAIL' and result['value']['reason']=='venv_root_not_directory'


@pytest.mark.parametrize('change',['identity','target','vantage','route'])
def test_worker_rechecks_local_policy(probe,manifest,api,change):
    path,routes,seen=api
    p,m=local(probe,manifest,path,'docker_container',{'container_state':'running','max_restarts':0},ID)
    if change=='identity':p['instance_id']=ID+'/../../logs'
    if change=='target':m['allowed_targets']=[]
    if change=='vantage':m['agent_vantage']='local:another'
    if change=='route':p['route']='unscoped'
    result=execute(p,m)
    assert result['predicate_status']=='UNKNOWN' and not seen
