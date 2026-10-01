"""Bounded read-only PostgreSQL contracts. No user-supplied SQL or row payloads."""
import math
import re
import time
from .common import CollectionStatus
from ..policy import allowed_path

OPERATIONS = {"postgresql_connect", "postgresql_read", "postgresql_role",
              "postgresql_activity", "postgresql_locks", "postgresql_headroom",
              "postgresql_replication", "postgresql_vacuum"}
MONITORING = OPERATIONS - {"postgresql_connect", "postgresql_read"}
SQLSTATES = {
    "42501": "postgresql_permission", "42P01": "postgresql_fixture_missing",
    "42703": "postgresql_schema_mismatch", "55P03": "postgresql_lock_unavailable",
    "57014": "postgresql_query_canceled", "40P01": "postgresql_deadlock",
    "40001": "postgresql_serialization", "53300": "postgresql_connections_exhausted",
    "53400": "postgresql_configuration_limit", "53100": "postgresql_disk_full",
    "53200": "postgresql_out_of_memory", "57P01": "postgresql_shutdown",
    "57P02": "postgresql_crash_shutdown", "57P03": "postgresql_not_ready",
    "25006": "postgresql_read_only", "3D000": "postgresql_database_missing",
}

def error_value(code, phase):
    code = code if isinstance(code, str) and re.fullmatch(r"[0-9A-Z]{5}", code) else None
    reason = SQLSTATES.get(code)
    if not reason and code:
        reason = "postgresql_authentication" if code.startswith("28") else "postgresql_connection" if code.startswith("08") else "postgresql_operation"
    return {"reason": reason or ("postgresql_connection_or_startup" if phase == "connect" else "postgresql_operation"), **({"error_code": code} if code else {})}

def assess(conn, probe):
    """Fixed queries return aggregates only, even before redaction."""
    op, expected = probe["operation"], probe["expected"]
    if op == "postgresql_connect":
        return {}
    if op == "postgresql_read":
        count = conn.execute("SELECT count(*) FROM public.support_probe WHERE id = 1").fetchone()[0]
        ok = count >= expected.get("min_rows", 1)
        return {"rows_present": count > 0, **({"reason": "postgresql_fixture_contract"} if not ok else {})}, ok
    version = conn.info.server_version
    if not 140000 <= version < 190000:
        raise CollectionStatus("UNAVAILABLE", "postgresql_version_unsupported", server_version_num=version)
    recovery = conn.execute("SELECT pg_catalog.pg_is_in_recovery()").fetchone()[0]
    metadata = {"server_version_num": version, "in_recovery": recovery}
    if op in {"postgresql_role", "postgresql_replication"} and recovery != (expected["role"] == "standby"):
        return {**metadata, "reason": "postgresql_role_mismatch"}, False
    if op == "postgresql_role":
        return metadata, True
    if op in {"postgresql_activity", "postgresql_locks", "postgresql_headroom"} or op == "postgresql_replication" and not recovery:
        visible = conn.execute("SELECT (SELECT rolsuper FROM pg_catalog.pg_roles WHERE rolname = current_user) OR pg_catalog.pg_has_role(current_user, 'pg_read_all_stats', 'USAGE')").fetchone()[0]
        if visible is not True:
            raise CollectionStatus("DENIED", "postgresql_statistics_visibility", **metadata, statistics_visible=False)
        metadata["statistics_visible"] = True
    if op in {"postgresql_activity", "postgresql_locks"}:
        tracking = conn.execute("SELECT current_setting('track_activities') = 'on'").fetchone()[0]
        hidden = conn.execute("SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE backend_type = 'client backend' AND pid <> pg_backend_pid() AND (state IS NULL OR state = 'disabled')").fetchone()[0]
        if not tracking or hidden:
            raise CollectionStatus("UNAVAILABLE", "postgresql_activity_incomplete", **metadata, masked_sessions=hidden)
    if op == "postgresql_activity":
        active, idle, waiting, oldest = conn.execute("""SELECT count(*) FILTER (WHERE state = 'active'),
            count(*) FILTER (WHERE state LIKE 'idle in transaction%'),
            count(*) FILTER (WHERE wait_event_type = 'Lock'),
            coalesce(max(extract(epoch FROM (clock_timestamp() - xact_start))), 0)
            FROM pg_catalog.pg_stat_activity WHERE backend_type = 'client backend' AND pid <> pg_backend_pid()""").fetchone()
        value = {**metadata, "active_sessions": active, "idle_transactions": idle, "lock_waiters": waiting, "oldest_transaction_seconds": max(0, float(oldest))}
        ok = all(value[key] <= expected[limit] for key, limit in [("active_sessions", "max_active_sessions"), ("idle_transactions", "max_idle_transactions"), ("oldest_transaction_seconds", "max_transaction_seconds")] if limit in expected)
        return {**value, **({"reason": "postgresql_activity_threshold"} if not ok else {})}, ok
    if op == "postgresql_locks":
        candidates = conn.execute("SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE pid <> pg_backend_pid() AND wait_event_type = 'Lock'").fetchone()[0]
        if candidates > 512:
            raise CollectionStatus("UNAVAILABLE", "postgresql_lock_scan_budget", **metadata, lock_waiters=candidates)
        blocked = conn.execute("""SELECT count(*) FROM
            (SELECT pid FROM pg_catalog.pg_stat_activity WHERE pid <> pg_backend_pid() AND wait_event_type = 'Lock' LIMIT 513) AS waiting
            WHERE cardinality(pg_catalog.pg_blocking_pids(pid)) > 0""").fetchone()[0]
        if blocked > 512:
            raise CollectionStatus("UNAVAILABLE", "postgresql_lock_scan_budget", **metadata)
        ok = blocked <= expected["max_blocked_sessions"]
        return {**metadata, "blocked_sessions": blocked, **({"reason": "postgresql_blocking_threshold"} if not ok else {})}, ok
    if op == "postgresql_headroom":
        maximum, reserved, super_reserved, used = conn.execute("""SELECT current_setting('max_connections')::int,
            coalesce(current_setting('reserved_connections', true), '0')::int,
            current_setting('superuser_reserved_connections')::int,
            (SELECT count(*) FROM pg_catalog.pg_stat_activity WHERE backend_type = 'client backend')""").fetchone()
        # Includes this diagnostic connection: conservative instantaneous admission estimate.
        headroom = max(0, maximum - reserved - super_reserved - used)
        ok = headroom >= expected["min_connection_headroom"]
        return {**metadata, "connections": used, "max_connections": maximum, "reserved_connections": reserved + super_reserved, "connection_headroom": headroom, **({"reason": "postgresql_headroom_threshold"} if not ok else {})}, ok
    if op == "postgresql_replication":
        if recovery:
            backlog = conn.execute("SELECT pg_catalog.pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn())").fetchone()[0]
            value = metadata
        else:
            count, known, backlog = conn.execute("SELECT count(*), count(replay_lsn), max(pg_catalog.pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)) FROM pg_catalog.pg_stat_replication").fetchone()
            value = {**metadata, "standbys": count}
            if count < expected["min_standbys"]:
                return {**value, "reason": "postgresql_standbys_missing"}, False
            if known != count:
                raise CollectionStatus("UNAVAILABLE", "postgresql_replication_unknown", **value)
        if backlog is None or backlog < 0:
            raise CollectionStatus("UNAVAILABLE", "postgresql_replication_unknown", **value)
        backlog = int(backlog)
        ok = backlog <= expected["max_replay_bytes"]
        return {**value, "replay_backlog_bytes": backlog, **({"reason": "postgresql_replay_threshold"} if not ok else {})}, ok
    if op == "postgresql_vacuum":
        age = conn.execute("SELECT max(pg_catalog.age(datfrozenxid)) FROM pg_catalog.pg_database").fetchone()[0]
        if age is None or age < 0:
            raise CollectionStatus("UNAVAILABLE", "postgresql_vacuum_unknown", **metadata)
        ok = age <= expected["max_xid_age"]
        return {**metadata, "oldest_xid_age": age, **({"reason": "postgresql_xid_age_threshold"} if not ok else {})}, ok
    raise ValueError("unregistered PostgreSQL operation")

