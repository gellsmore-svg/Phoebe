"""Measured offline performance; no synthetic timing claims."""
import json
import platform
import resource
import time
from pathlib import Path
from support_evidence.model import observation,canonical
from support_evidence.diagnose import diagnose
from support_evidence.bundle import export_bundle,replay
root=Path(__file__).resolve().parents[1];out=root/'.harness'/('benchmark-'+str(time.time_ns()));out.mkdir(parents=True)
base={'schema_version':1,'kind':'probe','id':'probe:benchmark','subject':'service:benchmark','operation':'http','predicate':'status','target':'http://127.0.0.1:1/','vantage':'local:benchmark','namespace':'current','route':'/','timeout':2,'interval':30,'freshness':60,'cost':'low','side_effect':'read_only','expected':{'status':200}}
records=[];now=time.time()
for i in range(1000):
    p=dict(base);p['subject']='service:'+str(i)
    records.append(observation(p,'FAIL' if i%100==0 else 'PASS',now=now))
start=time.perf_counter();report=diagnose(records,now,'1000 distinct scoped HTTP contracts');elapsed=time.perf_counter()-start
export_bundle(out/'incident.json',records,report);assert replay(out/'incident.json')[0]==report
size=(out/'incident.json').stat().st_size;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
cpu_model=next((s.split(':',1)[1].strip() for s in Path('/proc/cpuinfo').read_text().splitlines() if s.startswith('model name')),'unknown')
result={'workload':'1000 observations, distinct subjects, 10 failed contracts, no network/LLM/source index','hardware':{'cpu':cpu_model,'kernel':platform.release(),'python':platform.python_version(),'logical_cpus':__import__('os').cpu_count()},'diagnosis_seconds':elapsed,'peak_rss_bytes':rss,'bundle_bytes':size,'findings':len(report['findings']),'budgets':{'seconds':2,'rss_bytes':128*1024*1024,'bundle_bytes':8*1024*1024},'passed':elapsed<2 and rss<128*1024*1024 and size<8*1024*1024,'replay_equal':True,'limits':'CLI workload only; continuous agent overhead unmeasured'}
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));print(out)
raise SystemExit(0 if result['passed'] else 1)
