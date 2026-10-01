# Reproducible unfamiliar-operator study (pending)

Recruit engineers who have not read fixture application code. Give all arms the same public user-operation oracle, faults, timestamps and permitted read-only targets. Randomize order, separate fault variants into held-out cases, and hide injection labels/configuration from operators and diagnosis.

Arms: raw telemetry/alerts, reviewed Blackbox Exporter plus existing monitoring configuration, and the evidence report plus the same telemetry. Include Coroot where a suitable instance/account exists. Do not give the evidence arm extra observability without reporting the difference. Vary proxy ports/sockets, independently delayed DB reads, revoked accounts, unknown faults and concurrent failures. Avoid exact rule-fixture leakage.

Measure time/check count to first justified boundary, top-1/top-k boundary accuracy, false cause assertions, abstention, evidence traceability, successful safe escalation and task completion. Capture operator confidence separately from rule support. Record hardware/load, sensor coverage and overhead in every arm. Report uncertainty and case distributions rather than a single favourable anecdote.

Stop at a predeclared 20-minute per-case limit. No operator is asked to repair production; only registered fixture read-only checks are permitted. A useful report must explain scope and unknowns and improve justified investigation without increasing false attribution. If no incremental benefit appears, simplify to the mature monitoring integration.

No human study was performed during this implementation. No operator success/MTTR improvement is claimed.
