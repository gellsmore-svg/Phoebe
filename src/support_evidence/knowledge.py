"""Offline retrieval and deterministic grounded generation, outside runtime evidence.

Retrieval scores are lexical relevance, never confidence or incident probability.
No remote model, vector service, query payload or executable document is involved.
"""
import copy
import hashlib
import http.client
import ipaddress
import json
import math
import os
import sys
import re
import socket
import ssl
import time
from collections import Counter
from importlib.resources import files
from urllib.parse import urlsplit
from .model import canonical, digest, freshness, validate

RETRIEVAL_VERSION = "bm25-2"
GENERATION_VERSION = "template-1"
CARD_KEYS = {"schema_version", "kind", "id", "service", "revision", "title", "summary", "tags", "checks", "limitations", "applicability", "source", "integrity"}
STOP = {"postgresql", "postgres", "nginx", "the", "and", "a", "an", "of", "to", "for", "in", "is", "with", "from"}

def validate_card(card):
    if not isinstance(card, dict) or set(card) != CARD_KEYS:
        raise ValueError("knowledge card contract")
    if card["schema_version"] != 1 or card["kind"] != "knowledge_card" or card["service"] not in {"postgresql", "nginx", "docker", "venv"}:
        raise ValueError("knowledge card version/service")
    if not isinstance(card["id"], str) or not re.fullmatch(r"doc:[a-z0-9-]{1,64}", card["id"]):
        raise ValueError("knowledge card identifier")
    for key in ["revision", "title", "summary", "limitations", "applicability"]:
        if not isinstance(card[key], str) or not 1 <= len(card[key]) <= 1200 or any(ord(c) < 32 for c in card[key]):
            raise ValueError("knowledge text budget")
    for key in ["tags", "checks"]:
        if not isinstance(card[key], list) or not 1 <= len(card[key]) <= 32 or any(not isinstance(t,str) or not 1 <= len(t) <= 512 or any(ord(c) < 32 for c in t) for t in card[key]):
            raise ValueError("knowledge list contract")
    source = card["source"]
    if not isinstance(source,dict) or set(source) != {"url", "documentation_version", "verified_at", "licence"}:
        raise ValueError("knowledge provenance contract")
    if any(not isinstance(v,str) or not 1 <= len(v) <= 512 or any(ord(c) < 32 for c in v) for v in source.values()):
        raise ValueError("knowledge source text")
    url = urlsplit(source["url"])
    if url.scheme != "https" or url.username or url.password or url.query or url.fragment or url.port not in {None,443}:
        raise ValueError("knowledge source URL")
    if not ((card["service"] == "postgresql" and url.hostname == "www.postgresql.org" and re.fullmatch(r"/docs/18/[a-z0-9-]+\.html", url.path)) or (card["service"] == "nginx" and url.hostname == "nginx.org" and re.fullmatch(r"/en/docs/(http/)?[a-z0-9_]+\.html", url.path)) or (card["service"] == "docker" and url.hostname == "docs.docker.com" and url.path in {"/reference/api/engine/version/v1.47/", "/reference/api/engine/", "/engine/security/rootless/", "/engine/containers/resource_constraints/", "/reference/dockerfile/", "/reference/dockerfile.md", "/engine/network/", "/engine/storage/", "/engine/containers/start-containers-automatically/"}) or (card["service"] == "venv" and ((url.hostname == "docs.python.org" and url.path in {"/3.14/library/venv.html", "/3.14/library/site.html", "/3.14/library/sys.html"}) or (url.hostname == "packaging.python.org" and url.path in {"/en/latest/specifications/core-metadata/", "/en/latest/specifications/dependency-specifiers/", "/en/latest/specifications/recording-installed-packages/"})))):
        raise ValueError("knowledge authoritative source denied")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",source["verified_at"]):
        raise ValueError("knowledge verification date")
    payload = {k:v for k,v in card.items() if k != "integrity"}
    if digest(payload) != card["integrity"]:
        raise ValueError("knowledge card integrity")
    if len(canonical(card).encode()) > 16384:
        raise ValueError("knowledge card size")
    return card

def corpus():
    return validate_corpus([json.loads(p.read_text()) for p in sorted(files("support_evidence").joinpath("knowledge").iterdir(), key=lambda p:p.name) if p.name.endswith(".json")])

def validate_corpus(cards):
    if not isinstance(cards,list) or not 1 <= len(cards) <= 128:
        raise ValueError("knowledge corpus budget")
    for card in cards:validate_card(card)
    if len({c["id"] for c in cards}) != len(cards):
        raise ValueError("duplicate documentation IDs")
    return sorted(cards,key=lambda c:c["id"])

