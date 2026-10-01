"""Temporal graph projection; relations never create causal evidence."""
from .model import digest

def project(records, at):
    entities = sorted([r for r in records if r["kind"]=="entity"],key=lambda r:r["id"])
    edges = sorted([r for r in records if r["kind"]=="assertion" and r["valid_from"]<=at and (r["valid_until"] is None or at<r["valid_until"])],key=lambda r:r["id"])
    declared={(e["source"],e["target"],e["relation"],e.get("route"),e.get("operation")) for e in edges if e["view"]=="INTENDED"}
    observed={(e["source"],e["target"],e["relation"],e.get("route"),e.get("operation")) for e in edges if e["view"]=="OBSERVED"}
    drift=[]
    for e in edges:
        key=(e["source"],e["target"],e["relation"],e.get("route"),e.get("operation"))
        if e["view"]=="OBSERVED" and key not in declared:
            drift.append({"type":"undeclared_observed_relationship","assertion_id":e["id"],"evidence_ids":e["evidence_ids"]})
        if e["view"]=="INTENDED" and key not in observed:
            drift.append({"type":"declared_not_observed","assertion_id":e["id"],"caveat":"collection and workload coverage do not establish absence"})
    grouped={}
    for e in entities: grouped.setdefault((e["scope"],e["logical_id"]),[]).append(e)
    for key,items in sorted(grouped.items()):
        versions={e.get("technology_version") for e in items if e.get("technology_version")}
        if len(versions)>1: drift.append({"type":"version_conflict","entity_ids":[e["id"] for e in items]})
        instances={e.get("instance_id") for e in items if e.get("instance_id")}
        if len(instances)>1: drift.append({"type":"multiple_instances_identity_requires_reconciliation","entity_ids":[e["id"] for e in items]})
    graph={"entity_ids":[e["id"] for e in entities],"assertion_ids":[e["id"] for e in edges],"drift":drift,"views":{v:[e["id"] for e in edges if e["view"]==v] for v in ["INTENDED","DISCOVERED","OBSERVED"]},"coverage":"partial; no absence or causal propagation inferred"}
    graph["revision"]=digest({"entities":entities,"assertions":edges})
    return graph
