"""Deterministic ordinal support gates; no ranking implies a causal model."""
import json
from importlib.resources import files
from . import __version__
from .graph import project
from .model import validate, digest, freshness, scope

NEXT_CHECKS={
 "inspect_service_state":"Read allowlisted systemd state and independent listener evidence.",
 "collect_host_metrics":"Collect bounded host aggregates from the existing exporter.",
 "probe_dns":"Repeat allowlisted DNS resolution from the affected vantage.",
 "probe_connection":"Check the declared listener and route from the affected namespace.",
 "probe_tls":"Check certificate validity/hostname from the affected vantage.",
 "collect_filesystem":"Read capacity and inode headroom on the relevant allowlisted path.",
 "probe_upstream_http":"Compare proxy route with a separately declared upstream HTTP contract.",
 "probe_database_read":"Run the registered bounded representative fixture read with monitoring credentials.",
 "collect_driver_checkout":"Import bounded instrumented application-driver checkout wait/timeouts; do not use server connection counts.",
 "collect_database_activity":"Import approved aggregate query/lock activity without query text.",
}

def packages():
    result=[]
    for path in sorted(files("support_evidence").joinpath("packages").iterdir(),key=lambda p:p.name):
        if path.name.endswith(".json"):result.append(validate(json.loads(path.read_text())))
    return result

def diagnose(records,at,impact="unspecified operation",rule_packages=None,changes=None):
    if len(records)>5000:raise ValueError("incident work budget exceeded")
    for r in records:validate(r)
    pkgs=packages() if rule_packages is None else rule_packages
    for p in pkgs:validate(p)
    rules=[r for p in pkgs for r in p["rules"]]
    for r in rules:
        if set(r["next_checks"])-set(NEXT_CHECKS):raise ValueError("unregistered rule action")
    observations=sorted([r for r in records if r["kind"]=="observation"],key=lambda r:(r["event_at"],r["id"]))
    graph=project(records,at);unknowns=[];eligible=[]
    for o in observations:
        state=freshness(o,at)
        if state!="fresh" or o["collector_status"]!="OK" or o["predicate_status"]=="UNKNOWN":
            unknowns.append(o["id"]+":"+(state if state!="fresh" else "collection_or_predicate_unknown"))
        else:eligible.append(o)
    # Event-time precedence resists out-of-order delivery; simultaneous conflicts survive.
    latest={}
    for o in eligible:
        key=scope(o)+(o["dependence_group"],)
        latest[key]=max(latest.get(key,0),o["event_at"])
    current=[o for o in eligible if latest[scope(o)+(o["dependence_group"],)]-o["event_at"]<=1]
    findings=[];consumed=set()
    for rule in rules:
        for o in current:
            if o["operation"] not in rule["operations"] or o["predicate_status"]!="FAIL" or (rule["id"],scope(o)) in consumed:continue
            consumed.add((rule["id"],scope(o)))
            same=[x for x in current if scope(x)==scope(o) and abs(x["event_at"]-o["event_at"])<=2]
            support=[x for x in same if x["predicate_status"]=="FAIL"]
            contradictory=[x for x in same if x["predicate_status"]=="PASS"]
            compatible=[x for x in current if all(x.get(k)==o.get(k) for k in ["subject","instance_id","route","vantage"]) and abs(x["event_at"]-o["event_at"])<=2]
            missing=[pred for pred in rule["required_predicates"] if not any(x["predicate"]==pred and x["predicate_status"]=="FAIL" for x in compatible)]
            if rule["required_predicates"]:
                support=[x for x in compatible if x["predicate"] in rule["required_predicates"] and x["predicate_status"]=="FAIL"] or support
                contradictory += [x for x in compatible if x["predicate"] in rule["required_predicates"] and x["predicate_status"]=="PASS"]
            groups={x["dependence_group"] for x in support}
            direct=all(x["reliability"]=="direct" and x["retention"]=="retained" for x in support)
            assessment="inconclusive" if missing or contradictory else "strong" if direct else "moderate"
            f={"schema_version":1,"kind":"finding","id":"finding:"+digest([rule["id"],scope(o),sorted(x["id"] for x in support)])[:24],"finding_type":"observation" if not rule["required_predicates"] else "inference","boundary":rule["boundary"],"subject":o["subject"],"operation":o["operation"],"predicate":o["predicate"],"route":o["route"],"vantage":o["vantage"],"supporting":sorted({x["id"] for x in support}),"contradicting":sorted({x["id"] for x in contradictory}),"unknowns":rule["unknowns"]+["missing required predicate:"+m for m in missing],"rule_id":rule["id"],"rule_version":rule["version"],"assessment":assessment,"gates":{"required_evidence_complete":not missing,"independent_groups":len(groups),"independence_established":False,"reliable_direct_measurement":direct,"contradictions":len(contradictory),"signature_match":True,"topology_fit":"not_required_for_measured_boundary","temporal_compatibility":True,"probability":False},"next_checks":rule["next_checks"],"message":rule["message"]}
            findings.append(validate(f))
    covered={i for f in findings for i in f["supporting"]}
    for o in current:
        if o["predicate_status"]=="FAIL" and o["id"] not in covered:unknowns.append(o["id"]+":unsupported_failure_signature; abstain")
    health={}
    for o in observations:health[o["provenance"]["method"]]=health.get(o["provenance"]["method"],[])+[{"evidence_id":o["id"],"collector_status":o["collector_status"],"freshness":freshness(o,at)}]
    report={"schema_version":1,"kind":"incident","id":"incident:"+digest([at,impact,sorted(r["id"] for r in records)])[:24],"impact_contract":impact,"at":at,"interval":[min([o["event_at"] for o in observations]+[at]),at],"graph_revision":graph["revision"],"rule_versions":{p["id"]:p["version"] for p in pkgs},"findings":sorted(findings,key=lambda f:(f["subject"],f["operation"],f["vantage"],f["id"])),"passed":sorted(o["id"] for o in current if o["predicate_status"]=="PASS"),"unknowns":sorted(unknowns)+["Business correctness unknown without an authoritative oracle.","Failure location does not establish an initiating cause."] ,"changes":changes or [],"history_matches":[],"resolution":"unverified","engine_version":__version__,"collector_health":health,"permitted_actions":["registered read-only checks within manifest policy"],"requires_approval":["all remediation; no remediation executor is installed"],"coverage":{"observations":len(observations),"fresh_applicable":len(current),"history":"disabled","source_index":"disabled","llm":"disabled","unobserved":"unknown"},"topology":graph,"evidence_ids":sorted(r["id"] for r in records)}
    return validate(report)