def collect(probe, manifest, host, port, ip, creds):
    import psycopg
    deadline = probe.get("_deadline", time.monotonic() + probe["timeout"])
    budget = max(.01, deadline - time.monotonic() - .2)
    options = "-c default_transaction_read_only=on -c search_path=pg_catalog -c statement_timeout=" + str(max(1, int(budget * 1000)))
    phase = "connect"
    try:
        with psycopg.connect(host=host, hostaddr=ip, port=port, user=creds["username"], password=creds["password"], dbname=creds.get("database", "support"), connect_timeout=max(1, math.ceil(budget)), application_name="support-evidence-probe", options=options, sslmode="verify-full" if creds.get("ca_file") else "disable", **({"sslrootcert": str(allowed_path(creds["ca_file"], manifest))} if creds.get("ca_file") else {})) as conn:
            if probe["operation"] == "postgresql_connect":
                return {}
            phase = "query"
            remaining = max(1, int((deadline - time.monotonic() - .2) * 1000))
            conn.execute("SELECT pg_catalog.set_config('statement_timeout', %s, true)", (str(remaining),))
            if "lock_timeout_ms" in probe["expected"]:
                conn.execute("SELECT pg_catalog.set_config('lock_timeout', %s, true)", (str(min(probe["expected"]["lock_timeout_ms"], remaining)),))
            return assess(conn, probe)
    except psycopg.Error as error:
        value = error_value(error.sqlstate, phase)
        if phase == "query" and probe["operation"] in MONITORING:
            if error.sqlstate == "42501":
                raise CollectionStatus("DENIED", "postgresql_monitoring_permission", **{k:v for k,v in value.items() if k != "reason"}) from None
            if error.sqlstate in {"42703", "42883", "42P01"}:
                raise CollectionStatus("UNAVAILABLE", "postgresql_capability_unavailable", **{k:v for k,v in value.items() if k != "reason"}) from None
        return value, False
