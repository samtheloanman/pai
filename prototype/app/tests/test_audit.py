import json
import threading

import pytest

from pai import audit

SECRET = "SENTINEL-9f3a-secret"


def raw_rows(audit_db):
    return audit._con().execute("select * from entries order by id").fetchall()


def test_chain_verifies_and_detects_edits(audit_db):
    for i in range(3): audit.record("route", **{"pai.route": "chat"})
    assert audit.verify() is None
    audit._con().execute("update entries set fields = '{}' where id = 2")
    assert audit.verify() == 2


def test_first_entry_links_to_zeros_and_hash_formula(audit_db):
    import hashlib
    audit.record("route", **{"pai.route": "chat"})
    _id, ts, kind, fields, prev, h = raw_rows(audit_db)[0]
    assert prev == "0" * 64
    assert h == hashlib.sha256((prev + ts + kind + fields).encode()).hexdigest()
    assert fields == '{"pai.route":"chat"}'


def test_deleting_a_middle_entry_is_detected(audit_db):
    for _ in range(4): audit.record("route")
    audit._con().execute("delete from entries where id = 2")
    assert audit.verify() == 3


def test_reordered_entries_are_detected(audit_db):
    for i in range(4): audit.record("route", n=i)
    con = audit._con()
    a, b = con.execute("select ts, kind, fields, prev_hash, hash from entries where id in (2, 3) order by id").fetchall()
    con.execute("update entries set ts=?, kind=?, fields=?, prev_hash=?, hash=? where id = 2", b)
    con.execute("update entries set ts=?, kind=?, fields=?, prev_hash=?, hash=? where id = 3", a)
    assert audit.verify() == 2


def test_tail_truncation_needs_a_checkpoint(audit_db):
    for _ in range(3): audit.record("route")
    audit.checkpoint()
    audit._con().execute("delete from entries where id = 3")
    assert audit.verify() == 3  # the checkpointed head is gone
    # documented limit: without a checkpoint a truncated tail is undetectable
    audit._con().execute("delete from checkpoints")
    assert audit.verify() is None


def test_entries_added_after_checkpoint_still_verify(audit_db):
    audit.record("route"); audit.checkpoint(); audit.record("route")
    assert audit.verify() is None


def test_content_not_stored_by_default(audit_db):
    audit.record("model_call", prompt="secret text", **{"gen_ai.request.model": "pai-chat"})
    assert "secret text" not in json.dumps(audit.entries())


def test_content_stored_when_audit_content_on(audit_db, monkeypatch):
    monkeypatch.setenv("AUDIT_CONTENT", "1")
    audit.record("model_call", prompt="secret text")
    assert audit.entries()[0]["fields"]["prompt"] == "secret text"


