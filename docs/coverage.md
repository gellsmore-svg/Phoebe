# Coverage and limitations

Current version: 0.3.0. Working: Linux process/listener/service inventory; safe Nginx destination metadata; explicit DNS/TCP/UNIX/TLS/HTTP contracts; filesystem and host aggregate predicates; named global/user-systemd state; authenticated representative Mongo and PostgreSQL fixture reads; Prometheus/Monitoring Plugins/OTLP JSON snapshot import; temporal topology projection; deterministic ordinal findings and redacted incident replay.

| Current module family | Implemented scope | Remaining gaps |
|---|---|---|
| PostgreSQL (8 operations) | Fixed read/connection, role, activity/locks, ordinary connection headroom, replication byte/count contracts and frozen-XID age | Live replicated standby, managed/pooler combinations, actual exhaustion/WAL failures and production comparison |
| Nginx (2 operations) | Declared HTTP route/oracle and strict optional stub_status contract | Complete config interpretation, worker/upstream occupancy, interval loss estimator and production/build combinations |
| Docker (4 operations) | Local Linux Engine API, immutable-ID lifecycle, configured health and memory/PID headroom | Remote/Windows transports, rootless deployment integration, CPU/trend/host causality and automatic context discovery |
| Python venv (4 operations) | POSIX 3.11–3.14 static cfg/layout, isolation, script paths and recursive package metadata | Target execution, ABI/import/payload correctness, running-service identity, Windows and filesystem-wide atomic snapshot |
| Offline guidance | 45 reviewed cards, bm25-2/template-1, enriched export and versioned replay; fixed source audit | Live generative model, continuous source indexing, automatic summary updates or documentation-authoritative runtime facts |

See [PostgreSQL/Nginx](service-modules.md), [Docker/venv](docker-venv-modules.md) and [knowledge](knowledge.md). Card coverage describes investigation branches, not full collector coverage.

Boundaries have limits. HTTP failures are localized to the tested route/functional contract; retained upstream configuration and an independent healthy direct route narrow investigation, but do not prove proxy misconfiguration or a particular Nginx source line. The safe parser is not a full Nginx configuration interpreter. Discovery does not bind every socket to a process or assert absent expected instances without collection coverage. Logical identity/version conflict is preserved and requires operator reconciliation.

Only the current network namespace is supported. A distinct container probe is an independently executed network vantage; it is not a public Internet probe. Genuine public/remote-host user-path acceptance is pending. Direct database fixture reads demonstrate portable contracts, not application-specific query coverage. Mongo replicas/SRV, UNIX database sockets, arbitrary representative SQL, database profiling and multiple upstream-auth paths are pending. Network UNIX socket connection is implemented separately.

Host observations expose load and available memory, not a calibrated CPU-saturation or memory-leak mechanism. Collection is on demand; there is no continuous metrics warehouse or autonomous investigator. Capacity/inode thresholds and functional oracles are explicit contracts, never generated truths. Known condition/quorum fields are retained without an automatic propagation solver.

A direct fresh measured failure can strongly support its boundary; this does not establish independence, mechanism, initiating trigger, shared cause or safety. Imported evidence is moderate. Missing/stale evidence, failed collection, contradictions, clock skew and unknown signatures allow abstention. Historical similarity, statistical forecasts, exact source drill-down, eBPF, remote coordination, live LLM explanation and remediation are extension work. The citation-selector fallback seam is not a deployed LLM integration.

Storage has explicit caps and atomic ingestion, not guaranteed continuous availability. Queue overflow is avoided by synchronous bounded work; failed storage is surfaced by an exit error and no health assertion. There is no reserved emergency storage queue. Corrupt-store recovery is manual using verified bundles; a separate cached last-valid graph with an automatic stale marker is not implemented.

The Docker harness validates real disposable stack faults; the separate real user-manager test validates Linux systemd state collection. System-level unit deployment, service sandbox configuration, privileged discovery, multiple distributions and physical host loss are pending. Never generalize Compose to systemd support or fixture tests to production readiness.

[Current recorded validation](docker-venv-validation-results.json) covers 217 automated tests, 25 actual Docker/venv fixture cases, source receipts and offline installed-collector/replay checks. [Earlier service validation](service-validation-results.json) records PostgreSQL/Nginx fixtures separately. These are scoped results, not production readiness or aggregate benchmark accuracy.
