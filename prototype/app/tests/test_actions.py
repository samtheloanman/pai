import json
import threading
import time

import pytest

from pai import actions, audit, store

SENTINEL = "SENTINEL-summary-7c1e"


def kinds():
    return [e["kind"] for e in reversed(audit.entries(limit=100))]


def test_migration_adds_actions_table(client):
    import main
    from contextlib import closing
    with closing(main.db()) as con:
        assert con.execute("pragma user_version").fetchone()[0] == store.SCHEMA_VERSION
        assert con.execute("select count(*) from actions").fetchone()[0] == 0


def test_risky_action_does_not_run_on_propose(client):
    ran = []
    aid = actions.propose("delete", "Delete memory 3", {"memory_id": 3})
    assert ran == [] and actions.pending()[0]["id"] == aid


def test_propose_rejects_unknown_kind(client):
    with pytest.raises(ValueError):
        actions.propose("harmless", "x", {})


def test_ids_are_random(client):
    assert actions.propose("delete", "a", {}) != actions.propose("delete", "a", {})


def test_confirm_is_idempotent_and_expires(client, monkeypatch):
    ran = []
    aid = actions.propose("delete", "x", {}, ttl_s=60)
    assert actions.confirm(aid, lambda p: ran.append(1))["status"] == "done"
    assert actions.confirm(aid, lambda p: ran.append(1))["status"] == "already_done"
    old = actions.propose("delete", "y", {}, ttl_s=60)
    monkeypatch.setattr(actions, "now", lambda: time.time() + 61)
    assert actions.confirm(old, lambda p: ran.append(1))["status"] == "expired"
    assert ran == [1]
    assert actions.pending() == []


def test_unknown_id_and_unregistered_executor(client):
    assert actions.confirm("nope", lambda p: 1)["status"] == "unknown"
    aid = actions.propose("delete", "x", {"executor": "no_such"})
    assert actions.confirm(aid)["status"] == "unknown"
    assert actions.pending()[0]["id"] == aid  # not consumed


def test_rejected_never_runs(client):
    ran = []
    aid = actions.propose("delete", "x", {})
    actions.reject(aid)
    assert actions.confirm(aid, lambda p: ran.append(1))["status"] == "rejected"
    assert ran == [] and actions.pending() == []


def test_failed_executor_marks_failed_and_hides_error_from_audit(client):
    def boom(p): raise RuntimeError("secret-detail-xyz")
    aid = actions.propose("delete", "x", {})
    assert actions.confirm(aid, boom)["status"] == "failed"
    assert actions.confirm(aid, boom)["status"] == "failed"
    assert "secret-detail-xyz" not in json.dumps(audit.entries(limit=100))


def test_concurrent_confirms_run_executor_once(client):
    ran = []
    aid = actions.propose("delete", "x", {})
    def ex(p):
        time.sleep(0.05); ran.append(1)
    out = []
    ts = [threading.Thread(target=lambda: out.append(actions.confirm(aid, ex)["status"])) for _ in range(6)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert ran == [1] and out.count("done") == 1


def test_confirm_and_reject_are_audited(client, monkeypatch):
    payload = {"executor": "x", "secret": SENTINEL}
    a = actions.propose("delete", SENTINEL, payload)
    b = actions.propose("send", SENTINEL, payload)
    assert kinds() == ["action_proposed", "action_proposed"]
    actions.confirm(a, lambda p: None)
    assert kinds()[-1] == "action_confirmed"
    actions.reject(b)
    assert kinds()[-1] == "action_rejected"
    es = audit.entries(limit=100)
    assert SENTINEL not in json.dumps(es)
    assert all(e["fields"]["id"] in (a, b) and e["fields"]["kind"] in ("delete", "send") and "status" in e["fields"] for e in es)


def test_audit_failure_blocks_confirm_and_rolls_back(client, monkeypatch):
    ran = []
    aid = actions.propose("delete", "x", {})
    def bad(*a, **k): raise OSError("disk")
    monkeypatch.setattr(audit, "record", bad)
    with pytest.raises(actions.AuditUnavailable):
        actions.confirm(aid, lambda p: ran.append(1))
    assert ran == [] and actions.pending()[0]["id"] == aid
    with pytest.raises(actions.AuditUnavailable):
        actions.reject(aid)
    assert actions.pending()[0]["id"] == aid
    with pytest.raises(actions.AuditUnavailable):
        actions.propose("delete", "y", {})
    assert len(actions.pending()) == 1


# --- HTTP + chat wiring ---

def mem(client, text):
    import main
    return main.add_memory(text)


def test_chat_delete_proposes_but_does_not_delete(client):
    mid = mem(client, "my secret " + "x" * 200)
    r = client.post("/api/chat", json={"message": f"delete memory {mid}"}).json()["reply"]
    assert f"I can delete memory {mid}" in r and "Approvals" in r
    assert len(client.get("/api/memories").json()) == 1
    (a,) = client.get("/api/actions").json()
    assert set(a) == {"id", "kind", "summary", "created", "expires"} and a["kind"] == "delete"
    assert "x" * 81 not in a["summary"]


def test_chat_delete_missing_memory_no_proposal(client):
    r = client.post("/api/chat", json={"message": "forget memory 99"}).json()["reply"]
    assert r == "I can't find memory 99." and client.get("/api/actions").json() == []


def test_confirm_endpoint_deletes_memory_and_audits(client):
    mid = mem(client, "bye")
    client.post("/api/chat", json={"message": f"delete memory {mid}"})
    aid = client.get("/api/actions").json()[0]["id"]
    assert client.post(f"/api/actions/{aid}/confirm").json()["status"] == "done"
    assert client.get("/api/memories").json() == []
    assert "memory_deleted" in kinds() and "action_confirmed" in kinds()
    assert client.post(f"/api/actions/{aid}/confirm").json()["status"] == "already_done"


def test_reject_endpoint_keeps_memory(client):
    mid = mem(client, "stay")
    client.post("/api/chat", json={"message": f"delete memory {mid}"})
    aid = client.get("/api/actions").json()[0]["id"]
    assert client.post(f"/api/actions/{aid}/reject").json() == {"ok": True}
    assert len(client.get("/api/memories").json()) == 1 and client.get("/api/actions").json() == []


def test_endpoints_return_500_when_audit_down(client, monkeypatch):
    mid = mem(client, "stay")
    client.post("/api/chat", json={"message": f"delete memory {mid}"})
    aid = client.get("/api/actions").json()[0]["id"]
    monkeypatch.setattr(audit, "record", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    for path in ("confirm", "reject"):
        r = client.post(f"/api/actions/{aid}/{path}")
        assert r.status_code == 500 and r.json()["detail"] == "audit log unavailable"
    assert len(client.get("/api/memories").json()) == 1