def render(report,records):
    index={r["id"]:r for r in records};lines=["Impact contract: "+report["impact_contract"],"Incident: "+report["id"],"Time: "+str(report["at"]),"Graph: "+report["graph_revision"],"Evidence supports measured boundaries; initiating cause remains unverified."]
    if not report["findings"]:lines.append("No supported failing boundary; abstain or inspect scoped passing evidence.")
    for f in report["findings"]:
        lines += ["Boundary: "+f["boundary"]+" ["+f["assessment"]+"]", "  Scope: "+" / ".join(f[k] for k in ["subject","operation","route","vantage"]),"  "+f["message"],"  Rule: "+f["rule_id"]+"@"+f["rule_version"],"  Support: "+", ".join(f["supporting"]),"  Contradictions: "+(", ".join(f["contradicting"]) or "none measured"),"  Unknown: "+"; ".join(f["unknowns"])]
        for a in f["next_checks"]:lines.append("  Next ["+a+"]: "+NEXT_CHECKS[a])
    for i in report["passed"]:
        o=index[i];lines.append("PASS "+i+": "+" / ".join(o[k] for k in ["subject","operation","predicate","route","vantage"])+" at "+str(o["event_at"]))
    lines += ["Unknown: "+u for u in report["unknowns"]]
    lines += ["Change: "+c for c in report["changes"]]
    lines += ["History: disabled; no verified matches asserted.","Permitted: registered read-only diagnostics under manifest policy.","Approval required: all remediation; executor absent."]
    return "\n".join(lines)+"\n"

def optional_explanation(report, records, callback):
    """Closed citation selector seam. Free-form LLM claims cannot be validated, so reject them."""
    fallback=render(report,records)
    try:
        response=callback({"findings":report["findings"],"untrusted_data":True})
        if not isinstance(response,list) or len(response)>32:return fallback
        allowed={f["id"]:f for f in report["findings"]}
        for item in response:
            if set(item)!={"finding_id","evidence_ids"}:return fallback
            f=allowed[item["finding_id"]]
            if sorted(item["evidence_ids"])!=sorted(f["supporting"]):return fallback
        return fallback # deterministic wording is authoritative even for valid selections
    except Exception:return fallback
