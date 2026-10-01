"""Service contracts, chronology and privacy; Docker cases live in the harness."""
import copy
from types import SimpleNamespace
import pytest
from support_evidence.model import observation, clean, digest
from support_evidence.policy import validate_manifest
from support_evidence.modules.postgresql import assess, error_value
from support_evidence.modules.nginx import status_result
from support_evidence.modules.common import CollectionStatus
from support_evidence.diagnose import diagnose, packages
from support_evidence.bundle import export_bundle, replay

STATUS=b'Active connections: 3 \nserver accepts handled requests\n 100 80 300 \nReading: 1 Writing: 1 Waiting: 1 \n'

def pg_probe(probe,operation,expected):
    p=copy.deepcopy(probe);p.update(operation=operation,predicate=operation,target='postgresql://127.0.0.1:5432',expected=expected,credential_ref='SUPPORT_PG')
    return p

class Connection:
    def __init__(self,rows,version=180000):self.rows=iter(rows);self.info=SimpleNamespace(server_version=version)
    def execute(self,query,*args):
        assert 'DELETE' not in query and 'UPDATE' not in query and 'SELECT *' not in query
        return SimpleNamespace(fetchone=lambda:next(self.rows))

@pytest.mark.parametrize('code,reason',[('42501','postgresql_permission'),('55P03','postgresql_lock_unavailable'),('57014','postgresql_query_canceled'),('53300','postgresql_connections_exhausted'),('53100','postgresql_disk_full'),('53200','postgresql_out_of_memory'),('40P01','postgresql_deadlock'),('40001','postgresql_serialization'),('57P03','postgresql_not_ready'),('28P01','postgresql_authentication'),('42P01','postgresql_fixture_missing'),(None,'postgresql_connection_or_startup')])
def test_sqlstate_boundaries(code,reason):
    value=error_value(code,'connect')
    assert value['reason']==reason and set(value)<={'reason','error_code'}
    if code:assert value['error_code']==code

def test_no_localized_error_claims():
    assert 'error_code' not in error_value('password=do-not-retain','connect')
    assert error_value('57014','query')['reason']=='postgresql_query_canceled'

@pytest.mark.parametrize('operation,expected',[
 ('postgresql_activity',{'max_idle_transactions':0}),('postgresql_locks',{'max_blocked_sessions':0}),('postgresql_headroom',{'min_connection_headroom':2}),('postgresql_replication',{'role':'primary','min_standbys':1,'max_replay_bytes':0})])
def test_restricted_statistics_never_zero_health(probe,operation,expected):
    p=pg_probe(probe,operation,expected)
    with pytest.raises(CollectionStatus) as error:assess(Connection([(False,),(False,)]),p)
    assert error.value.collector=='DENIED' and error.value.value['reason']=='postgresql_statistics_visibility'
    assert not error.value.value['statistics_visible']

def test_disabled_or_masked_activity_is_unknown(probe):
    p=pg_probe(probe,'postgresql_activity',{'max_idle_transactions':0})
    with pytest.raises(CollectionStatus) as error:assess(Connection([(False,),(True,),(True,),(3,)]),p)
    assert error.value.value['masked_sessions']==3

@pytest.mark.parametrize('version',[130000,190000])
def test_unverified_diagnostic_version_abstains(probe,version):
    p=pg_probe(probe,'postgresql_role',{'role':'primary'})
    with pytest.raises(CollectionStatus) as error:assess(Connection([],version),p)
    assert error.value.collector=='UNAVAILABLE'

def test_activity_uses_explicit_thresholds(probe):
    p=pg_probe(probe,'postgresql_activity',{'max_idle_transactions':0})
    value,ok=assess(Connection([(False,),(True,),(True,),(0,),(1,2,0,40)]),p)
    assert not ok and value['idle_transactions']==2 and value['reason']=='postgresql_activity_threshold'
    assert 'query' not in value

def test_headroom_includes_reserved_slots_and_probe(probe):
    p=pg_probe(probe,'postgresql_headroom',{'min_connection_headroom':4})
    value,ok=assess(Connection([(False,),(True,),(10,2,3,2)]),p)
    assert value['connection_headroom']==3 and value['reserved_connections']==5 and not ok

@pytest.mark.parametrize('recovery,rows,reason',[
 (False,[(True,),(1,0,None)],'postgresql_replication_unknown'),
 (True,[(None,)],'postgresql_replication_unknown')])
def test_null_replication_is_unknown(probe,recovery,rows,reason):
    p=pg_probe(probe,'postgresql_replication',{'role':'standby' if recovery else 'primary','min_standbys':1,'max_replay_bytes':0})
    with pytest.raises(CollectionStatus) as error:assess(Connection([(recovery,),*rows]),p)
    assert error.value.value['reason']==reason

