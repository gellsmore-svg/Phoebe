import copy
import json
import os
import sys
import time
from pathlib import Path
import pytest
from support_evidence.discovery import entity
from support_evidence.store import Store
from support_evidence.model import clean,digest,observation
from support_evidence.supervisor import run_probe
from support_evidence.diagnose import diagnose
from support_evidence.worker import execute

def test_versioned_entity_records_preserve_boot_replacement(tmp_path):
    a=entity('host:stable','host','scope',{'boot_id':'boot1'})
    b=entity('host:stable','host','scope',{'boot_id':'boot2'})
    assert a['logical_id']==b['logical_id'] and a['id']!=b['id']
    s=Store(tmp_path/'e.sqlite');s.ingest([a,b]);assert len(s.records())==2;s.close()

def test_redacted_observation_hash_matches_retained_metadata(probe):
    r=observation(probe,'FAIL',now=100);r['value']['raw_log']='secret=not-retained';r['integrity']='invalid-old-hash'
    retained=clean(r);hash_value=retained.pop('integrity')
    assert hash_value==digest(retained) and 'not-retained' not in str(retained)

def test_aggregate_incident_allows_large_bounded_report(probe):
    records=[]
    for i in range(400):
        p=copy.deepcopy(probe);p['subject']='service:'+str(i);records.append(observation(p,'PASS',now=100))
    assert len(diagnose(records,100)['passed'])==400

def test_schema_copy_matches_runtime():
    from support_evidence.model import SCHEMA
    assert json.loads((Path(__file__).resolve().parents[1]/'schemas/records-v1.json').read_text())==SCHEMA

def test_absent_declared_systemd_unit_is_failed_active_contract(probe):
    p=copy.deepcopy(probe);p.update(operation='systemd',target='support-evidence-definitely-absent-fixture.service')
    result=execute(p,{'allowed_units':[p['target']]})
    assert result['predicate_status']=='FAIL' and result['collector_status']=='OK'
    assert result['value']['state']=='unit_not_available'


def test_empty_evidence_never_silently_becomes_healthy_exit(tmp_path):
    from support_evidence.cli import main
    assert main(['--store',str(tmp_path/'empty.sqlite'),'report','--json'])==3


def test_systemd_unit_cannot_be_a_command_option(probe,manifest):
    from support_evidence.policy import validate_manifest
    p=copy.deepcopy(probe);p.update(operation='systemd',target='-Hremote.service')
    m=copy.deepcopy(manifest);m['probes']=[p];m['allowed_targets']=[p['target']];m['allowed_units']=[p['target']]
    with pytest.raises(ValueError):validate_manifest(m)
