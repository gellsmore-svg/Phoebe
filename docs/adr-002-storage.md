# ADR 002: embedded temporal store
Status: accepted, 2026-10-01.
SQLite stores immutable validated records, receipt order and content hashes. Graphs are time-window projections of assertions, never mutable authoritative topology. Snapshot bundles carry records, rules, time and report so replay is independent of live dashboards.
Migration 1 creates the store; newer schema versions fail closed. A retention cap rejects ingestion atomically with a visible error; pinned incident bundles are separately owned files. No bulk telemetry replication. WAL, busy timeout and secure directories; filesystem permission guarantees require a Linux filesystem (DrvFS can report broad modes).