def test_missing_expected_replica_fails_topology(probe):
    p=pg_probe(probe,'postgresql_replication',{'role':'primary','min_standbys':1,'max_replay_bytes':0})
    value,ok=assess(Connection([(False,),(True,),(0,0,None)]),p)
    assert not ok and value['reason']=='postgresql_standbys_missing' and 'replay_backlog_bytes' not in value

def test_standby_backlog_is_local_not_timestamp_age(probe):
    p=pg_probe(probe,'postgresql_replication',{'role':'standby','max_replay_bytes':10})
    value,ok=assess(Connection([(True,),(12,)]),p)
    assert not ok and value['replay_backlog_bytes']==12

def test_lock_scan_cap_is_unknown(probe):
    p=pg_probe(probe,'postgresql_locks',{'max_blocked_sessions':0})
    with pytest.raises(CollectionStatus) as error:assess(Connection([(False,),(True,),(True,),(0,),(513,)]),p)
    assert error.value.value['reason']=='postgresql_lock_scan_budget'

def test_role_and_xid_age_contracts(probe):
    value,ok=assess(Connection([(True,)]),pg_probe(probe,'postgresql_role',{'role':'primary'}))
    assert not ok and value['reason']=='postgresql_role_mismatch'
    value,ok=assess(Connection([(False,),(20,)]),pg_probe(probe,'postgresql_vacuum',{'max_xid_age':10}))
    assert not ok and value['oldest_xid_age']==20

@pytest.mark.parametrize('status,body,collector',[(403,b'protected','DENIED'),(404,b'missing','UNAVAILABLE'),(502,b'gateway','UNAVAILABLE'),(200,b'customer body','ERROR'),(200,STATUS.replace(b'100 80',b'100 101'),'ERROR')])
def test_status_unavailable_is_not_service_failure(status,body,collector):
    with pytest.raises(CollectionStatus) as error:status_result(status,body,{'max_active_connections':10})
    assert error.value.collector==collector and body.decode().strip() not in str(error.value.value)

def test_historical_counter_gap_does_not_prove_current_loss():
    value,ok=status_result(200,STATUS,{'max_active_connections':5})
    assert ok and value['accepts']>value['handled'] and 'reason' not in value
    assert not status_result(200,STATUS,{'max_active_connections':2})[1]
    with pytest.raises(CollectionStatus):status_result(200,STATUS,{})

@pytest.mark.parametrize('delta',[.1,10])
@pytest.mark.parametrize('collector',['DENIED','TIMEOUT','UNAVAILABLE','ERROR'])
def test_new_unknown_blocks_older_pass(probe,delta,collector):
    passed=observation(probe,'PASS',now=100)
    denied=observation(probe,collector=collector,now=100+delta)
    report=diagnose([passed,denied],100+delta)
    assert passed['id'] not in report['passed'] and any(denied['id'] in u for u in report['unknowns'])
    old_pkgs=[p for p in packages() if p['id'] not in {'package:postgresql','package:nginx'}]
    assert passed['id'] in diagnose([passed,denied],100+delta,rule_packages=old_pkgs,engine_version='0.1.0')['passed']

def test_specific_signature_does_not_inherit_unrelated_support(probe):
    p=pg_probe(probe,'postgresql_read',{})
    canceled=observation(p,'FAIL',value={'reason':'postgresql_query_canceled','error_code':'57014'},now=100)
    missing=observation(p,'FAIL',value={'reason':'postgresql_fixture_missing','error_code':'42P01'},now=100)
    fs=diagnose([canceled,missing],100)['findings']
    assert len(fs)==2
    assert next(f for f in fs if f['rule_id']=='postgresql.query_canceled')['supporting']==[canceled['id']]
    assert next(f for f in fs if f['rule_id']=='postgresql.fixture_missing')['supporting']==[missing['id']]

def test_all_numeric_metadata_survives_storage_export_replay(probe,tmp_path):
    p=pg_probe(probe,'postgresql_activity',{'max_idle_transactions':0})
    value={'reason':'postgresql_activity_threshold','server_version_num':180000,'statistics_visible':True,'in_recovery':False,'active_sessions':2,'idle_transactions':1,'lock_waiters':2,'oldest_transaction_seconds':3.5,'query':'SELECT customer_secret','password':'forbidden'}
    record=clean(observation(p,'FAIL',value=value,now=100));report=diagnose([record],100)
    export_bundle(tmp_path/'bundle.json',[record],report)
    regenerated,records=replay(tmp_path/'bundle.json')
    assert regenerated==report and records[0]['value']['idle_transactions']==1
    assert 'customer_secret' not in str(records) and 'forbidden' not in str(records)

