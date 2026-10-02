"""A missing diagnostic prerequisite does not fail a service contract."""
class CollectionStatus(Exception):
    def __init__(self, collector, reason, **metadata):
        self.collector = collector
        self.value = {"reason": reason, **metadata}


def validate_local_probe(probe, manifest):
    """Recheck policy inside the isolated worker before any local target access."""
    from ..model import validate
    from .contracts import validate_service_contract
    validate({k:v for k,v in probe.items() if k != "_deadline"})
    validate_service_contract(probe)
    if probe["target"] not in manifest.get("allowed_targets",[]) or probe["vantage"] != manifest.get("agent_vantage") or probe["namespace"] != "current":
        raise PermissionError("local_probe_policy")
