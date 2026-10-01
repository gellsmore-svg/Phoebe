# Build an evidence-based support layer for opaque software

## Mission

Act as a senior systems engineer, SRE, architecture researcher and coding agent. Verify the research baseline below, create a new local Git repository, and implement the smallest useful supportability layer for software whose source may never have been fully read by a human.

Core requirement:

> An unfamiliar support engineer must be able to identify an evidence-supported failing boundary and the next safe diagnostic check without first reconstructing the whole application.

Do not promise automatic understanding of arbitrary business logic, exact root cause for every incident, or safety of unreviewed code. This project improves operational diagnosis. Source size is not a proxy for operational correctness.

The research baseline was established on 1 October 2026. Treat it as a challengeable starting point, not a fixed design. Prefer integration with existing tools when it satisfies the acceptance criteria. Build working software, tests and maintainer documentation; do not stop at a design document.

## 1. Verify existing art before coding

Use current primary documentation and author repositories. Record URLs, retrieval dates, versions, licences, edition limits and uncertainty in `docs/research.md`. Distinguish documented features, vendor claims, reproduced behaviour and your own inference.

Specifically compare:

- Coroot: https://docs.coroot.com/installation/architecture/ and https://docs.coroot.com/ai/overview/
- OTel: https://opentelemetry.io/docs/concepts/components/ and https://opentelemetry.io/docs/concepts/semantic-conventions/
- OTel entity model: https://opentelemetry.io/docs/specs/otel/entities/data-model/
- Checkmk: https://docs.checkmk.com/latest/en/devel_check_plugins.html
- Blackbox Exporter: https://github.com/prometheus/blackbox_exporter
- Backstage: https://backstage.io/docs/features/software-catalog/system-model/
- TOSCA: https://docs.oasis-open.org/tosca/TOSCA/v2.0/TOSCA-v2.0.html
- Provenance: https://www.w3.org/TR/prov-o/
- RCACopilot: https://www.microsoft.com/en-us/research/publication/automatic-root-cause-analysis-via-large-language-models-for-cloud-incidents/
- MicroRCA: https://github.com/elastisys/MicroRCA
- RCAEval: https://github.com/phamquiluan/RCAEval
- AIOpsLab: https://github.com/microsoft/AIOpsLab
- RCA survey: https://arxiv.org/abs/2408.00803

Coroot already documents topology-based analysis followed by LLM explanation. Commercial products also provide topology-aware and agentic investigations: Datadog Bits Investigation/Remediation, Dynatrace Intelligence, New Relic Autopilot, Splunk ITSI, Elastic, IBM Instana, BigPanda and PagerDuty. Verify current names and availability. Do not claim a novel invention of topology-aware diagnosis or “AI explains telemetry”.

Where relevant compare Grafana/Alloy/Loki/Tempo/Jaeger/Honeycomb; eBPF tools Coroot/Beyla/Pixie/Cilium-Hubble/Elastic Universal Profiling; Sourcegraph/SCIP/AppMap/CAST/Joern; OpsLevel/Cortex/Port; and mature monitoring Zabbix/Nagios/Icinga/Netdata/Sensu/Monit.

Research only unresolved implementation questions deeply; avoid an indefinite survey. Produce a build-versus-integrate decision: an adapter and report layer over existing monitoring is an acceptable implementation if it meets requirements. Do not construct a second observability company.

## 2. Repository and scope

Choose a neutral repository name after architecture verification. Do not assume a previously used project name is available. Create and initialise the local repository, make coherent commits, and record the toolchain and supported platforms. Remote creation/publishing requires an identified account and authorisation; do not invent either. Never modify unrelated application repositories or production services.

Select implementation language and embedded storage through short ADRs. Prioritise packaging, bounded concurrency, predictable deployment and maintainability. Python or Go may be sensible; neither is mandated. A graph database, Redis, Kubernetes, broker or LLM subscription must not be required for local diagnosis.

First deployment: one Linux host with systemd, Nginx, a Python HTTP service using FastAPI/Uvicorn/Gunicorn-style deployment, MongoDB, DNS/TCP/TLS and filesystem boundaries. Implement PostgreSQL as the second database adapter before declaring the model portable across databases. Keep core schemas independent of Linux, Python and database brand.

## 3. Architecture baseline

Use a temporal operational evidence model with a typed graph projection. “Support Model” is a provisional name. A graph is not inherently causal; a graph projection is not a validated behavioural digital twin.

Logical pipeline:

