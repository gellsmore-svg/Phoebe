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
    run(str(env/'bin/pip'),'install','--no-index','--find-links',str(wheelhouse),'support-evidence==0.2.0')
    replay=run(str(env/'bin/support-evidence'),'replay',str(fixture),'--json')
    report=json.loads(replay.stdout);assert report['kind']=='incident'
    for name in ['incident-postgresql-module.json','incident-nginx-module.json']:
        enriched=json.loads(run(str(env/'bin/support-evidence'),'replay',str(root/'examples'/name),'--json').stdout)
        assert enriched['knowledge']['entries'] and enriched['report']['kind']=='incident'
    hits=json.loads(run(str(env/'bin/support-evidence'),'knowledge','search','nginx','nginx_gateway_timeout','--json').stdout)
    assert hits and hits[0]['card']['service']=='nginx'
    run(str(env/'bin/pip'),'uninstall','-y','support-evidence')
    after=subprocess.run([str(env/'bin/python'),'-c','import support_evidence'],capture_output=True)
    assert after.returncode!=0
    result={'offline_install':True,'offline_replay':True,'removal':True,'reference':'Python/Linux local wheelhouse','network_required':False,'store':'no retained user store deleted'}
    out=root/'.harness'/'offline-install.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