def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+",text.lower()) if t not in STOP]

def retrieve(service, query, cards=None, limit=3, version=RETRIEVAL_VERSION):
    if version not in {"bm25-1", "bm25-2"}: raise ValueError("unsupported retrieval version")
    service = "postgresql" if service == "postgres" else service
    if service not in {"postgresql","nginx","docker","venv"} or not isinstance(query,str) or len(query) > 2048 or not 1 <= limit <= 5:
        raise ValueError("retrieval request budget")
    cards = corpus() if cards is None else validate_corpus(cards)
    documents = [c for c in cards if c["service"] == service]
    terms = set(tokens(query))
    if not terms or not documents:return []
    bags = [Counter(tokens(" ".join([c["title"],c["summary"],c["limitations"],*c["tags"],*c["checks"]]))) for c in documents]
    average = sum(sum(b.values()) for b in bags) / len(bags)
    hits=[]
    for card,bag in zip(documents,bags):
        score=0.0
        for term in terms & bag.keys():
            frequency=sum(term in b for b in bags)
            idf=math.log(1+(len(bags)-frequency+.5)/(frequency+.5))
            count=bag[term]
            score += idf*count*2.2/(count+1.2*(.25+.75*sum(bag.values())/average))
        # Exact structured signatures outrank incidental prose matches.
        score += sum(12 for tag in card["tags"] if tag in query.split() and tag.startswith(("postgresql_","nginx_") if version=="bm25-1" else ("postgresql_","nginx_","docker_","venv_")))
        if score > 0:hits.append({"card":copy.deepcopy(card),"score":round(score,6)})
    return sorted(hits,key=lambda h:(-h["score"],h["card"]["id"]))[:limit]

def service_of(observation, version=RETRIEVAL_VERSION):
    operation=observation["operation"]
    services=("postgresql","nginx") if version=="bm25-1" else ("postgresql","nginx","docker","venv")
    return next((service for service in services if operation.startswith(service+"_")),None)

def augment(report, records, cards=None, retrieval_version=RETRIEVAL_VERSION):
    """Generate an auxiliary explanation; never alter findings, status or support."""
    if retrieval_version not in {"bm25-1","bm25-2"}: raise ValueError("unsupported retrieval version")
    validate(report)
    for record in records:validate(record)
    cards=corpus() if cards is None else validate_corpus(cards)
    index={r["id"]:r for r in records if r["kind"]=="observation"}
    seeds=[];covered=set()
    for finding in report["findings"]:
        observations=[index[i] for i in finding["supporting"]]
        if observations and service_of(observations[0],retrieval_version):
            seeds.append((finding["id"],observations));covered.update(o["id"] for o in observations)
    # Unknown and unmatched service failures need guidance too, including stale coverage.
    seeds.extend((None,[o]) for o in sorted(index.values(),key=lambda o:o["id"]) if service_of(o,retrieval_version) and o["id"] not in covered and (o["predicate_status"] != "PASS" or freshness(o,report["at"]) != "fresh"))
    entries=[]
    for finding_id,observations in seeds[:128]:
        service=service_of(observations[0],retrieval_version)
        query=" ".join(str(v) for o in observations for v in [o["operation"],o["predicate"],o["value"].get("reason",""),o["value"].get("error_code",""),o["value"].get("status_code","")])[:2048]
        hits=retrieve(service,query,cards,version=retrieval_version)
        entries.append({"finding_id":finding_id,"evidence_ids":sorted(o["id"] for o in observations),"service":service,
            "observations":[{"id":o["id"],"collector_status":o["collector_status"],"predicate_status":o["predicate_status"],"freshness":freshness(o,report["at"])} for o in sorted(observations,key=lambda o:o["id"])],
            "status":"grounded_guidance" if hits else "no_matching_documentation",
            "explanation":"Runtime status is established only by the cited observations. Retrieved documentation supplies competing mechanisms and discriminating checks; it does not establish an initiating cause.",
            "documents":[{"id":h["card"]["id"],"integrity":h["card"]["integrity"],"score":h["score"],"title":h["card"]["title"],"summary":h["card"]["summary"],"checks":h["card"]["checks"],"limitations":h["card"]["limitations"],"applicability":h["card"]["applicability"],"source":h["card"]["source"]} for h in hits]})
    return {"schema_version":1,"kind":"knowledge_context","incident_id":report["id"],"corpus_integrity":digest(cards),"retrieval_version":retrieval_version,"generation_version":GENERATION_VERSION,"mode":"offline lexical retrieval and deterministic grounded generation","runtime_evidence":False,"truncated":len(seeds)>128,"entries":entries}

