"""Atomic, bounded evidence persistence with explicit schema migration."""
import json
import os
import sqlite3
import time
from pathlib import Path
from .model import clean, canonical, digest

class Store:
    def __init__(self, path, max_records=10000, max_bytes=64*1024*1024):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.max_records, self.max_bytes = max_records, max_bytes
        old = os.umask(0o077)
        try: self.db = sqlite3.connect(self.path, timeout=3)
        finally: os.umask(old)
        os.chmod(self.path, 0o600)
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0,1):
            self.db.close()
            raise ValueError("unsupported store schema; preserve database and restore a compatible snapshot")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=3000")
        if version == 0:
            with self.db:
                self.db.execute("CREATE TABLE records(id TEXT PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL, hash TEXT NOT NULL, received REAL NOT NULL)")
                self.db.execute("CREATE TABLE health(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                self.db.execute("PRAGMA user_version=1")
        self.db.execute("PRAGMA max_page_count=20000")

    def ingest(self, records):
        if len(records) > 5000: raise ValueError("snapshot record limit")
        safe = [clean(r) for r in records]
        with self.db:
            self.db.execute("UPDATE health SET value=value WHERE key=\"progress_at\"")
            size, count = self.db.execute("SELECT COALESCE(SUM(length(body)),0),count(*) FROM records").fetchone()
            for r in safe:
                body, h = canonical(r), digest(r)
                prior = self.db.execute("SELECT hash FROM records WHERE id=?",(r["id"],)).fetchone()
                if prior:
                    if prior[0] != h: raise ValueError("immutable record ID collision")
                    continue
                count += 1; size += len(body.encode())
                if count > self.max_records or size > self.max_bytes:
                    raise ValueError("retention quota exceeded; export incidents then explicitly prune")
                self.db.execute("INSERT INTO records VALUES(?,?,?,?,?)",(r["id"],r["kind"],body,h,time.time()))
            self.db.execute("INSERT OR REPLACE INTO health VALUES(?,?)",("progress_at",str(time.time())))
        return len(safe)

    def records(self):
        rows = self.db.execute("SELECT body,hash FROM records ORDER BY id").fetchall()
        result=[]
        for body, h in rows:
            r=json.loads(body)
            if digest(r) != h: raise ValueError("corrupt retained evidence")
            result.append(clean(r))
        return result

    def health(self):
        n, size = self.db.execute("SELECT count(*),COALESCE(SUM(length(body)),0) FROM records").fetchone()
        progress=self.db.execute("SELECT value FROM health WHERE key=?",("progress_at",)).fetchone()
        return {"schema_version":1,"integrity":self.db.execute("PRAGMA quick_check").fetchone()[0],"records":n,"payload_bytes":size,"progress_age_seconds":time.time()-float(progress[0]) if progress else None,"record_quota":self.max_records,"payload_quota":self.max_bytes,"drops":0,"queue":"synchronous_no_backlog"}

    def prune(self, before):
        with self.db:
            return self.db.execute("DELETE FROM records WHERE kind=\"observation\" AND received<?",(before,)).rowcount

    def close(self): self.db.close()
