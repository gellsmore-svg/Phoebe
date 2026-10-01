"""Real isolated user-manager systemd acceptance; no privileged system-unit writes."""
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from support_evidence.supervisor import run_probe
from support_evidence.policy import validate_manifest
from support_evidence.diagnose import diagnose
from support_evidence.bundle import export_bundle

if os.getuid()==0:raise SystemExit('Run as cello')
os.environ['XDG_RUNTIME_DIR']='/run/user/'+str(os.getuid())
root=Path(__file__).resolve().parents[1];out=root/'.harness'/('systemd-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
unit='support-evidence-fixture-'+uuid.uuid4().hex[:8]+'.service'
result={'unit':unit,'manager':'real Linux systemd user manager','fault':'stopped isolated transient Python process','scope':'no system-level privilege or unit installation tested'}
try:
    subprocess.run(['systemd-run','--user','--unit',unit,'--property=RuntimeMaxSec=120','--property=MemoryMax=64M',sys.executable,'-c','import time; time.sleep(120)'],check=True,capture_output=True)
    p={'schema_version':1,'kind':'probe','id':'probe:systemd-fixture','subject':'service:python-fixture','operation':'systemd_user','predicate':'active','target':unit,'vantage':'local:systemd-user','namespace':'current','route':'service-state','timeout':3,'interval':30,'freshness':60,'cost':'low','side_effect':'read_only','expected':{}}
    m=validate_manifest({'schema_version':1,'agent_vantage':p['vantage'],'allowed_targets':[unit],'allowed_units':[unit],'probes':[p]})
    healthy=run_probe(p,m);result['healthy']=healthy['predicate_status']
    subprocess.run(['systemctl','--user','stop',unit],check=True,capture_output=True)
    failed=run_probe(p,m);result['stopped']=failed['predicate_status']
    report=diagnose([failed],time.time(),'Python service active-state contract')
    result['findings']=[f['boundary'] for f in report['findings']]
    result['passed']=healthy['predicate_status']=='PASS' and failed['predicate_status']=='FAIL' and 'service/process' in result['findings']
    export_bundle(out/'incident.json',[failed],report)
except Exception as e:
    result['passed']=False;result['blocker']=type(e).__name__
finally:
    subprocess.run(['systemctl','--user','stop',unit],capture_output=True)
    subprocess.run(['systemctl','--user','reset-failed',unit],capture_output=True)
    result['cleanup']='transient unit stopped and failed-state reset'
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));print(out)
raise SystemExit(0 if result['passed'] else 1)