1. Safe deployment/configuration extraction and runtime discovery.
2. Existing telemetry adapters plus bounded active probes.
3. Assertion reconciliation, identity resolution and coverage tracking.
4. Temporal evidence persistence and graph projection.
5. Deterministic classification and bounded diagnostic planning.
6. CLI/JSON report, with optional LLM explanation.

Maintain three separate views:

- INTENDED: deployment/configuration claims about expected structure.
- DISCOVERED: actual present processes, units, sockets and instances.
- OBSERVED: communications and operations exercised in a time window.

Keep conflicting assertions and their provenance. Do not overwrite one view with another. Report undeclared dependencies, missing expected instances, version mismatch and ambiguous identity. An unobserved relationship is not proven absent unless workload and collection coverage support that conclusion.

Do not continuously index the entire source repository. Read-only source drill-down is optional and demand-driven after narrowing the incident. Match any source evidence to the deployed build.

## 4. Telemetry decisions

Use OTel semantic conventions and OTLP as the preferred interoperability substrate. Preserve schema versions and maturity status. OTel entity relationship work is evolving; do not assume every backend implements it.

Accept Prometheus and existing monitoring inputs. Reuse compatible hostmetrics/Nginx/Mongo/PostgreSQL receivers, exporters and Monitoring Plugins. Do not duplicate their collection, storage or transport without documenting a specific gap. A direct local probe must still work without a Collector.

Separate bulk telemetry storage from the bounded evidence store. Retain evidence references, safe excerpts, integrity hashes, source identity and retention status. A replayable incident must not depend entirely on a dashboard link that later expires.

eBPF is an optional Linux enhancement, never an installation prerequisite. Prefer adapters to existing instrumentation. Verify kernel, protocol, encryption, namespace, capability and overhead limits. No automatic payload capture or CAP_SYS_ADMIN default. Missing access reduces coverage.

Metrics, logs, traces, profiling, deployment events and probe results are different evidence sources. Trace sampling and missing instrumentation must be represented. Baggage must not contain credentials or act as a general configuration database.

## 5. Machine-readable contracts

Implement versioned schemas, validation, migrations and fixtures. Prefer a small set of records with typed kinds over a class per technology.

**Entity:** schema version, scope, stable logical identity, ephemeral instance identity if applicable, kind, technology/version, safe attributes and provenance. Kinds cover application/component/service/process/endpoint/host/network boundary/storage. Separate services from individual processes. Process identity must handle PID reuse and host scope.

**Relationship assertion:** source/target IDs, relation type, intended/discovered/observed view, validity interval, receipt time, provenance, evidence IDs, route/operation context, criticality and conditions. Support synchronous/asynchronous, optional/fallback and quorum semantics where known. Unknown semantics remain unknown.

**Probe definition:** operation, target, vantage/network namespace, credential reference, expected predicate, timeout, interval, cost and side-effect class.

**Observation:** immutable ID, subject, operation, event/receipt times, freshness limit, vantage, value/units, evidence lineage, collector status, predicate status, sampling/coverage, correlation/dependence group and redaction status.

Keep collection status and target predicate separate. A plugin crash or permission denial is a collection failure; it is not proof that the application failed. A validated target request exceeding its deadline may be evidence of target-operation failure. Support PASS/FAIL/UNKNOWN and fresh/stale explicitly, without collapsing all states to a boolean.

**Finding:** observation/inference/hypothesis type, supported failing boundary or candidate set, supporting and contradictory evidence IDs, unknowns, rule/model version, support assessment and registered next checks.

**Incident:** impact contract, interval, graph revision, evidence snapshot, candidate findings, relevant changes, history matches and operator-verified resolution status.

**Failure package:** version, technology applicability, required evidence, predicates, contradictions, predicted effects, bounded diagnostic recipes, source/licence and positive/negative/unknown fixtures.

**Action descriptor:** read/write classification, allowlisted targets, permissions, preconditions, deadline, side effects, approval policy and verification/rollback where relevant. Remediation execution is absent from the MVP.

Relations include RUNS_ON, LISTENS_ON, PROXIES_TO, DEPENDS_ON, CONNECTS_TO, STORES_IN, EMITS and MONITORED_BY. FAILURE_PROPAGATES_TO requires a validated mechanism or explicit hypothesis status; never infer it solely from network contact.

## 6. Plugin philosophy

Implement optional capabilities with common evidence outputs:

