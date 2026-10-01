# Plugin author guide

Capabilities are discovery, telemetry import, one bounded probe and declarative knowledge. Only bundled trusted Python workers run. There is no marketplace, remote package loading or action provider.

The invocation is JSON stdin `{probe, policy, deadline_at}` and one JSON observation on stdout. The worker reads at most 64 KiB and must return the original subject/instance/operation/predicate/route/vantage. Stdout and stderr together are capped at 64 KiB; non-reading stdin, crashes, invalid JSON, output flood and hangs terminate the invocation. All descendants in the original process group are killed. Child processes escaping the process group are outside this trusted-plugin isolation model; this is not a hostile-code sandbox.

Register operations in policy.OPERATIONS, implement the one read-only bounded operation in worker.py, and add original versioned JSON rules with source URLs and declared positive/negative/unknown fixtures. Add meaningful scope, denial, failure, timeout and negative-control tests. No shell templates, eval, executable YAML, automatic code download or unbounded regex is accepted.

The common contracts remain technology neutral. Required privileges, platform support and output/target cardinality belong in a package descriptor. The bundled descriptor is [plugins-v1.json](../schemas/plugins-v1.json). Unknown versions must reduce applicability rather than imply full coverage. Registered diagnostic action IDs are recommendation text; the CLI does not automatically execute them.

Existing exporter query snapshots should map exact operation/predicate/source/dependence group; preserve original event time and actual collection vantage. Imported success can establish only its named contract. The application-driver pool is distinct from server connection metrics and from the independent probe's pool.
