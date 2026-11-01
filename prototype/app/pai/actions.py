"""Confirm gate: risky actions are only proposed here; they run when the owner approves, at most once.

Security note: the confirm/reject endpoints rely on the app being bound to localhost/private network only
(OS-5) until an auth layer exists.

Fail closed: every audit entry is written BEFORE the state change or side effect it describes.
Audit entries carry the action id, kind and status only (never summary or payload).
"""
import json
import secrets
import time
from contextlib import closing
from typing import Any, Callable

from pai import audit

RISKY = {"send", "delete", "spend", "system"}


class AuditUnavailable(Exception):
    """The audit write failed, so the action was not taken."""


def now() -> float:  # module-level so tests can move the clock
    return time.time()


def _db():
    import main  # lazy: main imports this module, and owns the vault connection
    return main.db()


def _audit(entry: str, **fields) -> None:
    try:
        audit.record(entry, **fields)
    except Exception as e:
        raise AuditUnavailable(type(e).__name__) from None


def _delete_memory(payload: dict) -> Any:
    import main
    return main.forget(int(payload["memory_id"]))  # same path as DELETE /api/memories/{mid}, incl. its audit entry


EXECUTORS: dict[str, Callable[[dict], Any]] = {"delete_memory": _delete_memory}


def propose(kind: str, summary: str, payload: dict, ttl_s: int = 900) -> str:
    if kind not in RISKY:
        raise ValueError(f"{kind!r} is not a risky action kind")
    aid, t = secrets.token_urlsafe(16), now()
    _audit("action_proposed", id=aid, kind=kind, status="pending")
    with closing(_db()) as con, con:
        con.execute("insert into actions (id, kind, summary, payload, status, created, expires) values (?,?,?,?,'pending',?,?)",
                    (aid, kind, summary, json.dumps(payload), t, t + ttl_s))
    return aid


def pending() -> list[dict]:
    with closing(_db()) as con:
        rows = con.execute("select id, kind, summary, created, expires from actions where status = 'pending' and expires > ? order by created", (now(),)).fetchall()
    return [dict(zip(("id", "kind", "summary", "created", "expires"), r)) for r in rows]


def reject(action_id: str) -> None:
    with closing(_db()) as con:
        row = con.execute("select kind from actions where id = ? and status = 'pending'", (action_id,)).fetchone()
        if not row:
            return
        _audit("action_rejected", id=action_id, kind=row[0], status="rejected")
        with con:
            con.execute("update actions set status = 'rejected' where id = ? and status = 'pending'", (action_id,))


def confirm(action_id: str, executor: Callable[[dict], Any] | None = None) -> dict:
    """Run the action at most once. executor defaults to EXECUTORS[payload['executor']]."""
    with closing(_db()) as con:
        row = con.execute("select kind, payload, status, expires from actions where id = ?", (action_id,)).fetchone()
        if not row:
            return {"status": "unknown"}
        kind, payload, status, expires = row
        payload = json.loads(payload)
        if executor is None:
            executor = EXECUTORS.get(payload.get("executor"))
            if executor is None:
                return {"status": "unknown"}
        with con:  # the claim: only one caller can move pending -> executing
            claimed = con.execute("update actions set status = 'executing' where id = ? and status = 'pending' and expires > ?",
                                  (action_id, now())).rowcount == 1
        if not claimed:
            if status == "pending":  # lost the claim only because it is past its expiry (or another caller won)
                with con:
                    con.execute("update actions set status = 'expired' where id = ? and status = 'pending' and expires <= ?", (action_id, now()))
            cur = con.execute("select status from actions where id = ?", (action_id,)).fetchone()[0]
            return {"status": {"done": "already_done", "executing": "already_done"}.get(cur, cur)}
        try:
            _audit("action_confirmed", id=action_id, kind=kind, status="confirmed")
        except AuditUnavailable:
            with con:
                con.execute("update actions set status = 'pending' where id = ? and status = 'executing'", (action_id,))
            raise
        try:
            executor(payload)
            final, extra = "done", {}
        except Exception as e:
            final, extra = "failed", {"error": type(e).__name__}
        with con:
            con.execute("update actions set status = ?, result = ? where id = ?", (final, extra.get("error"), action_id))
        return {"status": final, **extra}
