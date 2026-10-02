"""Operation-specific thresholds and schemes: an absent contract is not health."""
import re
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = {
    "docker_daemon": set(),
    "docker_container": {"container_state", "max_restarts"},
    "docker_health": set(),
    "docker_resources": {"min_memory_headroom_bytes", "min_pids_headroom"},
    "venv_layout": {"python_version"},
    "venv_isolation": {"isolated"},
    "venv_dependencies": {"requirements"},
    "venv_scripts": set(),
    "postgresql_connect": set(),
    "postgresql_read": {"min_rows", "lock_timeout_ms"},
    "postgresql_role": {"role"},
    "postgresql_activity": {"max_active_sessions", "max_idle_transactions", "max_transaction_seconds"},
    "postgresql_locks": {"max_blocked_sessions"},
    "postgresql_headroom": {"min_connection_headroom"},
    "postgresql_replication": {"role", "min_standbys", "max_replay_bytes"},
    "postgresql_vacuum": {"max_xid_age"},
    "nginx_http": {"status", "sha256", "json_key", "json_value"},
    "nginx_stub_status": {"max_active_connections"},
}
SERVICE_OPERATIONS = set(FIELDS) | {"postgresql_connect", "postgresql_read"}

def validate_service_contract(probe):
    op, expected = probe["operation"], probe["expected"]
    if op not in SERVICE_OPERATIONS:
        return
    if op.startswith(("docker_", "venv_")):
        if not Path(probe["target"]).is_absolute() or "://" in probe["target"]:
            raise ValueError("local absolute service target required")
        if probe.get("credential_ref") or probe["route"] != probe["target"]:
            raise ValueError("local module requires target-scoped route and no credentials")
        if set(expected)-FIELDS[op]: raise ValueError("unsupported service contract field")
        required = {"docker_container":{"container_state","max_restarts"},"venv_layout":{"python_version"},"venv_isolation":{"isolated"},"venv_dependencies":{"requirements"}}.get(op,set())
        if not required <= set(expected) or op=="docker_resources" and not expected:
            raise ValueError("explicit local service contract required")
        if op.startswith("docker_") and op!="docker_daemon" and not re.fullmatch(r"[a-f0-9]{64}",probe["instance_id"] or ""):
            raise ValueError("full immutable container identity required")
        if op=="docker_daemon" and probe["instance_id"] is not None:
            raise ValueError("daemon identity must be scoped by socket and subject")
        if op=="venv_dependencies":
            from packaging.requirements import Requirement
            for item in expected["requirements"]:
                if Requirement(item).url: raise ValueError("direct URL contract unsupported")
        return
    scheme = urlsplit(probe["target"]).scheme
    if scheme not in ({"postgresql"} if op.startswith("postgresql") else {"http", "https"}):
        raise ValueError("service operation scheme mismatch")
    if op.startswith("postgresql") and not probe.get("credential_ref"):
        raise ValueError("PostgreSQL credential reference required")
    if op in FIELDS:
        if set(expected) - FIELDS[op]:
            raise ValueError("unsupported service contract field")
        if op not in {"postgresql_connect", "postgresql_read", "nginx_http", "nginx_stub_status"} and not expected:
            raise ValueError("explicit diagnostic threshold required")
        required = FIELDS[op] if op in {"postgresql_role", "postgresql_locks", "postgresql_headroom", "postgresql_vacuum"} else {"role", "max_replay_bytes"} if op == "postgresql_replication" else set()
        if not required <= set(expected):
            raise ValueError("missing service contract prerequisite")
        if op == "postgresql_replication" and expected["role"] == "primary" and expected.get("min_standbys", 0) < 1:
            raise ValueError("primary replication requires expected standbys")
    if "lock_timeout_ms" in expected and expected["lock_timeout_ms"] >= probe["timeout"] * 1000:
        raise ValueError("lock timeout must fit worker deadline")
