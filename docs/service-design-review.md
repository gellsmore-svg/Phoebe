# Recursive design review

Completion status: STABLE_WITH_UNCERTAINTY. Two generations, three isolated paths per generation, six path invocations. Context independence was full; error-correlation risk remains high because all paths used the same model and source. No closing blind audit ran and no STABLE_HIGH_CONFIDENCE claim is made. DEGENERATE_POPULATION remains a warning: paths shared a broad architecture, so agreement is not external verification.

Both generations used the unchanged pre-implementation tree at 5d9dcf9013148e9b9424e582aeca8e0987b928f8. The second generation used blind, dissent and source-heavy projections. Source, raw path artifacts, tree fingerprints and structurally validated bounded states were retained outside the repository in the local multipath run directory. Structural validation checks the review contract; it does not prove the engineering conclusions.

The review conserved the evidence constraints: diagnostic permission denial stays UNKNOWN; documentation is separate from runtime observations; SQL and operations remain fixed and bounded; Host/SNI/vantage/instance/interval matter; and existing reports must replay exactly. Dissent identified two concrete engine risks: UNKNOWN was filtered before recency selection, and new reason-specific findings could inherit unrelated same-scope failures. Phoebe 0.2.0 corrects both while preserving the supported 0.1.0 evaluator.

The chosen RAG design uses original official-source summaries, deterministic lexical retrieval and grounded template generation in a separate attachment. Both a generative consumer and a versioned enriched incident remain admissible future designs. A supervised source refresh audit was selected over silently rewriting reviewed summaries. Deployment privileges, supported build combinations, replica topology, thresholds and production behavior still require external facts.

The recursive diagnostic sequence is practical rather than an assertion of service-wide certainty:

1. Locate the measured boundary: connection, fixture/route contract or explicit aggregate threshold.
2. Retrieve source-backed mechanisms and retain alternatives producing the same symptom.
3. Choose the smallest registered check that distinguishes those alternatives within the declared policy.
4. Compare fresh observations only for compatible subjects, contracts, routes, instances and vantages.
5. Stop or abstain when visibility, capabilities, freshness, contradictory evidence or the execution budget prevents discrimination.

For PostgreSQL, a connection PASS followed by a read FAIL branches into fixture authorization/schema, locking, cancellation, resource and functional-contract questions. Monitoring denial stops aggregate interpretation instead of producing zero healthy counts. A replica timestamp or absent sender row requires role/topology evidence before interpretation.

For Nginx, a route FAIL branches into host/URI/oracle, proxy-side DNS/TLS/transport, upstream behavior, inactivity policy, resource limits and configuration lifecycle. Status counters and a successful external upstream check cannot eliminate those branches by themselves. Reading changed configuration does not prove it is active.

Empirical verification then exercised 22 service-module scenarios, the existing broader disposable harness, metadata/citation/chronology regressions, real pre-change bundles, and packaged offline replay. [Module coverage](service-modules.md) and [results](service-module-results.json) distinguish actual injections, real-counter threshold edges and unit doubles. These checks improve confidence in the implemented contracts; they do not remove the unresolved deployment uncertainty.
