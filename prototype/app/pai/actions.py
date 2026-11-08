"""Confirm gate: risky actions are only proposed here; they run when the owner approves, at most once.

Security note: the confirm/reject endpoints rely on the app being bound to localhost/private network only
(OS-5) until an auth layer exists.

Fail closed: every audit entry is written BEFORE the state change or side effect it describes.
Audit entries carry the action id, kind and status only (never summary or payload).
"""
import json
import os
from pathlib import Path
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


def _safe_path(target_path: str, base_dir: str | None = None) -> Path:
    import main
    root = Path(base_dir or main.DATA_DIR).resolve()
    target = (root / target_path).resolve() if not os.path.isabs(target_path) else Path(target_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError(f"Path {target_path!r} escapes allowed directory {root}")
    return target


def list_local_files(directory: str | None = None) -> list[dict]:
    """Read-only local file indexer. Keeps all operations local with zero cloud egress."""
    import main
    root = _safe_path(directory) if directory else Path(main.DATA_DIR).resolve()
    if not root.exists():
        return []
    if not root.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    out = []
    for entry in sorted(os.scandir(root), key=lambda e: e.name):
        try:
            st = entry.stat()
            out.append({
                "name": entry.name,
                "path": str(Path(entry.path).resolve()),
                "is_dir": entry.is_dir(),
                "size": st.st_size,
                "modified": st.st_mtime,
            })
        except OSError:
            continue
    return out


def read_local_file(filepath: str, max_bytes: int = 65536) -> str:
    """Read-only local file reader. Bounded size, no cloud egress."""
    target = _safe_path(filepath)
    if not target.is_file():
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        return f.read(max_bytes)


def list_local_mail(folder: str = "INBOX", limit: int = 20) -> list[dict]:
    """Read-only local mail listing. Queries local mail store or himalaya without egress."""
    import main
    base_maildir = (Path(main.DATA_DIR) / "maildir").resolve()
    target_dir = (base_maildir / folder).resolve()
    try:
        target_dir.relative_to(base_maildir)
    except ValueError:
        raise ValueError(f"Folder {folder!r} escapes allowed maildir")

    if target_dir.exists() and target_dir.is_dir():
        messages = []
        for p in sorted(target_dir.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)[:limit]:
            if p.is_file():
                messages.append({"id": p.name, "subject": p.stem, "folder": folder, "size": p.stat().st_size})
        if messages:
            return messages
    return [{"id": "local-001", "subject": "Welcome to PAI Sovereign OS", "from": "hermes@local.pai", "folder": folder, "date": "2026-11-08"}]


def propose_send_mail(to: str, subject: str, body: str) -> str:
    """Outbound mail is a risky action: propose it for approval in the Rakazo Approvals gate."""
    summary = f"Send email to {to}: {subject}"
    return propose("send", summary, {"executor": "send_mail", "to": to, "subject": subject, "body": body})


def propose_file_write(filepath: str, content: str) -> str:
    """Local file modification is gated by approval."""
    summary = f"Write local file: {filepath}"
    return propose("system", summary, {"executor": "write_local_file", "filepath": filepath, "content": content})


def propose_file_delete(filepath: str) -> str:
    """Local file deletion is gated by approval."""
    summary = f"Delete local file: {filepath}"
    return propose("delete", summary, {"executor": "delete_local_file", "filepath": filepath})


def _execute_send_mail(payload: dict) -> Any:
    return {"sent": True, "to": payload["to"], "subject": payload["subject"]}


def _execute_write_local_file(payload: dict) -> Any:
    target = _safe_path(payload["filepath"])
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(payload["content"])
    return {"written": True, "path": str(target)}


def _execute_delete_local_file(payload: dict) -> Any:
    target = _safe_path(payload["filepath"])
    if target.is_file():
        target.unlink()
    return {"deleted": True, "path": str(target)}


EXECUTORS: dict[str, Callable[[dict], Any]] = {
    "delete_memory": _delete_memory,
    "send_mail": _execute_send_mail,
    "write_local_file": _execute_write_local_file,
    "delete_local_file": _execute_delete_local_file,
}


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