@pytest.mark.parametrize('op,expected',[
 ('postgresql_replication',{'role':'primary','max_replay_bytes':10}),('postgresql_role',{}),('postgresql_locks',{}),('postgresql_activity',{}),('postgresql_headroom',{'min_connection_headroom':-1}),('postgresql_activity',{'query':'SELECT 1'}),('postgresql_read',{'lock_timeout_ms':3000})])
def test_invalid_or_implicit_service_contract_denied(probe,manifest,op,expected):
    p=pg_probe(probe,op,expected);m=copy.deepcopy(manifest);m.update(probes=[p],allowed_targets=[p['target']])
    with pytest.raises(ValueError):validate_manifest(m)

@pytest.mark.parametrize('age',[None,-1])
def test_missing_or_negative_xid_age_abstains(probe,age):
    p=pg_probe(probe,'postgresql_vacuum',{'max_xid_age':100})
    with pytest.raises(CollectionStatus) as error:assess(Connection([(False,),(age,)]),p)
    assert error.value.collector=='UNAVAILABLE'

@pytest.mark.parametrize('path,expected',[
 ('/missing',('UNAVAILABLE','UNKNOWN')),('/denied',('DENIED','UNKNOWN')),
 ('/large',('ERROR','UNKNOWN')),('/status',('OK','PASS'))])
def test_status_wire_collection_retains_only_metadata(probe,manifest,path,expected):
    import http.server
    import threading
    from support_evidence.supervisor import run_probe
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            self.send_response(404 if self.path=='/missing' else 403 if self.path=='/denied' else 200)
            self.end_headers()
            self.wfile.write(b'customer-body-'*6000 if self.path=='/large' else STATUS)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        p=copy.deepcopy(probe);p.update(operation='nginx_stub_status',target=f'http://127.0.0.1:{server.server_address[1]}{path}',expected={'max_active_connections':10})
        m=copy.deepcopy(manifest);m.update(probes=[p],allowed_targets=[p['target']])
        record=run_probe(p,validate_manifest(m))
        assert (record['collector_status'],record['predicate_status'])==expected
        assert 'customer-body' not in str(record) and 'body' not in record['value']
    finally:server.shutdown();server.server_close();thread.join()

def test_unreachable_status_endpoint_is_unknown(probe,manifest):
    import socket
    from support_evidence.supervisor import run_probe
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    p=copy.deepcopy(probe);p.update(operation='nginx_stub_status',target=f'http://127.0.0.1:{port}/status',expected={'max_active_connections':10})
    m=copy.deepcopy(manifest);m.update(probes=[p],allowed_targets=[p['target']])
    record=run_probe(p,validate_manifest(m))
    assert (record['collector_status'],record['predicate_status'])==('UNAVAILABLE','UNKNOWN')

def test_current_signature_packages_cannot_use_legacy_engine(probe):
    with pytest.raises(ValueError):diagnose([observation(probe,'FAIL',now=100)],100,engine_version='0.1.0')

def test_signature_mismatch_cannot_satisfy_required_predicate(probe):
    package=copy.deepcopy(next(p for p in packages() if p['id']=='package:http'))
    rule=package['rules'][0];package['rules']=[rule]
    rule['required_predicates']=['upstream_failed'];rule['match']={'reason':['http_status']}
    triggering=observation(probe,'FAIL',value={'reason':'http_status'},now=100)
    other=copy.deepcopy(probe);other['predicate']='upstream_failed'
    unrelated=observation(other,'FAIL',value={'reason':'oracle_mismatch'},now=100)
    findings=diagnose([triggering,unrelated],100,rule_packages=[package])['findings']
    assert len(findings)==1 and findings[0]['assessment']=='inconclusive'
    assert findings[0]['supporting']==[triggering['id']]
    assert 'missing required predicate:upstream_failed' in findings[0]['unknowns']

def test_connection_contract_does_not_require_query_execution(probe,monkeypatch):
    import sys
    from contextlib import contextmanager
    from support_evidence.modules.postgresql import collect
    def forbidden_query(*args):raise AssertionError('connection acceptance must not require query execution')
    @contextmanager
    def connect(**kwargs):
        assert kwargs['hostaddr']=='127.0.0.1'
        assert 'default_transaction_read_only=on' in kwargs['options']
        yield SimpleNamespace(execute=forbidden_query)
    monkeypatch.setitem(sys.modules,'psycopg',SimpleNamespace(connect=connect,Error=RuntimeError))
    p=pg_probe(probe,'postgresql_connect',{})
    assert collect(p,{},'localhost',5432,'127.0.0.1',{'username':'fixture','password':'disposable-fixture'})=={}
