# PostgreSQL, Nginx and retrieved guidance

PostgreSQL/Nginx collectors were introduced in 0.2.0 and remain available in current Phoebe 0.3.0 with the same explicit contracts. Docker/venv collectors are covered in the [companion guide](docker-venv-modules.md); shared retrieval/export behavior is covered in [knowledge and replay](knowledge.md). Documentation explains mechanisms and discriminating checks. Only scoped observations establish runtime status. No embedding service or generative-model account is required.

The collectors are selected explicitly in a manifest. A port or Server header does not identify the service. Use the hostname that represents the actual route: the pinned connection preserves that hostname for Host and TLS SNI. Every resolved address must be approved by the manifest. Choose a distinct predicate or route identity when changing a threshold or oracle, and supply an instance identity when known. Separately declare upstream targets; discovery never authorizes a new destination.

```sh
support-evidence check examples/manifest-service-modules.json --rag --export incident.json
support-evidence replay incident.json
support-evidence knowledge search postgres 'postgresql_query_canceled 57014'
support-evidence knowledge search nginx 'nginx_gateway_timeout 504'
support-evidence knowledge refresh --output official-source-audit.json
```

Set credential environment references before checking, and adjust example targets, thresholds, paths and oracle to the deployment. Database drivers remain an optional install: `pip install 'support-evidence[databases]'`. Store the JSON credential outside incident files; supported fields are username, password, database and optional ca_file. PostgreSQL TLS uses verify-full with the explicitly allowlisted CA path. Without ca_file the existing local-fixture mode disables TLS; use verified TLS for deployments that require it.

## PostgreSQL contracts

| Operation | Explicit contract | Evidence and limits |
| --- | --- | --- |
| postgresql_connect | Authenticated connection | Acceptance does not establish query, write or business correctness. |
| postgresql_read | Optional min_rows; optional lock_timeout_ms | Fixed SELECT count for public.support_probe id=1; only presence is retained. Default minimum is one. No manifest SQL is accepted. |
| postgresql_role | role primary or standby | Recovery-role match is separate from write availability and promotion readiness. |
| postgresql_activity | At least one of max_active_sessions, max_idle_transactions, max_transaction_seconds | Client-backend aggregates across the server, excluding the probe; full statistics visibility and activity tracking required. |
| postgresql_locks | max_blocked_sessions | Count of sessions with measured blockers; at most 512 candidates. No PIDs or query text retained. |
| postgresql_headroom | min_connection_headroom | Conservative ordinary admission estimate after reserved slots; includes the probe connection. Role limits, races and application driver pools remain unmeasured. |
| postgresql_replication | role and max_replay_bytes; primary also requires min_standbys ≥1 | Primary checks connected sender count and replay-position byte gap. Standby checks local receive-to-replay backlog. NULL positions remain UNKNOWN. |
| postgresql_vacuum | max_xid_age | Maximum database frozen-XID age. No vacuum, freeze, write or slot management is executed. |

Connection and fixed reads work with the declared application/fixture permissions. Activity, locks, headroom and primary replication conservatively require superuser statistics visibility or inherited pg_read_all_stats. Prefer a dedicated monitoring identity with only needed grants; Phoebe never grants privileges. Role and XID-age checks do not require broad statistics visibility. Missing grants, disabled or masked activity, unsupported diagnostic versions and absent capability fields produce collection UNKNOWN.

Aggregate collectors accept PostgreSQL 14–18 after capability checks; real integration was verified on PostgreSQL 18. Other diagnostic versions abstain. Compatibility with every 14–17 release, connection pooler, standby topology and extension combination has not been demonstrated. Each worker uses one short read-only transaction, fixed SQL, a safe search path, remaining statement budget and an outer process deadline. Statistics can still be delayed, and every aggregate is a point sample.

SQLSTATE is retained when the driver provides it. Specific distinctions include privilege, missing relation, lock acquisition, cancellation, deadlock, serialization, connection admission, storage, memory and lifecycle errors. A monitoring query denied permission is DENIED/UNKNOWN; denied SELECT on the declared fixture is a failed fixture contract. Some libpq connection failures omit SQLSTATE, including authentication failures; these stay unresolved connection/startup failures without parsing localized error text. 57014 does not uniquely identify a timeout or blocker.

The catalogue also covers WAL retention, replication slots, authentication policy and maintenance interpretation. TLS verification is also covered by a libpq source card; use the database connection collector for that contract. Those entries are guidance; this release does not install slot, log, arbitrary query or remediation collectors.

## Nginx contracts

| Operation | Contract | Evidence and limits |
| --- | --- | --- |
| nginx_http | Expected status, optional SHA-256 or simple JSON oracle | Bounded GET on declared host/path/scheme; no redirects, response bodies or automatic upstream selection. |
| nginx_stub_status | max_active_connections | Strict bounded text parser for the optional stub_status endpoint. Counts include the status request itself. |

