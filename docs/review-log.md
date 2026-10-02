# Bounded architecture and implementation review

Date: 2026-10-01. Budget: 15 documented passes; used 15. These are engineering reviews and actual test-driven changes by one coding agent, not independent experiments or repeated independent LLM invocations. Original research's 14 desk-review passes are preserved separately and are not counted as implementation reviews.

Reference workload: one Linux host with an opaque HTTP service/proxy, Mongo and PostgreSQL boundaries, offline evidence portability, ordinary-user operation and eventual heterogeneous extension. Scores are subjective architectural judgments, not measurements. Rubric 0 absent, 1 poor, 2 constrained, 3 adequate, 4 strong, 5 very strong. COST means lower cost; LOCK means independence. No scalar winner or statistical significance is implied.

Dimensions: PORT portability; AUTO discovery; DEPTH diagnostic depth; EXT extensibility; CLAR clarity; AI machine readability/reasoning support; DET evidence quality; SEC least privilege; OPS simplicity; FAIL support-platform resilience; SCALE scale; LOCAL offline; COST cost; LOCK independence.

| Architecture | PORT | AUTO | DEPTH | EXT | CLAR | AI | DET | SEC | OPS | FAIL | SCALE | LOCAL | COST | LOCK |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A Monitoring + AI |4|3|3|4|3|3|4|4|4|4|4|4|4|4|
| B OTel-centric |4|3|3|5|3|4|4|4|3|4|5|4|4|5|
| C eBPF-first |2|4|3|3|3|4|4|2|2|3|4|4|3|4|
| D Code-first |4|2|3|3|2|4|3|4|2|2|3|4|2|4|
| E Catalogue-first |4|2|2|4|4|4|2|5|4|3|4|3|3|4|
| F Graph/twin-first |4|2|3|5|3|5|3|4|2|3|3|4|2|5|
| G Research constrained hybrid |4|4|4|5|4|5|4|4|3|4|4|5|4|5|
| G Implemented adapter/report layer |3|3|3|4|4|4|4|4|4|3|3|5|4|5|

A–F vectors retain the provided research rubric, not vendor benchmarking. G is revised downward for Linux-only discovery, fixture-limited operations, incomplete model recovery and a sequential work budget; simpler operation improves OPS by one. Future heterogeneous breadth, operator benefit and causal depth remain unmeasured. Each final change is at most one point, and the two closure reviews preserve these vectors unchanged.

| Pass | Review and evidence | Actual change/outcome |
|---:|---|---|
|1|Existing art and current primary pages|Verified Coroot's non-LLM analysis/LLM explanation, OTel Development entity model and Checkmk separation; rejected novelty and telemetry-backend scope.|
|2|Unresolved gaps|Choose inspectable evidence contracts, retention, route/vantage scoping and replay.|
|3|Alternatives/build-versus-integrate|Use exported mature monitoring inputs plus direct bounded operation probes; no graph server/LLM dependency.|
|4|Failure semantics|Separate collection status and target predicate, stale/clock-skew/unknown, multiple faults and contradictions; meaningful negative controls.|
|5|Operability|One supervised worker, output/work/store budgets, atomic ingestion, no retries or remote package execution.|
|6|Unknown source|Diagnose without repository indexing; authoritative oracle required; green-readiness/no-oracle controls.|
|7|Determinism/LLM boundary|Ordinal measured support and closed citation fallback seam; no free-form authoritative model claims or actions.|
|8|Unfamiliar engineer|Expose evidence reasons, method, times, versions, safe next check and approval boundary; add study protocol.|
|9|Scale/identity|Host/boot/start-tick process IDs, immutable entity revisions, out-of-order event precedence; expand aggregate-report cap independently of scalar-record cap.|
|10|Simplification/re-score|Freeze implemented G vector; omit speculative history, forecasts, coordinator, remediation and full Nginx interpreter.|
|11|Live stack fault review|Found TLS IP-name verify code, absent UNIX predicate classification and ephemeral restart port issues; corrected them.|
|12|Deadline and systemd review|Initial blocked-query/stopped-Mongo runs returned truthful collection UNKNOWN; absolute worker budget, post-import/cleanup reserves and explicit five-second DB fixture budgets fixed target evidence delivery. Missing named units are a measured active-state failure.|
|13|Security/packaging|Reject option-like systemd names and use `--`; recompute hashes after redaction, detect stale built wheel and rebuild. Confirm secret fixtures absent from exported bundles.|
|14|Closure cycle A|78 automated tests, 20 labelled harness cases (19 real probe/service cases including controls, one topology fixture), real user-manager systemd, benchmark and offline installation/replay/removal pass. No new material architecture change, no score movement or new high-impact failure category.|
|15|Closure cycle B|Review preserved receipts, bundle replay, current wheel/source identity, privilege/coverage docs and cleanup. Vectors unchanged; no new material simplification/high-impact category. Remaining release gates explicitly carried into acceptance.md.|

The implemented-scope review is stable after the two closure cycles. This does not declare universal architecture convergence or production acceptance: the full brief's pending gates remain open. Reopen immediately after a new failed fixture, real incident, operator study or platform/collector change. The finite review budget ends here with visible limits rather than inventing self-scored certainty.

## Documentation maintenance — 2026-10-02

Aligned the repository overview, operator/architecture/schema/security/coverage guides and roadmap with committed 0.3.0 behavior. Added the documentation index, shared knowledge/replay guide and implemented version history. Historical 0.1.0/0.2.0 test and performance claims retain their original scope; current validation is linked separately. This is documentation maintenance, not another independent experiment or extension of the earlier 15-pass review budget.
