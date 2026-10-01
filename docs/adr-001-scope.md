# ADR 001: bounded evidence adapter and report layer
Status: accepted, 2026-10-01.
Current Coroot documentation confirms graph/ML diagnosis followed by LLM explanation. Checkmk separates discovery, parsing and checks. Neither invention nor a telemetry backend is required here.
Choose Python for inspectable adapters and DB libraries; SQLite for local immutable records and migrations. A JSON Schema contract remains technology independent. Reuse Prometheus query results, Monitoring Plugin status and OTel resources; direct probes fill the offline/operation-specific gap.
Core has no graph server, Collector, LLM or source index. Sequential supervised workers deliberately cap concurrency at one. This keeps the MVP auditable; throughput is bounded by the manifest work budget. No remote publishing.
Supported execution environment: Linux, Python 3.11+, local network namespace; tested environment recorded in test-report.md. Windows use through WSL. DB extras are optional.
