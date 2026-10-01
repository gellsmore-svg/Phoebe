# Operator guide

Start with a reviewed user-operation contract. Expected status/content must come from an authoritative requirement. An always-green readiness endpoint says nothing about a separate business operation. The sample boolean oracle is a fixture example, not a universal application test.

1. Review `discover` inventory and `coverage`; resolve ambiguous identities explicitly. Discovery authorises no automatic probes.
2. Put exact routes/targets, approved resolved addresses and the real execution vantage in a manifest. Do not describe a host-local probe as public or external.
3. Run `check manifest.json --export incident.json`. Collection failure, permission denial and stale measurements require investigation, not a restart.
4. Read each boundary, evidence IDs, contradictory results, method and time. Multiple boundaries can be real; a passed ping does not overrule a blocked read.
5. Perform the registered next check within a separately reviewed manifest. Uninstrumented pool checkout remains unknown even when server connection count is high.
6. Hand the retained bundle to escalation. `replay` works without the application, its source or its telemetry backend.

Monitoring integration uses exported query results, not a new metrics warehouse:

```bash
support-evidence import-monitoring manifest.json probe:orders prometheus-response.json --format prometheus --threshold 0
support-evidence import-monitoring manifest.json probe:orders plugin-status.json --format monitoring-plugin
support-evidence import-monitoring manifest.json probe:orders otlp-export.json --format otlp-json --metric probe_failure --threshold 0
```

Mappings must represent the predicate in the named contract. Prometheus/OTLP imports accept exactly one finite sample; absent or ambiguous series become UNKNOWN. Monitoring Plugins preserve UNKNOWN code 3. Thresholds are supplied and reviewed, never technology-wide defaults. These adapters do not authenticate to upstream backends or implement an OTLP receiver.

Database credentials are JSON objects held only in referenced environment variables named `SUPPORT_*` (username, password, database, optional auth_source/ca_file). Supply these through your approved secret launcher. No entire environment or raw connection string is persisted. Fixture databases must already exist and monitoring accounts need only the supported read. Never paste credentials into manifests, commands recorded in shell history, reports or issue trackers. Driver-pool evidence must come from the actual application driver, not this probe's separate pool.

`report --at TIMESTAMP` uses retained evidence at an explicit time. `export` writes a new self-contained file and refuses overwrite. `prune --before RECEIPT_TIMESTAMP` explicitly removes retained observations; export escalation bundles first. `health` reports quota, integrity and progress age; process heartbeats alone do not prove new evidence.

The CLI has no repair command. All restart, configuration, credential and deployment changes require the operational approval process. Diagnostic labels never authorise actions.
