# Verification and build versus integrate
Retrieval date: 2026-10-01. User-provided baseline retained verbatim under baseline/. This is an implementation-focused verification, not a product benchmark. No upstream code is copied.

| Primary source | Documented capability / implementation decision | Version, licence, limits |
|---|---|---|
| https://docs.coroot.com/installation/architecture/ | eBPF node telemetry, database cluster agent, Prometheus and ClickHouse backends; integrate where installed | rolling docs; Community code Apache-2.0 (upstream LICENSE); Enterprise commercial |
| https://docs.coroot.com/ai/overview/ | dependency/ML analysis precedes LLM explanations | rolling; AI Enterprise or Cloud integration for Community; local offline feature parity unverified |
| https://opentelemetry.io/docs/concepts/components/ | Collector and SDK interoperability | rolling; Apache-2.0 code; no Collector required locally |
| https://opentelemetry.io/docs/concepts/semantic-conventions/ | use explicit resource attributes and schema URL | rolling; maturity varies; do not assert universal stability |
| https://opentelemetry.io/docs/specs/otel/entities/data-model/ | entity model marked Development; relationships evolving | no dependence on universal backend support |
| https://docs.checkmk.com/latest/en/devel_check_plugins.html | separate parsing/discovery/checking, Check API V2 | docs identify 2.5.0; edition/licence varies; no server installed |
| https://github.com/prometheus/blackbox_exporter | reusable protocol probes | master; Apache-2.0 LICENSE checked; runtime pinned by harness |
| https://backstage.io/docs/features/software-catalog/system-model/ | catalogue components/APIs/resources | rolling; Apache-2.0 code; intent/ownership, not live health |
| https://docs.oasis-open.org/tosca/TOSCA/v2.0/TOSCA-v2.0.html | typed topology specification | 2.0; standards document terms; retrieval availability recorded below |
| https://www.w3.org/TR/prov-o/ | entity/activity/agent provenance | Recommendation 2013; W3C document terms; plain JSON implementation |
| https://www.microsoft.com/en-us/research/publication/automatic-root-cause-analysis-via-large-language-models-for-cloud-incidents/ | RCACopilot incident-specific evidence handling | author publication; no operational efficacy reproduced |
| https://github.com/elastisys/MicroRCA | response-time/resource graph baseline | master, research code; no root LICENSE visible, no reuse authorised |
| https://github.com/phamquiluan/RCAEval | multi-source datasets and baselines | main; MIT code, dataset licences separate; no dataset performance claim |
| https://github.com/microsoft/AIOpsLab | deployment/workload/injection/evaluation framework | main; MIT; full orchestration omitted |
| https://arxiv.org/abs/2408.00803 | RCA survey | paper identifier; literature lead, no reproduced algorithm |
| https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/connection-options/connection-pools/ | driver checkout wait differs from server connections | current 4.x docs; executor version in lock file; no universal pool limit |
| https://www.postgresql.org/docs/current/app-pg-isready.html | readiness tests connection acceptance | current docs resolve 18; representative authenticated query remains separate |
| https://www.postgresql.org/docs/current/runtime-config-client.html | statement/lock deadlines | 18; executor restricts queries to fixture read |
| https://nginx.org/en/docs/http/ngx_http_proxy_module.html | proxy upstream and UNIX socket semantics | rolling; metadata parser supports a safe subset |

Commercial names checked against primary pages: [Datadog Bits Investigation](https://docs.datadoghq.com/bits_ai/bits_investigation/) and [Bits Remediation](https://docs.datadoghq.com/bits_ai/bits_remediation/); [Dynatrace Intelligence](https://docs.dynatrace.com/docs/dynatrace-intelligence/root-cause-analysis/concepts); [New Relic Autopilot](https://docs.newrelic.com/docs/agentic-ai/autopilot/overview/); [Splunk ITSI](https://www.splunk.com/en_us/products/it-service-intelligence.html); [Elastic AI Assistant](https://www.elastic.co/docs/solutions/observability/ai/observability-ai-assistant); [Instana RCA](https://www.ibm.com/docs/en/instana-observability?topic=capabilities-root-cause-analysis); [BigPanda RCC](https://docs.bigpanda.io/en/root-cause-changes--rcc-); [PagerDuty AIOps](https://docs.pagerduty.com/ai-automation/aiops). Commercial terms, connector/role/region limits and performance require account-specific verification. No commercial installation was benchmarked.

Web retrieval of Datadog returned unsupported Markdown; IBM and systemd pages failed. Alternate direct upstream retrieval is tracked in source-ledger.json. No inaccessible content is represented as reproduced behaviour. Public documentation establishes capabilities, not their effectiveness for this workload.

Decision (engineering inference): ship a bounded interchange/store/diagnostic renderer with existing monitoring adapters. Direct DNS/TCP/TLS/HTTP and fixture DB checks fill missing operation/vantage information when no backend exists. Retain metadata and predicates, not a new telemetry warehouse. A controlled Blackbox Exporter comparison tests incremental scoping and retention; Coroot and unfamiliar-operator comparisons remain explicit acceptance items. Reopen this decision if operator benefit is not demonstrated.
