# Pre-measurement budgets
Declared before performance runs: 1,000-record offline diagnosis <2 s wall time, peak RSS <128 MiB, JSON bundle <8 MiB; bounded incident maximum 5,000 records, 64 KiB per scalar record (aggregate incident <=8 MiB), store 64 MiB logical payload and 10,000 records. Worker stdout+stderr <=64 KiB; deadline <=10 s plus 0.25 s termination allowance, one worker at a time, <=32 checks and <=60 s total nominal work per run. HTTP response <=64 KiB; manifest/import <=8 MiB. Discovery <=512 processes and 512 listeners.
Performance results apply only to the recorded hardware and workload. No continuous-host overhead claim follows from CLI measurement.

## Module and guidance limits in 0.3.0

| Path | Additional bound |
|---|---|
| PostgreSQL blocking | At most 512 lock-scan candidates; explicit statement/lock thresholds fit outer worker deadline |
| Nginx route/status | Existing 64 KiB HTTP body cap; strict status parser and explicit threshold |
| Docker | Version body 32 KiB, inspect body 1 MiB, nonstreaming stats body 256 KiB; one full container ID, stable start/restart/limit cohort |
| Venv metadata | cfg 16 KiB; METADATA 256 KiB/file; total metadata reads including rechecks 4 MiB; 4096 site entries; 512 distributions; 256 requirements/distribution; 2048 dependency visits |
| Venv scripts | At most 256 bin entries; 4096 prefix bytes/file |
| Knowledge | At most 128 reviewed cards, 16 KiB/card; query 2048 characters; default 3 hits (API maximum 5); at most 128 incident contexts with explicit truncation |
| Source audit | 5 seconds/request, 60 seconds overall, 1 MiB document body, 4096-byte worker result; unavailable/budget-exhausted receipts remain explicit |

These caps bound work; they do not imply the recorded baseline performance benchmark covered RAG or every new collector. [Module limits](docker-venv-modules.md) and [knowledge limits](knowledge.md) document UNKNOWN behavior when prerequisites or budgets prevent measurement.
