# Documentation index

Current package version: **0.3.0**. Start with the [repository overview](../README.md), [operator guide](operator-guide.md) and [coverage limits](coverage.md). Validation claims are tied to recorded versions and fixtures; pending production and operator-study gates remain pending.

| Topic | Documentation |
|---|---|
| Collection, monitoring imports, credentials, storage and installation | [Operator guide](operator-guide.md) |
| PostgreSQL/Nginx operations, permissions and limitations | [Service modules](service-modules.md) |
| Docker/Python venv operations, paths, identities and static evidence | [Docker/venv modules](docker-venv-modules.md) |
| Offline RAG, source audits, JSON shapes and incident replay | [Knowledge and replay](knowledge.md) |
| Evidence flow and optional guidance separation | [Architecture](architecture.md) |
| Records, store, bundles and version compatibility | [Schema reference](schema-reference.md) |
| Privileges, secret handling and execution boundaries | [Security](security.md) |
| Resource and input limits | [Budgets](budgets.md) |
| Failure and corruption handling | [Recovery](recovery.md) |
| Trusted adapters, rules and documentation cards | [Plugin guide](plugin-guide.md), [contribution rules](../AGENTS.md) |
| Measured verification and unresolved acceptance | [Test report](test-report.md), [acceptance](acceptance.md), [operator study](operator-study.md) |
| Future extensions | [Roadmap](roadmap.md) |
| Research provenance and design decisions | [Research](research.md), [review log](review-log.md), [scope ADR](adr-001-scope.md), [storage ADR](adr-002-storage.md) |
| Failure-mode reasoning | [PostgreSQL/Nginx review](service-design-review.md), [Docker/venv review](docker-venv-design-review.md) |
| Implemented version history | [Changelog](../CHANGELOG.md) |

## Examples and recorded results

[Manifest examples](../examples) require deployment-specific targets and contracts before collection. Retained incident examples replay offline, including [PostgreSQL](../examples/incident-postgresql-module.json), [Nginx](../examples/incident-nginx-module.json), [Docker](../examples/incident-docker-module.json) and [venv](../examples/incident-venv-module.json) with embedded guidance.

| Version/run | Recorded results |
|---|---|
| Initial implementation | [Stack integration](integration-results.json), [systemd user manager](systemd-results.json), [performance](performance-results.json), [localization metrics](localization-metrics.json) |
| PostgreSQL/Nginx 0.2.0 | [Validation summary](service-validation-results.json), [actual service scenarios](service-module-results.json) |
| Docker/venv 0.3.0 | [Validation, source receipts and offline installation](docker-venv-validation-results.json) |

The original research and implementation prompts remain verbatim in [baseline](baseline). Historical reviews and measurements retain their original dates and scope.
