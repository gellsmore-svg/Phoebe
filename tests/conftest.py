import pytest

@pytest.fixture
def probe():
    return {"schema_version":1,"kind":"probe","id":"probe:test","subject":"service:app","instance_id":None,"operation":"http","predicate":"user_path","target":"http://127.0.0.1:18761/orders","vantage":"local:test","namespace":"current","route":"/orders","timeout":2,"interval":30,"freshness":60,"cost":"low","side_effect":"read_only","expected":{"status":200}}

@pytest.fixture
def manifest(probe):
    return {"schema_version":1,"scope":"test","agent_vantage":probe["vantage"],"allowed_targets":[probe["target"]],"allowed_addresses":{"127.0.0.1":["127.0.0.1"]},"allowed_paths":[],"allowed_units":[],"probes":[probe],"entities":[],"assertions":[],"impact_contract":"GET /orders"}