- Discovery adapter: emits entities and assertions.
- Telemetry adapter: reads mature exporters/backends or describes their configuration.
- Probe provider: performs one bounded observation.
- Declarative knowledge package: classifies evidence and supplies diagnostic recipes.
- Separately gated action provider: future extension only.

Descriptors specify schema/package version, platform/technology compatibility, permissions, deadlines, output/cardinality bounds and side-effect classes. Unknown target versions must be supported safely.

Start with bundled providers and supervised subprocess isolation where appropriate. Define structured request/response schemas, cancellation, process-group termination, bounded output and limited retries. Catch one plugin's failure without corrupting engine state. A timeout does not sandbox hostile code: external packages must remain trusted or require stronger isolation.

Do not introduce a marketplace, RPC mesh or universal abstraction before a concrete use case needs it.

## 7. Diagnostic semantics

Use layered checks as a graph traversal, not a universal linear hierarchy:

host → process → listener → protocol → dependency operation → readiness → functional transaction → external user path.

DNS/TLS/proxy/authentication may occur on multiple edges. UNIX sockets, remote services, replicas, caches, retries, asynchronous queues and optional dependencies break a simple chain. Represent AND/OR/quorum conditions; do not force cyclic topology into a causal DAG.

A PASS applies only to the measured predicate, subject, route, vantage and interval. A TCP success does not prove HTTP correctness. A database ping does not prove authenticated representative queries work. Local success does not contradict remote network failure.

Return the smallest evidence-supported failing operation/boundary or candidate set. Distinguish impact, location, mechanism, initiating trigger and shared contributor. Allow concurrent faults and abstain when evidence cannot separate candidates.

Mongo server connections are not application driver-pool utilisation. Never assume a universal connection limit. Pool exhaustion requires suitable driver checkout/wait/timeout evidence. PostgreSQL pg_isready is not a representative authenticated query check.

Include bounded temporal correlation and change context, but never equate temporal proximity with cause. Avoid recursive polling without a work budget.

## 8. Failure knowledge as data

Create inspectable packages for Linux/systemd, Nginx, Python HTTP deployment, DNS/TLS/network/filesystem, Mongo and PostgreSQL.

Seed patterns from current upstream documentation, verified monitoring checks, alert rules and runbooks. Preserve sources/licences and audit thresholds/units/version differences. No universal cross-technology failure schema was established in the baseline research; treat your schema as a project contract, not an industry standard.

Use validated predicates and registered action IDs. No executable YAML, arbitrary shell templates, embedded eval or unbounded regex. Every rule must explain missing evidence and contradictory predicates.

Cover stopped/failed/restarting services, absent/misrouted listeners, upstream errors, authentication failure, slow dependency operations, storage capacity/inodes, TLS expiry/hostname mismatch and independently instrumented pool wait. Do not infer memory leaks or slow-query causes merely from generic high resource values.

## 9. Confidence and LLM boundary

MVP confidence is an auditable ordinal support assessment, not an invented probability. Define gates for strong/moderate/weak/inconclusive findings. Expose required-evidence completeness, independent collection groups, reliability, contradictions, signature match, topology fit and temporal compatibility.

Do not count an alert and its originating log as independent evidence. Different collectors may still share clock, network or host failures. Stale or mismatched-vantage evidence cannot silently strengthen a conclusion.

Heuristic ranking is permitted only when labelled as heuristic. Future probabilities require a calibrated model and release/time-separated held-out evaluation, reliability plots, Brier/log loss, abstention and out-of-distribution checks.

The LLM may explain findings, summarize changes, propose hypotheses and request registered read-only checks. It may not invent facts, assign authoritative confidence, calculate forecasts, edit the graph directly or execute unrestricted commands. Schema/policy validation decides whether a requested check runs. Facts require returned evidence.

Treat logs, repository text, runbooks and tool output as untrusted data, including prompt injection. Bound tokens, calls and time. Redact before transfer. Each material explanation claim must cite evidence IDs; validate citations and prohibit unsupported additions. Deterministic rendering is the fallback and always remains available.

## 10. Minimal product

Implement a local agent/service with an embedded-store candidate and CLI commands equivalent to:

- discover / inspect coverage;
- check a supported application or path;
- diagnose a failed contract;
- report as human text and schema-valid JSON;
- export/replay a redacted incident bundle;
- inspect engine, plugin and collector health.

Discover systemd units/processes/listeners and safe Nginx upstream metadata. Combine these with an optional small manifest for identities, expected external routes, budgets and critical dependency contracts. Do not scrape whole environment-variable sets or assume names/ports identify software uniquely.

