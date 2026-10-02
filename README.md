# Phoebe — Support Evidence

[Phoebe](https://github.com/gellsmore-svg/Phoebe) is a local CLI for evidence-scoped operational diagnosis. It collects explicitly allowed read-only checks, imports monitoring exports, identifies measured failing boundaries and exports incidents that replay offline. Version **0.3.0** includes PostgreSQL, Nginx, Docker and Python venv modules, plus optional source-grounded retrieval and deterministic generation.

Runtime conclusions come from scoped observations. Retrieved documentation supplies alternatives and next checks; it does not establish an initiating cause. The core needs no telemetry backend, graph database, vector service or LLM account.

## Quickstart

From a checkout, run as your ordinary Linux user (`cello` in this workspace). Python 3.11 or newer is required; the recorded reference environment is Linux/WSL with Python 3.12.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,databases]'
.venv/bin/support-evidence --version
.venv/bin/support-evidence replay examples/incident-docker-module.json
.venv/bin/support-evidence replay examples/incident-venv-module.json --json
```

These retained examples replay without live Docker, a target venv, database credentials or network access. Core installation uses `pip install -e .`; database collectors additionally need the `databases` extra. The `dev` extra supplies test/build dependencies. See the [operator guide](docs/operator-guide.md) for collection and escalation.

## Supported checks

| Family | Measured contracts | Guide |
|---|---|---|
| PostgreSQL | Connection, fixed fixture read, role, activity, blocking, connection headroom, replication backlog and frozen-XID age | [PostgreSQL/Nginx modules](docs/service-modules.md) |
| Nginx | Declared HTTP route/oracle and optional stub_status active-client threshold | [PostgreSQL/Nginx modules](docs/service-modules.md) |
| Docker | Approved local Engine socket, exact-ID container state, configured health and memory/PID headroom | [Docker/venv modules](docs/docker-venv-modules.md) |
| Python venv | Static layout/version intent, isolation setting, script paths and recursive dependency metadata | [Docker/venv modules](docs/docker-venv-modules.md) |
| Network, host and services | DNS/TCP/UNIX/TLS/HTTP, capacity/inodes, load/available memory and named system/user-systemd state | [Coverage](docs/coverage.md) |
| MongoDB and monitoring | Authenticated ping/fixed fixture read; Prometheus, Monitoring Plugins and OTLP JSON snapshots | [Operator guide](docs/operator-guide.md) |

Docker checks issue fixed GETs; they never run container commands. Venv checks never execute target Python, pip, imports, activation or path hooks. A static metadata PASS does not establish runtime import/ABI compatibility. Missing, denied, stale and unsupported evidence remain explicit. See [coverage limits](docs/coverage.md) and [security and privileges](docs/security.md).

## Capture and retrieve guidance

Choose a manifest example: [base contracts](examples/manifest.json), [PostgreSQL/Nginx](examples/manifest-service-modules.json), or [Docker/venv](examples/manifest-docker-venv-modules.json). Copy it to `my-manifest.json` and review targets, addresses, paths, thresholds, identities and the actual execution vantage. Database monitoring accounts and fixture tables must already exist; checks create neither.

```bash
.venv/bin/support-evidence --store ./evidence.sqlite check ./my-manifest.json --rag --export ./incident.json
.venv/bin/support-evidence replay ./incident.json --json
.venv/bin/support-evidence knowledge search docker docker_unhealthy --json
.venv/bin/support-evidence knowledge search venv venv_dependencies_missing --json
```

Exports require a new filename. `--rag` adds a separate knowledge context to text/JSON and embeds reviewed cards in the incident bundle. Current retrieval uses 45 original cards from 34 official sources across four families; searches and enriched replay work offline. [Knowledge and replay](docs/knowledge.md) explains versions, output shapes, source audits and guidance limits.

For `check`, `report` and `diagnose`, exit 0 means no supported failure with fresh applicable evidence, 1 means at least one strong/moderate failing boundary, and 3 means inconclusive or an input/policy/storage failure. Replay success returns 0 even when the retained incident contains failures. Read coverage and unknowns before interpreting a result as health.

## Validation and development

The recorded 0.3.0 validation passed **217 automated tests**, **25 actual disposable Docker/venv cases**, **34/34 source fetches**, and offline installation, an installed venv probe, search, replay and removal. Earlier version-specific validation records remain available; these counts describe different runs and are not summed. See the [test report](docs/test-report.md), [results](docs/docker-venv-validation-results.json) and [pending acceptance gates](docs/acceptance.md).

```bash
.venv/bin/python -m pytest -q
.venv/bin/python harness/service_modules.py
.venv/bin/python harness/docker_venv_modules.py
```

Integration harnesses create uniquely named owned fixtures, mutate only those fixtures and clean up containers. They perform real fault injection into disposable resources. The broader stack, user-systemd and performance harnesses are documented in the [test report](docs/test-report.md). Follow [contribution rules](AGENTS.md); commands and writes in this workspace run as cello.

After building the wheel and preparing `dist/wheelhouse`, offline installation is:

```bash
pip install --no-index --find-links dist/wheelhouse support-evidence==0.3.0
```

Build artifacts are local and ignored by Git. A fresh clone needs a prepared wheelhouse; the validated wheelhouse targets Linux/Python 3.12. See the [operator guide](docs/operator-guide.md) for build steps and dependency snapshot limits. `pip uninstall support-evidence` preserves separately owned stores and incident bundles.

## Documentation

The [documentation index](docs/README.md) links operator, architecture, schema, security, module, retrieval, validation and research material. [Version history](CHANGELOG.md) records the implemented package versions. The two supplied supportability briefs remain verbatim under [docs/baseline](docs/baseline).

The Python package and command are `support-evidence`. This workspace checkout is `/mnt/c/Users/cello/support-evidence`; the GitHub name follows the biblical-name convention used by sibling repositories. Store sensitive operational data on a Linux filesystem with effective private permissions; Windows DrvFS can report broad modes.
