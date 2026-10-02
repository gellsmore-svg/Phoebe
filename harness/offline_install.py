"""Install, offline replay and removal verification in a disposable venv."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
wheelhouse=root/'dist/wheelhouse'
fixture=root/'examples/incident-mongo-operation.json'
if not fixture.exists():raise SystemExit('Create verified checked-in example bundle before packaging check')
with tempfile.TemporaryDirectory(prefix='support-evidence-install-') as tmp:
    env=Path(tmp)/'venv';subprocess.run([sys.executable,'-m','venv',str(env)],check=True)
    def run(*args):return subprocess.run(list(args),check=True,capture_output=True,text=True)
    run(str(env/'bin/pip'),'install','--no-index','--find-links',str(wheelhouse),'support-evidence==0.3.0')
    cfg={k.strip():v.strip() for k,v in (line.split('=',1) for line in (env/'pyvenv.cfg').read_text().splitlines() if '=' in line)}
    probe={'schema_version':1,'kind':'probe','id':'probe:installed-venv','subject':'service:offline-install','instance_id':'release:offline-test','operation':'venv_layout','predicate':'static_layout','target':str(env),'vantage':'local:offline-test','namespace':'current','route':str(env),'timeout':3,'interval':30,'freshness':60,'cost':'bounded','side_effect':'read_only','expected':{'python_version':cfg['version']}}
    manifest={'schema_version':1,'scope':'offline installed static venv check','agent_vantage':probe['vantage'],'allowed_targets':[str(env)],'allowed_addresses':{},'allowed_paths':[str(env.resolve()),str(Path(cfg['home']).resolve()),str((env/'bin/python').resolve())],'allowed_units':[],'probes':[probe],'entities':[],'assertions':[]}
    manifest_path=Path(tmp)/'manifest.json';manifest_path.write_text(json.dumps(manifest))
    checked=json.loads(run(str(env/'bin/support-evidence'),'--store',str(Path(tmp)/'store.sqlite'),'check',str(manifest_path),'--json').stdout)
    assert checked['passed'] and not checked['findings']
    replay=run(str(env/'bin/support-evidence'),'replay',str(fixture),'--json')
    report=json.loads(replay.stdout);assert report['kind']=='incident'
    for name in ['incident-postgresql-module.json','incident-nginx-module.json','incident-docker-module.json','incident-venv-module.json']:
        enriched=json.loads(run(str(env/'bin/support-evidence'),'replay',str(root/'examples'/name),'--json').stdout)
        assert enriched['knowledge']['entries'] and enriched['report']['kind']=='incident'
    hits=json.loads(run(str(env/'bin/support-evidence'),'knowledge','search','nginx','nginx_gateway_timeout','--json').stdout)
    assert hits and hits[0]['card']['service']=='nginx'
    for service,query in [('docker','docker_unhealthy'),('venv','venv_dependencies_missing')]:
        hits=json.loads(run(str(env/'bin/support-evidence'),'knowledge','search',service,query,'--json').stdout)
        assert hits and hits[0]['card']['service']==service
    run(str(env/'bin/pip'),'uninstall','-y','support-evidence')
    after=subprocess.run([str(env/'bin/python'),'-c','import support_evidence'],capture_output=True)
    assert after.returncode!=0
    result={'offline_install':True,'installed_venv_probe':True,'offline_replay':True,'removal':True,'reference':'Python/Linux local wheelhouse','network_required':False,'store':'no retained user store deleted'}
    out=root/'.harness'/'offline-install.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
