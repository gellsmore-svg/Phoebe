# Schema reference

Contract version 1, JSON Schema draft 2020-12: [records-v1.json](../schemas/records-v1.json). Runtime ships the identical schema. Strict kind-specific fields reject unknown record structure; identifiers are immutable, scoped strings. Canonical JSON excludes NaN/Infinity and produces stable SHA-256 hashes.

| Kind | Meaning and mandatory scope |
|---|---|
| entity | scope, logical identity, separate instance, entity kind, bounded safe attributes and provenance; discoveries use immutable revision IDs |
| assertion | source/target, type, INTENDED/DISCOVERED/OBSERVED, validity, receipt, source/version/evidence, criticality, AND/OR/QUORUM/UNKNOWN, synchrony, labelled causal mechanism if any |
| probe | subject/instance, operation, predicate, exact target/route, actual vantage/current namespace, optional credential reference, timeout/interval/freshness, bounded cost and read-only class |
| observation | subject/instance/operation/predicate/route/vantage, event/receipt/freshness, collection and target states, coverage/sampling, dependence group, reliability, safe values, lineage and retention |
| finding | measured boundary, support/contradiction IDs, unknowns, package rule/version, ordinal gates and registered next checks |
| incident | impacted contract, interval/time, graph revision, embedded findings and evidence IDs, source health, versions, changes, unresolved/operator status and permitted action policy |
| failure_package | applicability, versioned declarative rules, required predicates, sources/licence, next checks and positive/negative/unknown fixtures |
| action | read classification, targets/permissions/preconditions/deadline, side effects, approval policy and verification; no executable command |

Semantic validation additionally forbids a collection failure with PASS/FAIL, inverted assertion intervals and unlabelled FAILURE_PROPAGATES_TO. Missing evidence never creates an observation. Values and attributes are allowlisted before persistence; raw log text, bodies, query values and environment dumps are omitted. Secret-bearing metadata is rejected.

The store migration is schema 0 -> 1 and transactional ingestion deduplicates exact ID/hash records; altered content under the same ID fails. A newer store version fails closed. There is no claimed migration from an earlier released product. Future record versions need explicit migrations and replay fixtures.

Scalar records are capped at 64 KiB. Aggregate incidents and bundles are capped at 8 MiB; diagnosis max 5,000 records. Unknown technology versions, OR/quorum semantics and sampling stay explicit. Stored semantics do not imply an implemented simulator, probabilistic model or automatic failure propagation.

## Version layers and enriched bundles

| Layer | Current/supported version | Meaning |
|---|---|---|
| Records | 1 | Strict entity/assertion/probe/observation/finding/incident/package/action contracts |
| SQLite store | 1 | Local transactional record schema; newer versions fail closed |
| Incident bundle | 1 core-only; 2 enriched | Embedded records, report, rule packages and hash; schema 2 also embeds reviewed cards/context |
| Diagnosis engine | 0.3.0; replay supports 0.1.0 and 0.2.0 | Recorded version selects report semantics |
| Retrieval/generation | bm25-2/template-1; legacy bm25-1 replay | Selects deterministic context regeneration from embedded cards |

Documentation cards/context are auxiliary structures validated in knowledge.py; they are not runtime record kinds in records-v1.json. Enriched bundle knowledge has cards and context; enriched CLI JSON has report and knowledge, where knowledge is the context only. Core-only CLI JSON remains the incident object. See [knowledge and replay](knowledge.md).

Probe expected fields are operation-specific, including database roles/thresholds, HTTP oracles, Docker lifecycle/headroom, and venv version/isolation/requirements. [Module contracts](service-modules.md) and [local module contracts](docker-venv-modules.md) define prerequisites. Docker/venv route must equal target so separate sockets/environment roots remain separate evidence scopes; container instance_id is a full immutable hexadecimal ID. Credentials remain references, never values.

New safe aggregate metadata includes PostgreSQL statistics, Nginx counters, Docker state/resource values and venv dependency/script counts. The model's closed allowlist discards sensitive/unrecognized payload fields before persistence. Core coverage retains source_index/llm disabled even when auxiliary guidance is attached. Bundle hashes and exact regeneration verify retained consistency; they are not digital signatures. Modifying reviewed cards cannot change already exported incidents because those incidents retain their own corpus and retrieval version.