Provide CPU/memory/disk/inode observations; DNS/TCP/TLS/HTTP probes; application liveness/readiness checks; Mongo reachability and bounded representative operation; and equivalent PostgreSQL probes. Respect namespaces, UNIX sockets, credentials and target allowlists.

Provide one external user-path vantage in the acceptance environment. Synthetic operations must be read-only or explicitly designated disposable fixture operations. Limit their load.

Functional correctness requires an authoritative oracle. Generate proposed support contracts when helpful, but do not treat generated expectations as truth. An always-green health endpoint must not defeat an independent transaction check.

Ship the deterministic product before optional LLM integration. Exclude mandatory graph DB, vector DB, full source indexing, continuous profiling, graphical portal, automatic remediation and distributed coordination from the critical path.

## 11. Prediction, history and source extension

Define extension seams, not speculative implementations:

- Statistical prediction: slopes/headroom/backlog rates, EWMA/change points and sufficient-history seasonal models. Validate resets, discontinuities, missing data and fit uncertainty. Certificate expiry is date arithmetic; domain registration expiry needs a separate available source.
- Incident memory: structured filters and topology/failure fingerprints first; optional vector recall later. Preserve unresolved/retracted causes. Similarity is not causal evidence by itself.
- Code drill-down: infrastructure → dependency → endpoint → module → function → exact deployed source. Source/build identity is mandatory. Static possible calls and observed execution remain distinct.
- Distributed deployment: host agents/coordinator, authenticated scoped transport, bounded queues, idempotent ingestion and time-aware reconciliation.
- Docker/Kubernetes/cloud, Redis/queues, Java/.NET/Node and existing trace/eBPF adapters.
- Human-approved remediation, followed only later by narrowly validated automation.

## 12. Security

Default core to unprivileged, read-only operation. Put privileged collection in narrow helpers with explicit capabilities/allowlists. A read-only mount of a Docker socket does not make Docker API access read-only.

Use credential references resolved by executors. Database monitoring accounts receive only the privileges required for supported operations. No secrets/private keys/full configuration dumps in evidence bundles, logs, graphs or LLM input. Query text, database values and request bodies may contain PII; default to metadata/aggregate collection.

Restrict probe destinations, redirects and DNS resolution against SSRF/rebinding. Validate paths, subprocess arguments and action schemas. Add retention limits, redaction tests and secure file permissions. Remote mode later requires mTLS, scoped identity, RBAC, tenant isolation, revocation and audit.

Stages are OBSERVE, DIAGNOSE, RECOMMEND, APPROVED REMEDIATE and NARROW AUTOMATIC REMEDIATE. MVP stops at recommendation. Diagnostic confidence never grants action permission.

## 13. Support the support platform

Handle collector/plugin crash or hang, queue overflow, storage failure, stale/corrupt graph, bad rule, clock skew, coordinator disconnection and LLM outage.

Use bounded queues, deadlines, quotas, deduplication, explicit drops and backlog age. Preserve last-valid model revision with a stale label when an update fails validation. Reuse existing Collector buffering and self-telemetry where appropriate. Heartbeats must be accompanied by progress-age checks.

Local diagnosis continues without a coordinator or LLM. When collection fails, relevant target status becomes unknown/stale. An independent basic external watchdog detects total agent/host loss. Do not create an infinite chain of elaborate monitoring services.

## 14. Operator output

Every report must answer:

1. What user operation is affected?
2. Where is the supported failing boundary or candidate set?
3. Which evidence IDs support and contradict it?
4. What passed, at what vantage and time?
5. What changed?
6. What similar verified incidents exist, if history is enabled?
7. What is unknown or unobserved?
8. What next bounded check best separates candidates?
9. What action is permitted and what requires approval?

Include timestamps, source/collector health, graph/rule versions, coverage gaps and an escalation bundle. Avoid presenting unrelated successful checks as global health. Explain to a competent engineer unfamiliar with the application.

## 15. Testing and fault injection

Create meaningful unit/schema/contract/property tests for identities, predicate scope, graph reconciliation, missing/stale evidence, contradictions, deterministic replay, rule evaluation and plugin deadlines.

Integration tests must use disposable environments. Real systemd tests require a VM or suitable systemd-enabled environment. Ordinary Compose is insufficient to claim systemd support.

Inject at least:

