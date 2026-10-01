"""Reuse existing monitoring exports. Explicit contracts supply meaning."""
from .model import observation, digest


def from_monitoring_plugin(probe,exit_code,source="monitoring_plugin",at=None):
    r=observation(probe,status={0:"PASS",1:"FAIL",2:"FAIL",3:"UNKNOWN"}.get(exit_code,"UNKNOWN"),collector="OK" if exit_code in {0,1,2,3} else "ERROR",value={"exit_code":exit_code},method=source,now=at)
    r["reliability"]="imported";r["dependence_group"]="upstream:"+source;r.pop("integrity",None);r["integrity"]=digest(r)
    return r

def from_prometheus(probe,response,threshold,direction="above",source="prometheus"):
    r=observation(probe,collector="UNAVAILABLE",value={"reason":"missing_or_ambiguous_sample"},method="prometheus_import")
    result=response.get("data",{}).get("result",[])
    if response.get("status")=="success" and response.get("data",{}).get("resultType")=="vector" and len(result)==1:
        ts,value=result[0]["value"]
        try:
            number=float(value)
            if not __import__("math").isfinite(number):raise ValueError()
            fail=number>threshold if direction=="above" else number<threshold
            r=observation(probe,"FAIL" if fail else "PASS",value={"sample":number,"threshold":threshold},method="prometheus_import",now=float(ts))
            r["received_at"]=__import__("time").time()
        except (ValueError,TypeError):pass
    r["reliability"]="imported";r["dependence_group"]="upstream:"+source;r.pop("integrity",None);r["integrity"]=digest(r)
    return r

def from_otlp_metric(probe,response,metric,threshold,source="otel"):
    """OTLP JSON gauge/sum snapshot; no OTLP listener, re-export or resource guessing."""
    points=[]
    for resource in response.get("resourceMetrics",[]):
        for scope in resource.get("scopeMetrics",[]):
            for item in scope.get("metrics",[]):
                if item.get("name")==metric:
                    points.extend(item.get("gauge",item.get("sum",{})).get("dataPoints",[]))
    if len(points)!=1:return observation(probe,collector="UNAVAILABLE",value={"reason":"missing_or_ambiguous_sample"},method="otlp_json_import")
    point=points[0]
    value=point.get("asDouble",point.get("asInt"))
    snapshot={"status":"success","data":{"resultType":"vector","result":[{"value":[int(point["timeUnixNano"])/1e9,value]}]}}
    r=from_prometheus(probe,snapshot,threshold,source=source);r["provenance"]["method"]="otlp_json_import";r.pop("integrity",None);r["integrity"]=digest(r)
    return r
