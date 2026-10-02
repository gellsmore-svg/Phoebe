"""Grounding, corpus isolation, citation integrity and genuine legacy compatibility."""
import copy
import json
from pathlib import Path
import pytest
from support_evidence.model import observation, clean, digest
from support_evidence.knowledge import corpus, retrieve, attachment, augment, validate_card, refresh_sources
from support_evidence.diagnose import diagnose
from support_evidence.bundle import export_bundle, replay
from support_evidence.cli import main

ROOT=Path(__file__).resolve().parents[1]

def service_record(probe,reason='postgresql_query_canceled',collector='OK',now=100):
    p=copy.deepcopy(probe);p.update(operation='postgresql_read',predicate='fixture_read')
    return clean(observation(p,'FAIL' if collector=='OK' else 'UNKNOWN',collector,{'reason':reason},now=now))

@pytest.mark.parametrize('query,expected',[('postgresql_query_canceled 57014','doc:pg-sqlstate'),('postgresql_statistics_visibility','doc:pg-visibility'),('postgresql_headroom_threshold','doc:pg-headroom')])
def test_retrieval_returns_relevant_inspectable_primary_source(query,expected):
    hits=retrieve('postgres',query)
    assert hits[0]['card']['id']==expected
    assert all(h['card']['source']['url'].startswith('https://www.postgresql.org/docs/18/') for h in hits)
    assert hits==retrieve('postgresql',query)

def test_unrelated_query_abstains_and_service_filter_holds():
    assert retrieve('postgresql','penguins bananas rocketships')==[]
    assert all(h['card']['service']=='nginx' for h in retrieve('nginx','nginx_gateway_timeout 504'))
    assert retrieve('nginx','the and nginx')==[]

def test_grounded_generation_cites_docs_and_separate_evidence(probe):
    record=service_record(probe);report=diagnose([record],100);unchanged=copy.deepcopy(report)
    value=attachment(report,[record]);entry=value['context']['entries'][0]
    assert report==unchanged and value['context']['runtime_evidence'] is False
    assert entry['evidence_ids']==[record['id']] and entry['finding_id']==report['findings'][0]['id']
    assert any(d['id']=='doc:pg-sqlstate' for d in entry['documents'])
    assert 'does not establish' in entry['explanation']

def test_unknown_and_stale_collectors_receive_guidance(probe):
    unknown=service_record(probe,'postgresql_statistics_visibility','DENIED')
    p=copy.deepcopy(probe);p['operation']='postgresql_activity'
    unknown=clean(observation(p,collector='DENIED',value={'reason':'postgresql_statistics_visibility'},now=100))
    report=diagnose([unknown],100);entry=attachment(report,[unknown])['context']['entries'][0]
    assert not report['findings'] and entry['observations'][0]['predicate_status']=='UNKNOWN'
    assert entry['documents'][0]['id']=='doc:pg-visibility'
    stale=service_record(probe,now=1)
    entry=attachment(diagnose([stale],100),[stale])['context']['entries'][0]
    assert entry['observations'][0]['freshness']=='stale' and entry['finding_id'] is None

def test_embedded_sources_replay_without_installed_corpus(probe,tmp_path,monkeypatch):
    record=service_record(probe);report=diagnose([record],100);knowledge=attachment(report,[record])
    path=tmp_path/'rag.json';export_bundle(path,[record],report,knowledge=knowledge)
    assert json.loads(path.read_text())['schema_version']==2
    import support_evidence.knowledge as module
    monkeypatch.setattr(module,'corpus',lambda:(_ for _ in ()).throw(RuntimeError('no corpus or network available')))
    assert replay(path,with_knowledge=True)==(report,[record],knowledge)

def test_forged_citation_rejected_even_with_rehashed_envelope(probe,tmp_path):
    record=service_record(probe);report=diagnose([record],100);knowledge=attachment(report,[record]);path=tmp_path/'rag.json'
    export_bundle(path,[record],report,knowledge=knowledge)
    data=json.loads(path.read_text());data['knowledge']['context']['entries'][0]['documents'][0]['source']['url']='https://nginx.org/en/docs/control.html'
    data.pop('integrity');data['integrity']=digest(data);path.write_text(json.dumps(data))
    with pytest.raises(ValueError):replay(path)

def test_bad_card_hash_or_authority_rejected():
    card=copy.deepcopy(corpus()[0]);card['summary']='Changed without a corpus revision'
    with pytest.raises(ValueError):validate_card(card)
    card['source']['url']='http://169.254.169.254/latest/meta-data/'
    card['integrity']=digest({k:v for k,v in card.items() if k!='integrity'})
    with pytest.raises(ValueError):validate_card(card)

@pytest.mark.parametrize('path',[ROOT/'examples'/name for name in ['incident-concurrent-faults.json','incident-driver-checkout.json','incident-misleading-readiness.json','incident-mongo-operation.json','incident-postgres-operation.json']],ids=lambda p:p.name)
def test_genuine_pre_change_bundles_replay_exactly(path):
    original=json.loads(path.read_text())
    assert original['report']['engine_version']=='0.1.0'
    assert replay(path)[0]==original['report']

def test_cli_rag_json_is_explicit_and_replay_has_guidance(probe,tmp_path,capsys):
    record=service_record(probe,now=100);input_path=tmp_path/'records.json';input_path.write_text(json.dumps([record]))
    store=str(tmp_path/'store.sqlite');path=tmp_path/'out.json'
    assert main(['--store',store,'ingest',str(input_path)])==0
    assert main(['--store',store,'export',str(path),'--at','100','--rag'])==0
    capsys.readouterr()
    assert main(['replay',str(path),'--json'])==0
    data=json.loads(capsys.readouterr().out)
    assert data['knowledge']['entries'] and data['report']['engine_version']==__import__('support_evidence').__version__

def test_refresh_uses_fixed_inventory_and_secret_free_process(monkeypatch):
    import support_evidence.supervisor as supervisor
    calls=[]
    monkeypatch.setenv('SUPPORT_PG','not-to-forward')
    def fake(argv,request,timeout,env,output_limit):
        calls.append((argv,request,timeout,env,output_limit))
        return {'source_sha256':'a'*64}
    monkeypatch.setattr(supervisor,'supervise',fake)
    receipts=refresh_sources()
    assert calls and {c[1]['url'] for c in calls}=={c['source']['url'] for c in corpus()}
    assert all('SUPPORT_PG' not in c[3] and c[2]<=5 and c[4]==4096 for c in calls)
    assert receipts['summaries_changed'] is False and all(s['review_required'] for s in receipts['sources'])

def test_cli_partial_source_refresh_is_explicit(tmp_path,monkeypatch,capsys):
    import support_evidence.cli as cli
    receipt={'schema_version':1,'kind':'source_refresh_audit','sources':[{'url':'https://nginx.org/en/docs/control.html','status':'unavailable','review_required':True}],'summaries_changed':False}
    monkeypatch.setattr(cli,'refresh_sources',lambda:receipt)
    path=tmp_path/'receipt.json'
    assert main(['knowledge','refresh','--output',str(path)])==3
    assert '0/1 sources fetched' in capsys.readouterr().out and json.loads(path.read_text())==receipt