def test_concurrent_writes_keep_chain(audit_db):
    threads = [threading.Thread(target=audit.record, args=("route",)) for _ in range(20)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert audit.verify() is None and len(audit.entries(limit=50)) == 20


def test_entries_filter_by_kind_newest_first(audit_db):
    audit.record("route"); audit.record("config_changed", what="rules"); audit.record("route")
    assert [e["id"] for e in audit.entries()] == [3, 2, 1]
    assert [e["kind"] for e in audit.entries(kind="config_changed")] == ["config_changed"]


def test_chat_call_writes_one_model_call_entry(client, mock_litellm):
    r = client.post("/api/chat", json={"message": "tell me a story about dragons"})
    assert r.status_code == 200 and r.json()["reply"] == "hello there"
    calls = [e for e in audit.entries(kind="model_call") if e["fields"]["gen_ai.request.model"] == "pai-chat"]
    assert len(calls) == 1
    f = calls[0]["fields"]
    assert isinstance(f["duration_ms"], int) and f["duration_ms"] >= 0
    assert f["gen_ai.usage.input_tokens"] == 11 and f["gen_ai.usage.output_tokens"] == 7
    assert f["success"] is True
    assert "prompt" not in f and "reply" not in f
    assert "dragons" not in json.dumps(audit.entries()) and "hello there" not in json.dumps(audit.entries())
    assert audit.entries(kind="route")[0]["fields"]["pai.route"]
    assert audit.verify() is None


def test_chat_stores_prompt_and_reply_when_audit_content_on(client, mock_litellm, monkeypatch):
    monkeypatch.setenv("AUDIT_CONTENT", "1")
    client.post("/api/chat", json={"message": "tell me a story about dragons"})
    f = next(e["fields"] for e in audit.entries(kind="model_call") if e["fields"]["gen_ai.request.model"] == "pai-chat")
    assert f["reply"] == "hello there" and "dragons" in f["prompt"]


def test_model_error_is_audited_as_failure(client, mock_litellm):
    mock_litellm.status = 500
    assert client.post("/api/chat", json={"message": "tell me a story about dragons"}).status_code == 502
    f = audit.entries(kind="model_call")[0]["fields"]
    assert f["success"] is False and f["error"] == "HTTP 500"


def test_voice_calls_are_audited(client, mock_litellm):
    client.post("/api/transcribe", files={"audio": ("a.webm", b"x", "audio/webm")})
    client.post("/api/speak", json={"text": "hi"})
    models = {e["fields"]["gen_ai.request.model"] for e in audit.entries(kind="model_call")}
    assert {"pai-stt", "pai-tts"} <= models


def test_memory_and_config_events_never_store_text(client, mock_litellm):
    client.post("/api/chat", json={"message": f"Remember that {SECRET} lives here"})
    client.post("/api/chat", json={"message": f"tell me about {SECRET}"})
    mid = client.get("/api/memories").json()[0]["id"]
    client.put("/api/rules", json={"text": f"rule {SECRET}"})
    client.post("/api/interview", json={"key": "name", "value": SECRET})
    client.delete(f"/api/memories/{mid}")
    kinds = [e["kind"] for e in audit.entries(limit=100)]
    assert {"memory_added", "memory_deleted", "config_changed"} <= set(kinds)
    cfg = {e["fields"]["what"]: e["fields"] for e in audit.entries(kind="config_changed")}
    assert cfg["interview"]["key"] == "name" and "rules" in cfg
    assert SECRET not in json.dumps(raw_rows(None))
    assert client.get("/api/activity").status_code == 200 and SECRET not in client.get("/api/activity").text


def test_memory_text_stored_only_with_audit_content(client, monkeypatch):
    monkeypatch.setenv("AUDIT_CONTENT", "1")
    client.post("/api/chat", json={"message": "Remember that my dentist is on Fridays"})
    assert audit.entries(kind="memory_added")[0]["fields"]["text"] == "my dentist is on Fridays"


def test_activity_api(client, mock_litellm):
    for i in range(3): audit.record("route")
    audit.record("config_changed", what="x")
    assert len(client.get("/api/activity?kind=route").json()) == 3
    assert len(client.get("/api/activity?limit=2").json()) == 2
    assert client.get("/api/activity?limit=99999").status_code == 200
    assert client.get("/api/activity/verify").json() == {"intact": True, "first_broken": None}
    audit._con().execute("update entries set kind = 'x' where id = 2")
    assert client.get("/api/activity/verify").json() == {"intact": False, "first_broken": 2}


def test_limit_is_capped_at_500(audit_db):
    for _ in range(3): audit.record("route")
    assert len(audit.entries(limit=10**6)) == 3
    assert audit.MAX_LIMIT == 500


def test_audit_failure_fails_the_request(client, mock_litellm, monkeypatch):
    def boom(*a, **k): raise RuntimeError("disk full")
    monkeypatch.setattr(audit, "record", boom)
    r = client.post("/api/chat", json={"message": "tell me a story about dragons"})
    assert r.status_code == 500 and r.json()["detail"] == "audit log unavailable"


def test_failed_memory_audit_leaves_no_memory(client, monkeypatch):
    real = audit.record
    def selective(kind, **f):
        if kind == "memory_added": raise RuntimeError("disk full")
        return real(kind, **f)
    monkeypatch.setattr(audit, "record", selective)
    r = client.post("/api/chat", json={"message": "Remember that the code is 1234"})
    assert r.status_code == 500 and r.json()["detail"] == "audit log unavailable"
    assert client.get("/api/memories").json() == []


def test_failed_delete_audit_keeps_memory(client, monkeypatch):
    client.post("/api/chat", json={"message": "Remember that the code is 1234"})
    mid = client.get("/api/memories").json()[0]["id"]
    monkeypatch.setattr(audit, "record", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    assert client.delete(f"/api/memories/{mid}").status_code == 500
    assert len(client.get("/api/memories").json()) == 1