A missing, inaccessible, malformed or unreachable monitoring endpoint leaves collection UNKNOWN. A valid status sample that exceeds its explicit active-client threshold fails that specific contract. Active clients include idle Waiting connections; they do not measure complete worker occupancy. Cumulative accepted/handled gaps are retained as metadata, with no current-drop diagnosis. This release has no interval-loss estimator, so counter resets cannot fabricate a loss finding.

The optional status module must be present and its endpoint explicitly configured and approved. Open-source Nginx 1.28-alpine was exercised; rolling official documentation may describe other builds and commercial features. The catalogue records applicability rather than assuming all features exist.

502/504 establish a failed declared route, with refusal, DNS, TLS, routing, timeout and upstream-generated responses preserved as alternatives. A successful direct upstream check narrows investigation only for the measured route, namespace, instance and interval. proxy_read_timeout covers gaps between reads, while the Phoebe deadline covers the complete worker operation. Reading configuration records intent; rejected reloads can leave the old configuration serving requests. No production nginx -t, reload, arbitrary command, upload or load generator is executed.

Guidance also covers virtual hosts, oracles, workers/file descriptors, buffering/temp storage, upstream groups/retries, DNS, TLS, rate limits and request-size boundaries. One GET and basic client counters cannot measure all those failures. Follow registered checks or approved aggregate imports and keep unmeasured branches unknown.

## Retrieval and replay

The PostgreSQL/Nginx families retain 26 original cards (13 each). The current four-family corpus contains 45 cards referencing 34 official sources, including Docker, Python and PyPA documentation. Every card has a stable documentation ID, revision, applicability, verification date, source URL, limitations and canonical content hash. Current bm25-2 lexical ranking with exact signature boosts retrieves at most three cards per explanation. Scores measure relevance, never confidence. Unrelated queries abstain. Generation joins separately labelled evidence references with retrieved summaries, alternatives, limitations and proposed checks using deterministic templates.

`--rag` adds a separate knowledge context. JSON output becomes an explicit object with report and knowledge; without the flag the incident JSON remains the existing shape. Denied, stale, unmatched and unavailable service observations can receive guidance without becoming failure findings. Existing findings and assessments remain untouched.

RAG exports use bundle schema 2 and embed the complete small corpus, context, retrieval/generation versions and hashes. Replay regenerates both the core report and the grounded context from embedded data without consulting installed documentation or the network. Core-only bundles remain schema 1. Phoebe supports recorded engine versions 0.1.0, 0.2.0 and 0.3.0. Current diagnosis retains the 0.2.0 fixes that prevent a newer UNKNOWN from exposing older PASS and isolate reason-specific support. Earlier enriched bundles regenerate with bm25-1; current guidance uses bm25-2/template-1.

`knowledge refresh` fetches only the bundled inventory of official HTTPS pages. Public DNS is checked, connections are pinned, redirects rejected, and each request has a supervised process deadline plus a one-MiB response limit. It saves source hashes and review-required receipts; raw HTML is not retained. An unavailable or partial source audit returns exit 3 and explicit receipts. It does not automatically rewrite reviewed summaries or mark new prose authoritative. Compare receipts and revise the original cards with reviewed source facts when documentation changes. Ordinary checks, retrieval and replay stay offline except for explicitly declared service probes.

## Verification and remaining coverage

[Service integration results](service-module-results.json) record 22 actual service scenarios and owned-resource cleanup. They cover healthy controls, authentication rejection, restricted statistics, role mismatch, absent declared replica, headroom/XID threshold edges, blocked fixture query, lock deadline, measured blocking/idle transaction, revoked SELECT, missing fixture, Nginx route/status control, wrong Host, wrong oracle, denied/malformed status, client threshold edge, 504 with responsive direct upstream, 502 with healthy direct upstream, and invalid reload rejection with continued old routing.

Headroom, XID and active-client edge cases apply deliberately strict contracts to real counters; they are not injected exhaustion, wraparound or saturation. SQLSTATE variants, NULL replication metrics, unsupported versions and additional masking use unit doubles. A replicated standby, actual resource exhaustion, WAL archive/slot failures and production deployment comparison remain untested. The broader failure catalogue is not a claim of complete detection.

[Historical 0.2.0 validation](service-validation-results.json): 157 automated tests, 22 service-module scenarios, the existing 20-case regression harness, all 20 official source fetches, and offline wheel installation/retrieval/replay/removal passed. Genuine 0.1.0 bundles continue to replay exactly.

[Current 0.3.0 validation](docker-venv-validation-results.json) records 217 automated tests, 25 actual Docker/venv cases, 34/34 source fetches and offline installation/probe/search/replay/removal. The 22 PostgreSQL/Nginx cases above are a separate recorded run; neither corpus expansion nor those other fixtures establish production or replicated-standby coverage.