def attachment(report, records, cards=None):
    cards=corpus() if cards is None else validate_corpus(cards)
    return {"cards":cards,"context":augment(report,records,cards)}

def verify_attachment(value, report, records):
    if not isinstance(value,dict) or set(value)!={"cards","context"}:
        raise ValueError("knowledge attachment contract")
    if not isinstance(value["context"],dict): raise ValueError("knowledge context contract")
    expected=augment(report,records,value["cards"],retrieval_version=value["context"].get("retrieval_version"))
    if expected != value["context"]:
        raise ValueError("knowledge generation or citation mismatch")
    return value

def render_context(context):
    lines=["Retrieved guidance (documentation is not runtime evidence):", "  Retrieval: "+context["retrieval_version"]+"; generation: "+context["generation_version"]]
    for entry in context["entries"]:
        lines.append("  Context for "+(entry["finding_id"] or ", ".join(entry["evidence_ids"]))+": "+entry["status"])
        for observation in entry["observations"]:
            lines.append("    Observed "+observation["id"]+": "+"/".join(observation[k] for k in ["collector_status","predicate_status","freshness"]))
        for doc in entry["documents"]:
            lines.extend(["    ["+doc["id"]+"] "+doc["title"]+": "+doc["summary"],"      Check: "+"; ".join(doc["checks"]),"      Limit: "+doc["limitations"],"      Source: "+doc["source"]["url"]+" (verified "+doc["source"]["verified_at"]+"; "+doc["applicability"]+")"])
    if context["truncated"]:lines.append("  Guidance budget reached; remaining entries omitted.")
    if not context["entries"]:lines.append("  No failing, unknown or stale supported-service observation requires guidance.")
    return "\n".join(lines)+"\n"

def fetch_source(url, timeout):
    """Fixed official URLs, public DNS, pinned TLS, no redirects and bounded bodies."""
    parsed=urlsplit(url)
    addresses=sorted({a[4][0] for a in socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)},key=lambda address:(ipaddress.ip_address(address).version,address))
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise ValueError("documentation DNS policy")
    deadline=time.monotonic()+timeout
    raw=socket.create_connection((addresses[0],443),timeout=max(.01,deadline-time.monotonic()))
    try:
        raw.settimeout(max(.01,deadline-time.monotonic()))
        tls=ssl.create_default_context().wrap_socket(raw,server_hostname=parsed.hostname)
        connection=http.client.HTTPConnection(parsed.hostname,443,timeout=timeout);connection.sock=tls
        try:
            connection.request("GET",parsed.path,headers={"Host":parsed.hostname,"User-Agent":"Phoebe-source-audit/0.2","Connection":"close"})
            tls.settimeout(max(.01,deadline-time.monotonic()))
            response=connection.getresponse()
            if response.status != 200:raise ValueError("documentation HTTP status")
            body=bytearray()
            while True:
                chunk=response.read(min(65536,1048577-len(body)))
                if not chunk:break
                body.extend(chunk)
                if len(body)>1048576:raise ValueError("documentation size budget")
                if time.monotonic()>=deadline:raise TimeoutError()
            return hashlib.sha256(body).hexdigest()
        finally:connection.close()
    finally:raw.close()

def refresh_sources():
    """Audit fresh official sources; summaries require review before a new revision.

No fetched HTML is executed, retained or silently promoted into reviewed guidance.
"""
    from .supervisor import supervise, WorkerError
    inventory=sorted({c["source"]["url"] for c in corpus()})
    env={k:v for k,v in os.environ.items() if k in {"PATH","LANG","LC_ALL","PYTHONPATH","HOME","SSL_CERT_FILE","SSL_CERT_DIR"}}
    deadline=time.monotonic()+60;receipts=[]
    for url in inventory:
        remaining=deadline-time.monotonic()
        if remaining<=0:
            receipts.append({"url":url,"status":"budget_exhausted","review_required":True});continue
        try:
            result=supervise([sys.executable,"-m","support_evidence.knowledge_worker"],{"url":url,"timeout":min(5,remaining)},min(5,remaining),env,output_limit=4096)
            sha=result["source_sha256"]
            if not isinstance(sha,str) or not re.fullmatch(r"[0-9a-f]{64}",sha):raise ValueError("source receipt")
            receipts.append({"url":url,"status":"fetched","source_sha256":sha,"review_required":True})
        except (OSError,ValueError,KeyError,WorkerError,http.client.HTTPException):
            receipts.append({"url":url,"status":"unavailable","review_required":True})
    return {"schema_version":1,"kind":"source_refresh_audit","retrieved_at":time.time(),"corpus_integrity":digest(corpus()),"summaries_changed":False,"sources":receipts}
