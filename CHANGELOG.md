# Implemented version history

These entries describe committed package versions and recorded validation, not separate GitHub release artifacts. Pending acceptance gates are listed in [acceptance](docs/acceptance.md).

## 0.3.0 — 2026-10-02

[Implementation commit](https://github.com/gellsmore-svg/Phoebe/commit/8a46af196afbfb0852ad05a2f5e92315c20dfa5a).

- Four fixed local Docker Engine operations cover daemon access, immutable container state, configured health and memory/PID headroom.
- Four static Python venv operations cover layout/version intent, isolation, absolute script paths and recursive dependencies/extras without executing target code.
- Nineteen additional official-source cards bring offline RAG to 45 cards from 34 URLs. BM25-2 adds Docker/venv signatures and retains bm25-1 replay for earlier enriched incidents.
- Recorded validation: 217 automated tests, 25 actual disposable cases, 34/34 source fetches, offline installation/probe/search/replay/removal and preserved existing containers. See [results](docs/docker-venv-validation-results.json).

## 0.2.0 — 2026-10-01

[Implementation commit](https://github.com/gellsmore-svg/Phoebe/commit/20cf0f578403a46b3b7627b3847c5eacc9f2a5d3).

- Eight PostgreSQL and two Nginx operations, classified failure signatures, explicit thresholds and diagnostic visibility checks.
- Twenty-six original documentation cards, BM25-1/template-1 guidance and self-contained schema-2 enriched bundles.
- Newer UNKNOWN evidence blocks older PASS; reason-specific findings retain matching support. Legacy 0.1.0 evaluation remains available for old incident replay.
- Recorded validation: 157 automated tests, 22 actual service-module scenarios, a 20-case broader harness and 20 source fetches. See [results](docs/service-validation-results.json).

## 0.1.0 — 2026-10-01

The initial implementation ingested the supplied briefs and added versioned evidence records, bounded read-only probes, monitoring snapshot imports, temporal topology, ordinal findings, an immutable SQLite store and offline incident replay. The [historical test report](docs/test-report.md) records 78 automated tests, the 20-case stack harness, a real user-systemd check and a bounded offline benchmark with their limitations.
