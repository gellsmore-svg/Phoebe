# Supporting the support platform

`health` shows store schema/integrity, retained payload count/bytes, configured quotas and time since successful ingestion. There is one synchronous check at a time, no hidden durable queue and no implied progress merely from process existence. A hung worker, output flood, crash or invalid result becomes UNKNOWN collection with a reason; the engine continues to later workers and deterministic reporting remains available.

If ingestion fails validation or quota checks, the transaction preserves earlier records. Export important incidents before explicitly pruning observations. Never automatically prune the only evidence behind a report. A newer store schema, corrupt hash or SQLite error fails closed and returns exit 3. The CLI reports no target-health conclusion when its own storage fails.

For corruption: stop scheduled capture, preserve the original database for inspection, create a new store, replay verified incident bundles and explicitly ingest their retained records if operationally needed. Replay checks canonical hash and exact derived report equality before trusting a bundle. No automatic stale last-valid graph cache is claimed.

For collector loss: report its denied/unavailable/timeout result and freshness; do not call the target failed or healthy from lack of collection. Inspect supervisor/deadline reasons and independent probes. Timestamp skew prevents fresh evidentiary support. At quota, ingestion fails visibly; there is no fabricated zero-drop success claim after a failed batch.

For total agent/host disappearance, an independent basic external watchdog should check the agreed user route and scheduled capture progress. The local tool cannot diagnose power loss from inside the vanished host. The separate probe-namespace harness validates vantage semantics, while a deployed independent watchdog remains an operational installation task.

No coordinator or LLM is needed for local check/report/replay. The optional explanation stub falls back to deterministic text; no account, network call or model output is part of current health. Bad knowledge packages fail schema/action registration validation; replace them through reviewed versioned updates and replay regression fixtures.
