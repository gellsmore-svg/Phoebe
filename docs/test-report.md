# Test and performance report

## Current recorded validation: 0.3.0 (2 October 2026)

[Docker/venv validation](docker-venv-validation-results.json) records 217 passing automated tests, 25 actual disposable cases, 34/34 official source fetches and offline wheel installation, an installed venv probe, four-family retrieval, old/enriched replay and uninstall. Existing containers were preserved and owned containers cleaned; commands/files used cello (UID 1000). The [module guide](docker-venv-modules.md) distinguishes static metadata, real fault injection, threshold edges and unknown coverage.

[PostgreSQL/Nginx validation](service-validation-results.json) retains the separate 0.2.0 run: 157 automated tests, 22 service cases, 20 broader regression cases, 20 source fetches and offline packaging checks. Counts from different versions/runs are not added, and the original performance/localization measurements below have not been rerun as 0.3.0 RAG benchmarks. Production, public/remote paths, replicated standby, remote/rootless Docker deployment and venv native imports/ABI remain unmeasured.

Current reproduction commands, run as cello from the checkout:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python harness/run.py
.venv/bin/python harness/service_modules.py
.venv/bin/python harness/docker_venv_modules.py
.venv/bin/python harness/systemd.py
.venv/bin/python harness/benchmark.py
.venv/bin/python harness/offline_install.py
```

Integration harnesses inject faults only into uniquely owned disposable fixtures. Offline installation requires a prepared local wheelhouse; see [operator setup](operator-guide.md). Source audits contact the fixed official inventory and use a new receipt filename. [Acceptance](acceptance.md) retains unfinished broader release gates.

## Initial implementation measurements (1 October 2026)

Historical baseline below was executed on 1 October 2026 as cello. Source and actual machine-readable results accompany this report. Retained examples contain only safe metadata and original rule packages, not fixture passwords, response bodies or database values.

78 automated pytest cases passed in 14.03 seconds. Coverage includes versioned schemas, immutable store/quota rollback/corruption, entity revisions/PID reuse, topology views, freshness and out-of-order observations, scope/contradictions, driver evidence requirements, unknown signatures, exact replay, deadline/process-group termination/output caps, hostile target syntax/rebinding, log injection/secret redaction, real TCP/UNIX/HTTP/TLS probes and valid/expired/hostname-mismatched certificates. Rule fixtures include PASS/FAIL/UNKNOWN for every bundled rule package; held-out route, oracle, TLS and simultaneous-fault variants extend those fixtures.

Docker harness: 20 cases passed. Nineteen exercise real disposable services/probes (including healthy/no-oracle/external controls); one temporal-topology case is explicitly a synthetic assertion fixture. Cases include stopped Python and Mongo, wrong proxy TCP/UNIX upstream, representative Mongo delay while ping passes, authenticated PostgreSQL connection while the read is blocked by a real lock, independently instrumented application-driver pool wait/timeouts, revoked accounts, real bounded tmpfs byte/inode exhaustion, DNS failure, a separate probe container namespace, external-path failure/local success and two simultaneous faults. It hides ground truth from diagnosis. Initial failures and corrections are recorded in review-log.md; final successful results are in integration-results.json.

A separate real Linux systemd user-manager harness confirms active/stopped declared Python service classification and removes its unique transient unit. This does not claim system-level deployment from Compose. TLS/host/PID/collector/LLM failure variants are automated live-probe or contract tests, not all Docker stack injections. A real shared-host pressure experiment remains pending.

Final Docker cleanup succeeded: True. Existing container names remained present: True. Image IDs and registry digests are retained in integration-results.json; mutable reference tags are {'app': 'support-evidence-fixture:0.1.0', 'mongo': 'mongo:8.0', 'pg': 'postgres:18', 'nginx': 'nginx:1.28-alpine', 'blackbox': 'prom/blackbox-exporter:v0.28.0', 'storage': 'support-evidence-fixture:0.1.0'}. Docker daemon 29.7.1, Python 3.12.3, kernel 6.18.40.1-microsoft-standard-WSL2.

Predeclared 1,000-observation benchmark: 0.787 seconds diagnosis, 38.74 MiB peak RSS, 870,200 bytes retained bundle, 10 failing scopes. Budgets were <2 seconds, <128 MiB and <8 MiB. Replay was identical. Hardware: AMD Ryzen 7 5800H with Radeon Graphics, 16 logical CPUs, Python 3.12.3. This measures the CLI workload, not continuous agent overhead or fleet scalability.

Offline wheelhouse installation in a fresh temporary venv, exact incident replay and package uninstall passed without network access; disposable venv removed. The initial run retained dependency snapshots in requirements-runtime.lock and requirements-dev.lock. These describe reference inputs, not a complete 0.3.0 runtime lock; current project metadata adds packaging for venv checks. Packaging wheel and wheelhouse are under dist/; the wheelhouse contains platform-specific rpds-py for this Linux/Python 3.12 environment.

Existing monitoring baseline: Blackbox Exporter v0.28.0 correctly reported failure on the same disposable wrong-port target (True). Its raw Prometheus output is retained separately. This confirms that basic failure detection already exists; incremental portable evidence/report fields are demonstrated, while a statistically meaningful matched-case comparison and operator success study are pending.

Localization evaluation: top-1 measured-boundary hit 16/16 and top-k expected boundary-set recall 16/16 on positive harness cases; controls are excluded. These coarse labels describe tested predicates, not initiating root causes or held-out production accuracy. Traceability checks pass for all reports. Unknown signatures abstain in unit tests, but a heterogeneous abstention rate and operator success remain unmeasured. No initiating cause is asserted by current templates; general false causal-attribution accuracy is unmeasured. Per-case `diagnosis_ms` includes report export and replay-validation I/O, while the separate 1,000-record benchmark measures pure diagnosis. Counts and caveats are retained in localization-metrics.json.

Run: `.venv/bin/python -m pytest -q`; `harness/run.py`; `harness/systemd.py`; `harness/benchmark.py`; `harness/offline_install.py`. Per-case check durations and event timestamps are retained in example bundles and .harness results. Acceptance.md lists pending gates.

## Service modules in 0.2.0

[Final service validation](service-validation-results.json) records 157 passing automated tests, 22 PostgreSQL/Nginx scenarios, the broader 20-case harness, 20 official source fetches and offline installation/retrieval/replay/removal. [Coverage and limits](service-modules.md) distinguish real faults, threshold edge cases and unit doubles.
