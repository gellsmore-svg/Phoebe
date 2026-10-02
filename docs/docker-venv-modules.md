# Docker and Python venv modules (0.3.0)

Eight registered read-only operations use existing process deadlines, scope, freshness, redaction, diagnosis and replay. Run all commands as `cello`. The manifest example requires real paths, a full container ID and deployment identity before use.

| Operation | Explicit contract | Measurement |
|---|---|---|
| `docker_daemon` | Empty expected object | Linux Engine version response and compatible API envelope |
| `docker_container` | `container_state` (running/exited/paused), `max_restarts` | Exact-ID lifecycle state, automatic restart count, exit code and recorded OOM flag |
| `docker_health` | Empty expected object; running is prerequisite | Existing Engine health status and numeric failing streak |
| `docker_resources` | At least one of `min_memory_headroom_bytes`, `min_pids_headroom` | Configured limit minus current usage; stable running/start/restart/limit cohort |
| `venv_layout` | `python_version`, e.g. 3.12 or 3.12.3 | cfg version, approved base directory and regular/executable interpreter entry |
| `venv_isolation` | `isolated` boolean | cfg include-system-site-packages setting only |
| `venv_scripts` | Empty expected object | Static Python shebang paths within the declared environment |
| `venv_dependencies` | Nonempty list `requirements`, e.g. app[crypto]>=2 | Local dist-info versions, Requires-Python and recursive active Requires-Dist/extra closure |

Targets are absolute local paths, explicitly listed in allowed_targets and resolved allowed_paths. Set route equal to target so separate sockets/environments cannot supply support or contradiction for each other. Docker container operations require a full immutable 64-character lowercase hexadecimal instance_id, never a reusable name or short ID. Use a venv deployment identity for instance_id. Layout also needs explicit approval for the resolved cfg home directory and interpreter symlink destination.

```bash
support-evidence check examples/manifest-docker-venv-modules.json --rag --json
support-evidence knowledge search docker docker_unhealthy --json
support-evidence knowledge search venv venv_dependencies_missing --json
support-evidence replay examples/incident-docker-module.json --json
support-evidence replay examples/incident-venv-module.json --json
```

Docker uses fixed GET requests over one approved Unix socket. It selects the intersection of the daemon API range with 1.24–1.47; the integration daemon reported 1.55 and accepted 1.47. This is a tested compatibility envelope, not a claim that every historical daemon was tested. DOCKER_HOST, contexts and ambient CLI settings cannot choose a destination. No Docker CLI, exec, health command, logs, writes, redirects, remote transport or namespace entry runs in the collector. Inspect bodies can contain sensitive data; bodies, environment, health output, commands and labels are discarded, and only closed aggregate fields survive.

Absent or refused daemon sockets fail the declared daemon connection boundary. Exact-ID 404 from a compatible inspect endpoint fails container existence. API denial, malformed/oversized response, deadline, unsupported version/platform, identity mismatch and changing resource lifetime yield UNKNOWN. No configured health check and starting health yield UNKNOWN. Unlimited/absent memory/PID limits and missing counters yield UNKNOWN. A successful version request is only daemon API evidence; running is only lifecycle evidence; healthy is only the configured health contract. Memory usage includes cache. Exit 137 does not independently prove OOM. The restart counter measures automatic Engine restarts and is neither a manual-restart count nor a rate.

Venv checks never run target Python, pip, activation, entrypoints, imports or .pth hooks. Directory-relative reads reject metadata symlinks and nonregular files, including FIFOs. Configuration is capped at 16 KiB, METADATA at 256 KiB, total reads at 4 MiB, site entries at 4096, distributions at 512, requirements per distribution at 256 and recursive dependency visits at 2048. Metadata is reread and directory/cfg changes checked. There is no filesystem-wide atomic snapshot guarantee. Script inspection is capped at 256 bin entries and 4096 prefix bytes per file.

Python version and extra markers use target cfg metadata. Platform/implementation markers, direct URL metadata, unsupported extras, negative extra comparisons, legacy egg paths, .pth hooks and external system packages remain UNKNOWN; collector runtime facts are never substituted. Missing dependencies and version conflicts remain positive static failure evidence even when other dependency edges are unknown; metadata_complete records that visibility separately. POSIX Python 3.11–3.14 metadata is supported. Copied interpreters receive only a regular/executable-file check: cfg version is not an executable version proof. Windows layout, native imports/ABI, RECORD payload hashes, hidden import paths and actual running-service interpreter identity are unmeasured.

RAG adds 19 original source cards from official Docker, Python and PyPA documentation, bringing the corpus to 45 cards. BM25-2 retrieval adds Docker/venv signatures; deterministic template-1 generation retains alternative mechanisms and explicit limitations. Documentation never changes runtime status, confidence or causality. Schema-2 bundles carry the full hashed corpus, rules, evidence and generated context. Replay dispatches bm25-1 for earlier PostgreSQL/Nginx bundles and preserves both 0.1.0 and 0.2.0 reports exactly. No remote model or runtime network is required for retrieval/replay. Shared CLI JSON shapes, source audits and version dispatch are explained in [knowledge and replay](knowledge.md).

Run `python harness/docker_venv_modules.py` as cello for actual disposable integration. It mutates only UUID-named owned containers and local test venvs, caps resources, cleans containers and checks existing containers remain present. It includes healthy/unhealthy/absent health, pause/stop/missing identity, automatic versus manual restarts, resource controls/thresholds, bounded container OOM and venv relocation/config/version/dependency failures. See [validation results](docker-venv-validation-results.json). 217 automated tests passed, 25 actual fixture cases passed, and offline wheel installation/search/replay/removal passed. Official source audit fetched 34/34 fixed sources. The Dockerfile HTML exceeds the 1 MiB fetch budget, so its official Markdown representation is used without raising that budget. Unit tests additionally cover API permission/protocol/deadline, unsafe paths, privacy, dependency cycles/extras/markers, target nonexecution and legacy replay.
