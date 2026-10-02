# Operator guide

This guide describes Phoebe 0.3.0. Start with a reviewed user-operation contract. An expected status, threshold or oracle must come from the requirement for that operation. Readiness does not establish a separate business operation.

## Capture an incident

1. Review `discover` inventory and `coverage`; resolve ambiguous identities. Discovery authorizes no automatic probes.
2. Copy a [base](../examples/manifest.json), [PostgreSQL/Nginx](../examples/manifest-service-modules.json) or [Docker/venv](../examples/manifest-docker-venv-modules.json) manifest. Set exact targets/routes, approved resolved addresses or paths, actual vantage, instance identity and explicit thresholds.
3. Run `check` and export to a new filename. Use `--rag` when escalation should include source-grounded guidance.
4. Read supporting and contradictory evidence, collector health, unknowns, methods and timestamps. Several boundaries can fail; ping does not overrule a separately scoped read failure.
5. Perform a recommended read-only next check through an appropriate reviewed manifest. Recommendations are not automatically executed.
6. Share the retained bundle for escalation. Replay works without the target application, source repository, telemetry backend or live services.

```bash
support-evidence --store ./evidence.sqlite discover
support-evidence --store ./evidence.sqlite check ./my-manifest.json --rag --export ./incident.json
support-evidence replay ./incident.json --json
support-evidence --store ./evidence.sqlite report --rag --json
support-evidence --store ./evidence.sqlite coverage
support-evidence --store ./evidence.sqlite health
```

`--store` is a global option and precedes the command. Without it, collection/report commands use the current user's `~/.local/state/support-evidence/evidence.sqlite`. Replay, knowledge and plugins do not open that store. `check` reports only the records from its current manifest/run; `report` and `diagnose` use retained store records. `report --at TIMESTAMP` evaluates those records at the supplied Unix time. Store sensitive evidence on a Linux filesystem with effective private permissions.

## Module prerequisites

| Family | Before checking | Interpret separately |
|---|---|---|
| PostgreSQL | Install databases extra; provide referenced monitoring credentials, allowed address/CA and required fixture/statistics permissions | Connection, representative read, role, aggregate thresholds and replication are separate predicates |
| Nginx | Declare actual host/path/scheme/oracle; approve optional status endpoint and active-client threshold | Route behavior, upstream behavior, config intent and status coverage |
| Docker | Approve one local Linux Engine socket; use full immutable container IDs and explicit lifecycle/resource contracts | Running, configured health, resource headroom and application correctness |
| Python venv | Approve the environment root, layout's resolved base/interpreter paths and deployment identity; set route equal to target | Static metadata versus interpreter execution, native imports and running-process identity |

Details and version limits are in [service modules](service-modules.md) and [Docker/venv modules](docker-venv-modules.md). Missing health checks/statistics, unmeasured system packages and unknown target markers remain UNKNOWN. The venv collector never executes target code. Docker access denial is a collection gap, while a compatible API positively reporting an exact container ID missing is an existence failure.

## Monitoring imports and credentials

Monitoring integration consumes exported query results:

```bash
support-evidence --store ./evidence.sqlite import-monitoring my-manifest.json probe:orders prometheus-response.json --format prometheus --threshold 0
support-evidence --store ./evidence.sqlite import-monitoring my-manifest.json probe:orders plugin-status.json --format monitoring-plugin
support-evidence --store ./evidence.sqlite import-monitoring my-manifest.json probe:orders otlp-export.json --format otlp-json --metric probe_failure --threshold 0
```

Mappings must represent the named predicate. Prometheus/OTLP imports accept one finite sample; missing or ambiguous series become UNKNOWN. Monitoring Plugin code 3 remains UNKNOWN. Thresholds are reviewed contracts, never technology-wide defaults. Import success returns 0 for successful ingestion even when the imported observation is UNKNOWN; inspect its state, then run `report`. These adapters do not authenticate to upstream backends or run an OTLP receiver.

Database credentials are JSON objects in referenced `SUPPORT_*` environment variables: username, password, database and optional auth_source/ca_file as applicable. Supply them through the approved secret launcher. The worker receives one named secret plus minimal runtime environment. No credential dump or raw connection string is retained. Fixture tables/data and monitoring grants must already exist. Driver-pool evidence comes from the actual application driver, not a probe's separate pool or server connection count.

## Guidance, exits and retention

[Knowledge and replay](knowledge.md) explains the four searchable families, `--rag` JSON wrapper, embedded cards and source audits. Core-only JSON is an incident object; enriched JSON has report and knowledge keys. Use `knowledge search` without creating or changing an incident.

For check/report/diagnose, exit 1 indicates at least one strong/moderate supported boundary; exit 3 indicates no fresh applicable evidence, inconclusive findings, stale/unknown/skew/unsupported observations, or input/policy/storage failure; exit 0 indicates no supported failure with fresh applicable evidence. A supported finding takes precedence over other uncertainty for exit selection; inspect the whole report. None of these establish unmeasured business correctness. Replay/export success returns 0 regardless of retained incident status. Knowledge search returns 0 even with no hits; source refresh returns 3 for a partial audit.

`export` refuses overwrite. `prune --before RECEIPT_TIMESTAMP` explicitly removes retained observations; export important evidence first. `health` reports integrity, quotas and progress age. [Recovery](recovery.md) covers corruption and collection loss. No repair command or remediation executor is installed.

## Installation and offline preparation

From a checkout as cello:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev,databases]'
.venv/bin/python -m build --wheel
.venv/bin/pip download --only-binary=:all: --dest dist/wheelhouse ./dist/support_evidence-0.3.0-py3-none-any.whl
.venv/bin/python harness/offline_install.py
```

Preparation can fetch dependencies. The resulting core wheelhouse supports offline installation on the platform it was built/downloaded for:

```bash
pip install --no-index --find-links dist/wheelhouse support-evidence==0.3.0
pip uninstall support-evidence
```

The offline harness verifies installation, an installed venv probe, searches for all four families, old/enriched incident replay and removal in a disposable environment. Database drivers require separately prepared extra wheels for offline database collection. Build output and wheelhouse are ignored by Git and are not present in a fresh clone. The recorded reference is Linux/Python 3.12; prepare platform-specific dependency wheels for other environments.

`pyproject.toml` defines current dependencies, including packaging for venv requirement parsing. `requirements-runtime.lock` is the initial runtime snapshot and omits that later dependency; it is not a complete 0.3.0 installation manifest. `requirements-dev.lock` also records a reference snapshot. Use the current project/wheel dependency metadata for installation. Uninstalling the package preserves independently owned stores and bundles.
