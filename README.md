# Phoebe

**Phoebe tells you which service boundary is measurably failing, and is
explicit about what it has not measured.** You declare a set of read-only
checks (Postgres, Nginx, Docker, Python venvs, network, host, systemd), and
it collects the evidence and reports each failing boundary with its scope,
support, contradictions and unknowns. It then exports the incident as a
bundle that replays offline anywhere.

It never claims more than it measured. A failing boundary is *where*
something is broken; the initiating cause stays unverified until other
evidence establishes it. The core needs no telemetry backend, graph database,
vector service or LLM account.

## Is it for you?

**Good fit:** you operate Linux services and want a diagnosis you can hand to
someone else, or replay later, that separates what was measured from what
was assumed.

**Not a fit:** continuous monitoring or automatic remediation. Phoebe runs
on demand, its checks are read-only, and every remediation needs human
approval because there is no executor.

## Try it

Phoebe is installed from a clone; the PyPI name `phoebe` belongs to an
unrelated project. The package and command are `support-evidence`. You need
Python 3.11+.

```bash
git clone https://github.com/gellsmore-svg/Phoebe && cd Phoebe
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/support-evidence replay examples/incident-docker-module.json
```

The retained incident replays with no Docker, credentials or network:

```
Evidence supports measured boundaries; initiating cause remains unverified.
Boundary: docker declared static/API contract [strong]
  Engine reported an unhealthy configured check; application correctness and
  downstream causes require independent evidence.
  Contradictions: none measured
  Unknown: initiating cause unverified; unmeasured operations and vantages remain unknown
  Next [collect_docker_state]: Repeat docker_container for the declared full container ID; ...
Coverage: 1 fresh applicable of 1 observations; all unmeasured paths unknown.
Approval required: all remediation; executor absent.
```

## Diagnose your own system

1. **Declare the checks.** Copy a manifest
   ([base](examples/manifest.json),
   [Postgres/Nginx](examples/manifest-service-modules.json) or
   [Docker/venv](examples/manifest-docker-venv-modules.json)) to
   `my-manifest.json` and set its targets, addresses, paths, thresholds,
   identities and execution vantage. Database monitoring accounts and fixture
   tables must already exist; Phoebe creates neither.
2. **Collect and export:**

   ```bash
   .venv/bin/support-evidence --store ./evidence.sqlite check ./my-manifest.json --rag --export ./incident.json
   ```

   `--rag` adds guidance retrieved offline from 45 reviewed cards drawn from
   34 official sources. Guidance suggests alternatives and next checks; it is
   never treated as runtime evidence. Database collectors need
   `pip install -e '.[databases]'`.
3. **Read the exit code, then the coverage.** `0` means no supported failure
   with fresh applicable evidence, `1` means at least one strong or moderate
   failing boundary, and `3` means inconclusive or an input, policy or
   storage failure. Check coverage and unknowns before reading `0` as
   "healthy".

## What it checks

| Family | Measured contracts | Guide |
|---|---|---|
| PostgreSQL | Connection, fixture read, role, activity, blocking, connection headroom, replication backlog, frozen-XID age | [service modules](docs/service-modules.md) |
| Nginx | Declared HTTP route and oracle; optional stub_status client threshold | [service modules](docs/service-modules.md) |
| Docker | Approved local Engine socket, exact-ID container state, configured health, memory/PID headroom | [Docker/venv modules](docs/docker-venv-modules.md) |
| Python venv | Layout and version intent, isolation, script paths, recursive dependency metadata | [Docker/venv modules](docs/docker-venv-modules.md) |
| Network, host, services | DNS/TCP/UNIX/TLS/HTTP, capacity and inodes, load and memory, systemd unit state | [coverage](docs/coverage.md) |
| MongoDB, monitoring imports | Authenticated ping and fixture read; Prometheus, Monitoring Plugins and OTLP JSON snapshots | [operator guide](docs/operator-guide.md) |

## Know before you rely on it

- **Checks are read-only and narrow by design.** Docker checks issue fixed
  GETs and never run container commands. Venv checks never execute the target
  Python, pip, imports or activation.
- **A static PASS is not runtime compatibility.** A venv's metadata can pass
  while imports or the ABI still fail at runtime.
- **Missing, denied, stale and unsupported evidence stay explicit**, never
  silently treated as healthy. See [coverage limits](docs/coverage.md).
- **Treat stores and incident bundles as sensitive.** Keep them on a Linux
  filesystem with private permissions; Windows DrvFS (under `/mnt/c`) can
  report broader modes than you set. See [security](docs/security.md).
- **A replay that succeeds returns `0`** even when the incident it replays
  contains failures.

## Validation and development

The recorded 0.3.0 validation passed 217 automated tests, 25 real disposable
Docker and venv cases, 34 of 34 source fetches, and an offline
install-search-replay-removal cycle. Per-version records are not summed. See
the [test report](docs/test-report.md) and
[pending acceptance gates](docs/acceptance.md).

```bash
.venv/bin/pip install -e '.[dev,databases]'
.venv/bin/python -m pytest -q
.venv/bin/python harness/docker_venv_modules.py     # real fault injection into owned, disposable fixtures
```

Offline installs from a prepared wheelhouse (Linux, Python 3.12) and build
steps are in the [operator guide](docs/operator-guide.md).
`pip uninstall support-evidence` leaves stores and incident bundles in place.

[Documentation index](docs/README.md) · [CHANGELOG](CHANGELOG.md) ·
[contribution rules](AGENTS.md) · original briefs in [docs/baseline](docs/baseline)
