# Recursive failure review

This review follows each measured boundary through prerequisites and downstream contracts, then tests counterexamples to a healthy/cause conclusion. It is an explicit dependency/failure-tree review, not a confidence score or independent-model consensus claim.

## Docker

1. Socket access depends on the declared path, user permissions, daemon/user-service lifecycle, runtime-directory persistence and namespace. A reachable version endpoint still leaves API compatibility and container existence separate. Denial cannot mean a stopped workload.
2. Container existence depends on exact instance identity and lifecycle. A name can be reused; running, paused, restarting and exited differ. Manual restart is a counterexample to interpreting RestartCount as all restarts. Resource samples must retain start/restart/limit cohort identity.
3. Health depends on a configured check, its startup interval and its dependency contract. Running without a check and starting with a check are counterexamples to healthy. A healthy check does not prove the published route or an authoritative application oracle.
4. Resource headroom depends on configured cgroup limits and visible counters, then host capacity, swap, CPU throttling, PID limits and application allocation patterns. An unbounded limit and exit 137 are counterexamples to known headroom and proven OOM. The implemented snapshot checks memory/PID; CPU/trend/leak/host causality remain unmeasured.
5. Application availability recursively depends on container DNS/network/port routing, Nginx host/TLS/proxy behavior, database authentication/role/locks/replication, mount/UID/readonly policy and filesystem capacity/inodes. Existing separately scoped modules can measure these boundaries. No container-state observation proves the whole chain.
6. Collector failures depend on API permissions, supported versions/platform, response budgets, malformed fields, socket replacement and lifetime races. UNKNOWN barriers prevent older successful evidence from filling current gaps.

## Python venv

1. Declared root depends on cfg structure, base installation, interpreter entry, version intent and permissions. A regular executable named python can still be the wrong binary; static PASS makes no interpreter-execution claim.
2. Entry scripts depend on their absolute shebang paths. A moved environment with an intact base symlink is a counterexample to complete layout usability. Shell/env trampolines require facts this static collector cannot establish.
3. Isolation depends on cfg intent, then actual process prefix, import paths, .pth hooks, activation context and system package visibility. cfg isolation PASS does not imply an existing service uses this environment. Hooks and unknown external paths are never executed to resolve ambiguity.
4. Dependencies depend recursively on normalized distribution identity, versions, Requires-Python, marker environment, activated extras and transitive requirements. Cycles terminate through a bounded fixed point. Present top-level packages can have missing transitive edges or incompatible versions. Unknown target platform must not inherit collector platform.
5. Metadata visibility depends on regular local files, parse/version completeness, duplicates, legacy/editable hooks, budgets and concurrent installation. Positive missing/version failures and incomplete visibility can coexist. Rechecks detect observed races, while cross-file atomicity remains a limitation.
6. Runtime success additionally depends on import-name mapping, package payload integrity, architecture/native ABI, dynamic loaders, permissions and downstream services. Static metadata cannot prove these. Product code neither executes target interpreter nor performs installation or remediation.

## Verification closure

The new tests exercise direct counterexamples, privacy and scope separation. Actual disposable fixtures verify Engine classifications and local venv state, including a 64 MiB-capped OOM container. Golden 0.1/0.2 incidents preserve historical semantics and bm25-1 generation. Offline wheel validation confirms packaged assets, all four service searches, replay and removal. Production, remote/rootless Docker and Windows/native-import behavior remain outside the claimed validation scope. Source refresh receipts audit availability; they do not turn documentation into incident evidence.
