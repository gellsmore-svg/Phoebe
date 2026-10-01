# Contribution rules
Run commands and write files as cello. Never use production services for injection.
Python >=3.11; install `python3 -m venv .venv`, `.venv/bin/pip install -e '.[dev,databases]'`.
Validate with `.venv/bin/python -m pytest -q`. Disposable integration: `.venv/bin/python harness/run.py`.
Do not collapse collection errors, UNKNOWN, stale observations or missing evidence to PASS.
Scope evidence by subject, operation, predicate, route, vantage, instance and interval.
Keep intended/discovered/observed assertions and provenance; graph contact is not causality.
No arbitrary shell, eval, remote code, remediation or LLM-authoritative facts.
Rules are JSON data and must include provenance and fixtures. New operations require registered bounded executors.
Never persist credentials, raw response bodies, database values, environment dumps or query text.
Keep claim -> evidence -> graph revision -> method -> versioned rule inspectable.
Do not claim systemd integration from Compose or describe simulations as real injected faults.
Run meaningful tests before committing. Preserve research and disclose pending acceptance gates.