- stopped Python and Mongo processes;
- wrong Nginx upstream TCP port and UNIX socket;
- reachable database with delayed/blocked representative operation;
- instrumented driver checkout wait/timeouts;
- revoked credentials;
- bounded test-volume capacity/inode exhaustion;
- DNS failure, TLS expiry and hostname mismatch;
- external-path failure with local-path success;
- undeclared observed dependency and dormant declared dependency;
- collector loss, stale evidence, plugin hang and LLM failure;
- two simultaneous faults and shared-host pressure;
- PID reuse, instance replacement and out-of-order observations;
- misleading green readiness and semantic error with/without an oracle;
- PostgreSQL connection success with blocked query;
- malicious log instructions, unsafe probe targets and secret-bearing fixtures.

Ground truth belongs to the test harness and must be hidden from diagnosis. Unknown/new failures must allow abstention. Include negative controls and held-out variants beyond the exact rule fixtures. Evaluate rule changes against prior incident bundles.

Compare raw alerts/telemetry, an existing monitoring configuration and the support report on identical cases; include Coroot comparison where feasible. If unavailable, record the limitation honestly. Do not fabricate benchmark results.

Report top-1/top-k localisation, false causal claims, abstention, checks/time to useful boundary, operator success, evidence traceability and resource overhead. Run an unfamiliar-operator study where feasible; otherwise provide a reproducible study protocol and mark it pending.

## 16. Recursive architecture and implementation review

Compare A traditional monitoring + AI; B OTel-centric; C eBPF-first; D code-first; E catalogue-first; F graph/twin-first; G constrained hybrid.

Preserve 0–5 vectors for PORT, AUTO, DEPTH, EXT, CLAR, AI, DET, SEC, OPS, FAIL, SCALE, LOCAL, COST and LOCK. Higher is favourable; COST means lower cost and LOCK means independence. Define the rubric and workload. Do not invent a scalar score or imply subjective numbers are measurements.

Perform explicit review passes covering existing art, gaps, alternatives, failure, operability, unknown source, deterministic/LLM split, unfamiliar operator, scale, simplification and re-scoring. Reopen decisions after failed tests or new evidence. Record actual changes, test results and pass count in `docs/review-log.md`.

Converge only after two successive documented review cycles produce no material new architecture/simplification, no vector movement above one point and no new high-impact failure category, while required tests pass. Stability is not evidence of universal correctness. Set a finite review budget and report blockers instead of endlessly self-scoring.

## 17. Acceptance gates

- Fresh evidence can localise supported injected boundaries without whole-repository indexing or an LLM.
- Every material diagnostic claim resolves to retained evidence and a versioned rule/model.
- Missing, stale, denied and failed collection never silently become PASS.
- Local/remote and operation-specific results remain correctly scoped.
- Driver-pool, server-connection and query-operation failures are not conflated.
- Multiple faults and contradictions do not force one confident cause.
- PostgreSQL uses the same core contracts without technology-specific core branching.
- Hung plugins terminate within configured deadlines; deterministic reporting survives LLM failure.
- Unsafe targets, secret transfer and telemetry prompt injection are covered by tests.
- No remediation runs by default, and the deployed permissions match documentation.
- Define measurable latency/resource/storage budgets before performance testing; publish the hardware, workload and actual results. Do not claim budgets passed without measurements.
- Installation, removal, offline use and incident replay work in the supported reference environment.
- Existing-tool comparison shows the incremental benefit, or the design is simplified to an integration that does.

## 18. Deliverables

Provide working source, packaging, schemas/migrations, plugin contracts, rule packages, sample manifest, disposable reference-stack harness, automated tests, fault-injection cases and redacted example reports.

Documentation must include README/quickstart, architecture and ADRs, research/source ledger, schema reference, plugin author guide, security/privilege matrix, coverage limitations, operator guide, support-platform recovery, test/performance report, review vectors and extension roadmap. Add `AGENTS.md` explaining invariants, commands, evidence rules and safe contribution boundaries for future coding agents.

Maintain one inspectable route from a report claim to evidence, topology revision, collection method and rule implementation. At completion state what works, how it was tested, what remains unknown and which acceptance gates remain pending.

Final test:

> If an AI generates 500,000 unreviewed lines tonight and the application fails tomorrow, can an unfamiliar engineer identify a justified starting boundary, inspect the evidence and perform a safe next check?

The answer must not depend on previous human source familiarity, ungrounded log guessing or replacing mature observability infrastructure. It may legitimately stop at a boundary and explain the evidence still needed to determine the cause.
