# Security and privilege matrix

| Capability | Privileges and limit |
|---|---|
| Core/store/replay | ordinary user; no remediation, network on replay or remote code |
| Linux inventory | readable `/proc`, systemd inventory; denials reduce coverage; no command-line/environment scrape |
| systemd state | named allowlisted units, system or user manager; no start/stop executor |
| DNS/TCP/TLS/HTTP | exact destination and approved address set; pin connection IP, verify TLS hostname, reject redirects, credentials in URL and query strings; no bodies retained |
| UNIX/filesystem | exact canonical path allowlist; no writes by probes |
| Mongo fixture | authenticated read on support_probe, directConnection/no discovery to other hosts, deadline and projection; no server administration |
| PostgreSQL fixture/diagnostics | Referenced monitoring credentials; fixed read-only SQL and deadlines; diagnostic visibility requires appropriate statistics grants, otherwise UNKNOWN |
| Nginx route/status | Approved hostname/address/path and explicit oracle/threshold; optional status endpoint; no reload/config execution or bodies retained |
| Docker collectors | Existing approved local Linux Engine Unix socket; fixed version/inspect/nonstreaming-stats GETs, full container IDs and local scope revalidation; no exec/logs/writes/context discovery |
| Python venv collectors | Read access to approved root and layout base/interpreter paths; bounded nofollow metadata reads; no target Python/pip/import/activation/.pth execution |
| Knowledge search/replay | Reviewed-card search or retained evidence/context replay; no network, model or fresh runtime measurement |
| Knowledge source audit | Fixed official HTTPS URL inventory, public pinned DNS/TLS, no redirects, supervised limits; hashes/receipts only, no raw documents retained |
| Monitoring import | local bounded exports, scalar sample/status only; no raw log interpretation |
| Docker harnesses | cello creates and mutates only uniquely named/labelled owned fixtures, with resource caps and cleanup; existing containers are preserved |
| systemd harness | unique transient user unit; never modifies existing services |

Destination validation rejects URL userinfo/query/fragment/control characters, nonregistered schemes, special/link-local/metadata/multicast addresses and any DNS answer outside the explicit approved set. Connections use the approved literal IP to resist DNS rebinding. UNIX/path resolution is exact, though local path replacement races and a compromised trusted host remain outside strong sandbox guarantees. The core does not expose an HTTP service to untrusted callers. Docker socket permissions carry Engine authority beyond this tool; Phoebe constrains its own requests to fixed GETs rather than changing the daemon permission model. Ambient DOCKER_HOST/context settings cannot select a target. Container identity, target/route and execution vantage are checked again inside the local worker.

TLS certificate chain and hostname verification are never disabled for HTTPS/TLS. Mongo TLS fixtures require certificates for the approved literal IP; SRV, replicas and broad managed-service discovery are not supported. PostgreSQL uses verify-full when a reviewed CA file is supplied; plain DB mode is intended only for explicitly reviewed local/disposable environments. Remote encrypted database deployments require configured CA and appropriate certificates.

Secret references resolve only in the executor; one referenced variable is passed alongside minimal runtime environment. No raw exceptions, response bodies, database values, credentials, private keys or arbitrary logs are persisted. Redaction uses safe metadata allowlists plus rejection patterns; it is not a detector for every possible PII string. Review identity/source fields and export scopes. Imported evidence and documentation remain data; no text executes or controls confidence. Docker inspect bodies and health output are discarded; venv retains numeric/static aggregates rather than metadata contents. Documentation guidance travels in a separate hashed attachment and cannot create a finding. There is no live LLM transfer.

Store/bundle creation requests mode 0600 and private directories. Windows DrvFS can report broad permissions despite chmod, so sensitive deployment storage belongs on a Linux filesystem under the operator's home. No silent chown is used: all workspace writes run as cello. Quotas limit inputs, evidence, response bytes, workers and total nominal work. A systemd user-unit example provides further process limits but requires deployment validation.

Remote mTLS/RBAC/tenant separation, encrypted stores and hostile plugin sandboxing remain future work, not claimed capabilities. Diagnostic confidence never grants permission for a repair.

See [module prerequisites](operator-guide.md), [Docker/venv limits](docker-venv-modules.md) and [knowledge audits](knowledge.md) for current supported boundaries. Remote/rootless Docker deployment integration, Windows venv and native import/ABI validation remain outside the recorded reference coverage.
