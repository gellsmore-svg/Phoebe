# Phoebe — Support Evidence

Phoebe follows the biblical-name convention used by the sibling repositories.

A local CLI that gives an unfamiliar engineer a measured failing boundary, retained evidence and a bounded next check. It imports existing monitoring exports and performs explicitly allowlisted read-only probes. Diagnosis needs no LLM, source index, telemetry backend or graph database.

Created from the two supplied supportability briefs, retained in [docs/baseline](docs/baseline). This is an initial working implementation. [Acceptance status](docs/acceptance.md) distinguishes passed checks from pending release gates.

## Quickstart

Run as your ordinary Linux user (cello here):

```bash
cd /mnt/c/Users/cello/support-evidence
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,databases]'
.venv/bin/python -m pytest -q
.venv/bin/support-evidence --store /tmp/support-evidence-demo.sqlite discover
.venv/bin/support-evidence --store /tmp/support-evidence-demo.sqlite health
```

Discovery is read-only and records bounded process/listener/systemd inventory. It does not automatically probe discovered addresses. Copy [the manifest](examples/manifest.json), review destinations, predicates, vantage, budgets and monitoring accounts, then run:

```bash
.venv/bin/support-evidence --store ./example.sqlite check ./my-manifest.json --export ./incident.json
.venv/bin/support-evidence replay ./incident.json
.venv/bin/support-evidence replay ./incident.json --json
```

The sample manifest is a contract example, not an assertion that those ports belong to your applications. No fixture database is created by a check. Mongo reads only `support_probe` with `_id=1`; PostgreSQL executes only the registered fixture count. The database extras and reviewed monitoring credentials are required for those probes.

CLI exit codes: 0 no supported failure (check coverage), 1 supported failing predicate, 3 inconclusive/validation/collection failure. A zero status does not establish business correctness or health of unmeasured paths. Reports always preserve route, operation, vantage and timestamp.

## Reproducible verification

```bash
.venv/bin/python harness/run.py
.venv/bin/python harness/systemd.py
.venv/bin/python harness/benchmark.py
```

Docker harness creates a unique network and temporary containers, seeded fixture databases, proxy and an independent probe namespace; cleanup runs in `finally`. No existing containers are selected for mutation. The separate systemd harness uses a uniquely named transient user-manager unit and cleans it up. Results appear under `.harness/`; checked-in redacted examples are under `examples/`.

See [operator guide](docs/operator-guide.md), [architecture](docs/architecture.md), [schema reference](docs/schema-reference.md), [plugin guide](docs/plugin-guide.md), [security](docs/security.md), [coverage limits](docs/coverage.md), [recovery](docs/recovery.md), [research](docs/research.md), [review log](docs/review-log.md) and [test report](docs/test-report.md).

A retained example can be replayed immediately:

```bash
.venv/bin/support-evidence replay examples/incident-mongo-operation.json
```

Offline core installation is available with `pip install --no-index --find-links dist/wheelhouse support-evidence==0.2.0`. The supplied wheelhouse targets Linux/Python 3.12; rebuild dependency wheels for another platform. Removal uses `pip uninstall support-evidence` and preserves separately owned incident bundles/stores.

GitHub repository: [gellsmore-svg/Phoebe](https://github.com/gellsmore-svg/Phoebe). The Python package and CLI remain `support-evidence`; the local checkout remains `/mnt/c/Users/cello/support-evidence`. Commits use a repository-only `cello <cello@localhost>` identity. File-writing and validation commands run as cello. Linux filesystem mode enforcement should be used for sensitive operational stores; this checkout is on Windows DrvFS.

PostgreSQL and Nginx have explicit bounded support modules with classified failure signatures, monitoring visibility checks and offline retrieval from 26 original cards grounded in official documentation. Use `support-evidence check examples/manifest-service-modules.json --rag --export incident.json` after adjusting the example policy and credentials. See [service modules and RAG](docs/service-modules.md) for operations, privileges, failure coverage and replay guarantees. [Actual service-module results](docs/service-module-results.json) record 22 disposable scenarios; production and replicated-standby coverage remain pending.
