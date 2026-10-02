# Extension roadmap

Current 0.3.0 ships local Docker and static Python venv modules alongside PostgreSQL/Nginx, with offline reviewed-card retrieval and deterministic generation. See [coverage](coverage.md) for current limits. The following items remain extensions; proceed when measurable operator benefit warrants the component.

1. Add reviewed native Checkmk/Coroot/backend connectors in place of exported snapshots; measure useful-boundary time against the same faults and an unfamiliar operator.
2. Add full config interpretation, workload/collector coverage contracts, explicit absence rules and an automatic stale last-valid graph snapshot.
3. Add application-specific representative reads and real remote watchdogs; support managed DB TLS, replicas and sockets without broadening credentials or target scope.
4. Structured verified incident fingerprints and retracted/unresolved outcomes; similarity remains separate from causal support.
5. Statistical trend extensions with discontinuity/missing-data/fit tests: headroom slopes, EWMA/change points, calendar expiry. No LLM arithmetic.
6. Demand-driven source/symbol drill-down only after a boundary is narrowed, with exact deployed build identity; static possible calls and observed executions remain distinct.
7. Expand Docker beyond local Linux API snapshots, add Kubernetes/cloud, Redis/queues and Java/.NET/Node adapters, and define an explicitly authorized approach to venv runtime/ABI checks; existing OTel/eBPF integrations before custom instrumentation.
8. Authenticated scoped coordination, bounded reconnect queues, mTLS/RBAC/tenant isolation and clock-aware idempotent ingestion.
9. Optional model explanation with process isolation, strict evidence citations, redaction and hard cost/deadline limits. Free-form claim validation is unresolved; deterministic output always remains complete.
10. Separately authorised remediation provider with target scopes, preconditions, verification and rollback. The current product stops at recommendation.
