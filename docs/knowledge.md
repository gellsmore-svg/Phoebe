# Knowledge, source audits and offline replay

Phoebe 0.3.0 offers optional retrieval-augmented guidance alongside deterministic runtime diagnosis. It uses a bundled lexical index and template generation, with no embedding service, remote model or generative account. Documentation is auxiliary context; scoped observations alone support findings and health.

## Reviewed corpus

| Family | Original cards | Scope |
|---|---|---|
| PostgreSQL | 13 | Connection/permissions, SQLSTATE, activity, locks, headroom, replication, WAL, vacuum/XID age and TLS |
| Nginx | 13 | Route/oracle, gateway alternatives, status/capacity, DNS/TLS, limits, buffering, retries and lifecycle |
| Docker | 10 | Socket/API/namespace, exact identity/lifecycle, health, restarts, memory/PIDs, network and storage dependencies |
| Python venv | 9 | Structure/base, moved scripts, isolation/hooks, recursive dependencies/extras/markers, metadata and runtime limits |

The 45 cards reference 34 fixed official PostgreSQL, Nginx, Docker, Python and PyPA URLs. Each card includes an ID, revision, applicability, verification date, licence/source, original summary, discriminating checks, limitations and content hash. Broad failure guidance does not imply a collector exists for every mechanism.

```bash
support-evidence knowledge search postgres 'postgresql_query_canceled 57014' --json
support-evidence knowledge search nginx 'nginx_gateway_timeout 504' --json
support-evidence knowledge search docker docker_unhealthy --json
support-evidence knowledge search venv venv_dependencies_missing --json
```

`postgres` aliases `postgresql`. Current retrieval is `bm25-2`; it filters by family and boosts exact operation/reason tags. Search returns up to three cards by default, with lexical relevance scores rather than incident probabilities or confidence. An unrelated query can return no matches. Generation is `template-1`, retaining evidence references, competing mechanisms, limits and checks. Failed, unknown and stale service observations can receive guidance without becoming supported findings.

## Output and export

`--rag` is supported by `check`, `report`, `diagnose` and `export`. Without it, core report JSON is the incident object. With it, report/check/diagnose JSON has `report` and `knowledge` keys; knowledge is a separate context, never evidence. `replay --json` uses that wrapper when the retained bundle already contains guidance and needs no additional flag.

```bash
support-evidence --store ./evidence.sqlite check ./my-manifest.json --rag --export ./incident.json
support-evidence --store ./evidence.sqlite report --rag --json
support-evidence --store ./evidence.sqlite export ./escalation.json --rag
support-evidence replay ./incident.json --json
```

For historical analysis, add `--at TIMESTAMP` using the Unix event time appropriate to the retained records. Exports refuse an existing output file. Core-only bundles use schema 1; enriched bundles use schema 2 and carry the full reviewed corpus, generated context and hashes alongside evidence and embedded rules. Record/store schema version remains 1. The core coverage fields source_index and llm remain disabled because auxiliary guidance does not alter the evidence engine.

Replay verifies bundle integrity, regenerates the report from retained records and rules with its recorded engine version, then regenerates enriched context from embedded cards and its recorded retrieval version. Engines 0.1.0/0.2.0/0.3.0 and legacy bm25-1 contexts are supported. Replay does not query a live service, installed corpus, store, network or model. Successful replay returns exit 0 even when the retained incident describes a supported failure. Hashes establish content/reproduction consistency; bundles are not signed identity attestations.

## Audit sources

```bash
support-evidence knowledge refresh --output ./official-source-audit.json
```

Refresh audits the fixed URLs already present in bundled cards. It checks public DNS, pins TLS connections, verifies certificates, rejects redirects and limits each response to 1 MiB. A supervised request has at most five seconds; the overall audit budget is 60 seconds. A request can therefore be unavailable or budget_exhausted. The official Dockerfile Markdown URL avoids its larger HTML representation while retaining the response cap.

Receipts retain timestamps, source hashes and review_required; raw documents are discarded. Exit 0 means all sources fetched, while a partial/unavailable audit returns 3 with receipts. Fetch success does not update prose, applicability or verification dates automatically. Maintainers review source facts, revise cards and hashes, and validate replay before publishing updates. The recorded 0.3.0 audit fetched 34/34 sources; later availability is a separate observation.

Ordinary search and enriched replay remain offline. Service checks can contact only their explicitly declared targets. See [module guides](service-modules.md), [Docker/venv](docker-venv-modules.md), [schema](schema-reference.md) and [plugin guide](plugin-guide.md).
