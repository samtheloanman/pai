"""Tamper-evident audit trail: an append-only, hash-chained log in its own encrypted file (DATA_DIR/audit.db).

Entries never hold message text unless AUDIT_CONTENT=1. A chain detects edits, deleted or reordered
entries. It cannot see the TAIL being cut off; checkpoint() stores the head hash in a separate table so
verify() notices a truncation back past it (an attacker who can also rewrite the checkpoints table, or
who holds the vault key, can still rewrite everything: this is evidence for the owner, not a defence
against a fully compromised box).

The checkpoint protects the log only up to the last clean verify: GET /api/activity/verify (and app
startup) write one after a clean verify. Ids are `integer primary key` WITHOUT AUTOINCREMENT, so after a
tail truncation new entries reuse the cut ids and chain cleanly onto the cut head; that is undetectable
unless a checkpoint covered the cut entries.

Hash rule: hash = sha256(json.dumps([prev_hash, ts, kind, fields_json], separators=(",", ":"))), where
fields_json is the canonical (sort_keys, compact) JSON of the fields. JSON-encoding the list keeps the
parts unambiguous (no way to shift characters between neighbouring fields).
"""
import hashlib
import json
import os
import threading
import time
from contextlib import closing

from pai import store

KINDS = {"model_call", "route", "action_proposed", "action_confirmed", "action_rejected",
         "memory_added", "memory_deleted", "outbound", "config_changed"}
CONTENT_FIELDS = {"prompt", "reply", "text", "answer"}
MAX_LIMIT = 500
ZERO = "0" * 64
_lock = threading.Lock()  # serialises writers in this process; BEGIN IMMEDIATE covers other processes

MIGRATIONS = [
    """
    create table entries (id integer primary key, ts text not null, kind text not null, fields text not null,
                          prev_hash text not null, hash text not null);
    create table checkpoints (id integer primary key, entry_id integer not null, head_hash text not null, ts text not null);
    """,
]


def _con():
    con = store.connect(os.path.join(os.environ.get("DATA_DIR", "/data"), "audit.db"),
                        key=os.environ["PAI_VAULT_KEY"], migrations=MIGRATIONS)
    con.isolation_level = None  # autocommit; record() opens its own BEGIN IMMEDIATE
    return con


def _hash(prev: str, ts: str, kind: str, fields: str) -> str:
    return hashlib.sha256(json.dumps([prev, ts, kind, fields], separators=(",", ":")).encode()).hexdigest()


def record(kind: str, /, **fields) -> int:
    """Append one entry and return its id. Raises on any failure: callers decide what a failed audit means."""
    if kind not in KINDS:
        raise ValueError(f"unknown audit kind {kind!r}")
    if os.getenv("AUDIT_CONTENT") != "1":
        fields = {k: v for k, v in fields.items() if k not in CONTENT_FIELDS}
    body = json.dumps(fields, sort_keys=True, separators=(",", ":"), default=str)
    with _lock, closing(_con()) as con:
        con.execute("begin immediate")
        try:
            row = con.execute("select hash from entries order by id desc limit 1").fetchone()
            prev = row[0] if row else ZERO
            now = time.time()  # one reading for both seconds and milliseconds
            ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(now)) + f".{int(now * 1000) % 1000:03d}Z"
            eid = con.execute("insert into entries (ts, kind, fields, prev_hash, hash) values (?,?,?,?,?)",
                              (ts, kind, body, prev, _hash(prev, ts, kind, body))).lastrowid
            con.execute("commit")
        except BaseException:
            try:
                con.execute("rollback")
            except Exception:  # e.g. "no transaction active": never mask the original error
                pass
            raise
    return eid


def checkpoint() -> None:
    """Remember the current head so verify() can detect later truncation of the tail."""
    with _lock, closing(_con()) as con:
        row = con.execute("select id, hash from entries order by id desc limit 1").fetchone()
        if row:
            con.execute("insert into checkpoints (entry_id, head_hash, ts) values (?,?,?)",
                        (row[0], row[1], time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))


def verify() -> int | None:
    """Id of the first broken entry, or None if the chain (and the latest checkpoint) is intact."""
    with closing(_con()) as con:
        prev, expect = ZERO, 1
        for eid, ts, kind, fields, p, h in con.execute("select id, ts, kind, fields, prev_hash, hash from entries order by id"):
            if eid != expect or p != prev or h != _hash(p, ts, kind, fields):  # gap, reorder or edit
                return eid
            prev, expect = h, eid + 1
        cp = con.execute("select entry_id, head_hash from checkpoints order by id desc limit 1").fetchone()
        if cp and not con.execute("select 1 from entries where id = ? and hash = ?", cp).fetchone():
            return cp[0]
    return None


def entries(limit: int = 100, kind: str | None = None) -> list[dict]:
    """Newest first."""
    limit = max(1, min(limit, MAX_LIMIT))
    q, args = "select id, ts, kind, fields from entries", []
    if kind:
        q, args = q + " where kind = ?", [kind]
    with closing(_con()) as con:
        rows = con.execute(q + " order by id desc limit ?", [*args, limit]).fetchall()
    return [{"id": i, "ts": ts, "kind": k, "fields": json.loads(f)} for i, ts, k, f in rows]
