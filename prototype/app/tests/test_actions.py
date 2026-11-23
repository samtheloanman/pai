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


def test_local_files_listing_and_read(client, tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))
    (tmp_path / "files").mkdir()
    test_file = tmp_path / "files" / "notes.txt"
    test_file.write_text("Local knowledge without cloud egress", encoding="utf-8")

    files = actions.list_local_files()
    assert len(files) == 1
    assert files[0]["name"] == "notes.txt"
    assert files[0]["size"] > 0
    assert files[0]["is_dir"] is False

    content = actions.read_local_file(str(test_file))
    assert content == "Local knowledge without cloud egress"


def test_local_files_path_traversal_blocked(client, tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="escapes allowed directory"):
        actions._safe_path("../../etc/passwd", str(tmp_path))


def test_local_mail_listing(client, tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))
    # No maildir yet: an empty inbox, never an invented message
    assert actions.list_local_mail() == []

    # Maildir inbox mail
    inbox = tmp_path / "maildir" / "INBOX"
    inbox.mkdir(parents=True)
    msg = inbox / "msg-123.eml"
    msg.write_text("From: sam@local.pai\nSubject: Standup update\n\nAll clear", encoding="utf-8")
    
    mail_inbox = actions.list_local_mail()
    assert len(mail_inbox) == 1
    assert mail_inbox[0]["id"] == "msg-123.eml"
    assert mail_inbox[0]["subject"] == "msg-123"


def test_propose_send_mail_gated_by_approval(client):
    aid = actions.propose_send_mail("ops@local.pai", "Server status", "All systems operational")
    pending = actions.pending()
    assert any(a["id"] == aid for a in pending)
    target = next(a for a in pending if a["id"] == aid)
    assert target["kind"] == "send"
    assert "ops@local.pai" in target["summary"]

    res = actions.confirm(aid)
    # no mail connector exists: the approved action is recorded as failed, never as sent
    assert res == {"status": "failed", "error": "mail not configured"}
    assert "action_confirmed" in kinds()
    import main
    from contextlib import closing
    with closing(main.db()) as con:
        assert con.execute("select status, result from actions where id = ?", (aid,)).fetchone() == ("failed", "mail not configured")


def test_propose_file_write_and_confirm(client, tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))
    target_rel = "config/app_settings.json"
    content = '{"mode": "hermes_local"}'

    aid = actions.propose_file_write(target_rel, content)
    assert not (tmp_path / "files" / target_rel).exists()

    res = actions.confirm(aid)
    assert res["status"] == "done"
    assert (tmp_path / "files" / target_rel).read_text(encoding="utf-8") == content
    assert not (tmp_path / target_rel).exists()


def test_tools_api_endpoints(client, tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))

    # 1. Write file via proposed action and confirm via API
    write_res = client.post("/api/tools/files/write", json={"filepath": "docs/readme.txt", "content": "Hermes PAI Local Tooling"})
    assert write_res.status_code == 200
    aid = write_res.json()["action_id"]

    # Confirm the pending approval
    conf = client.post(f"/api/actions/{aid}/confirm")
    assert conf.status_code == 200 and conf.json()["status"] == "done"

    # 2. Read file via API
    rf = client.get("/api/tools/files/read", params={"filepath": "docs/readme.txt"})
    assert rf.status_code == 200
    assert rf.json()["content"] == "Hermes PAI Local Tooling"

    # 3. List files via API
    flist = client.get("/api/tools/files")
    assert flist.status_code == 200
    assert any("docs" in f["name"] for f in flist.json()["files"])

    # 4. Local mail endpoint
    mres = client.get("/api/tools/mail")
    assert mres.status_code == 200 and mres.json()["messages"] == []

    # 5. Outbound mail proposal endpoint
    mail_prop = client.post("/api/tools/mail/send", json={"to": "dev@local.pai", "subject": "Local tool ping", "body": "Ping"})
    assert mail_prop.status_code == 200
    m_aid = mail_prop.json()["action_id"]
    m_conf = client.post(f"/api/actions/{m_aid}/confirm")
    assert m_conf.status_code == 200 and m_conf.json() == {"status": "failed", "error": "mail not configured"}


def test_mail_folder_traversal_blocked(client, tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="escapes allowed maildir"):
        actions.list_local_mail(folder="../../etc")

    res = client.get("/api/tools/mail", params={"folder": "../../etc"})
    assert res.status_code == 400


def test_list_files_not_a_directory_error(client, tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))
    (tmp_path / "files").mkdir()
    single_file = tmp_path / "files" / "hello.txt"
    single_file.write_text("world", encoding="utf-8")

    with pytest.raises(ValueError, match="Path is not a directory"):
        actions.list_local_files("hello.txt")

    res = client.get("/api/tools/files", params={"directory": "hello.txt"})
    assert res.status_code == 400


def test_hermes_system_prompt_wires_local_mail_and_files(tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))
    (tmp_path / "files").mkdir()
    doc = tmp_path / "files" / "budget_2026.txt"
    doc.write_text("Confidential local numbers", encoding="utf-8")

    # When query mentions files
    prompt_files = main.system_prompt("what files are in my workspace?")
    assert "Local files (read-only, no egress):" in prompt_files
    assert "budget_2026.txt" in prompt_files

    # When query mentions mail: no maildir means no inbox section and no invented message
    assert "Local mail inbox" not in main.system_prompt("check my inbox for new emails")
    inbox = tmp_path / "maildir" / "INBOX"
    inbox.mkdir(parents=True)
    (inbox / "Quarterly review.eml").write_text("Subject: Quarterly review", encoding="utf-8")
    prompt_mail = main.system_prompt("check my inbox for new emails")
    assert "Local mail inbox (read-only, no egress):" in prompt_mail
    assert "Quarterly review" in prompt_mail



def test_file_tools_cannot_reach_vault_audit_or_keys(client, tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))
    for n in ("pai.db", "pai.db-wal", "pai.db-shm", "audit.db", "audit.db-journal", "vault-key"):
        (tmp_path / n).write_text("secret", encoding="utf-8")
    files = tmp_path / "files"
    files.mkdir()
    (files / "ok.txt").write_text("fine", encoding="utf-8")
    for n in ("copy.db", "x.db-wal", "id.key", "litellm.env", "my-secret.txt"):
        (files / n).write_text("secret", encoding="utf-8")

    # listing shows only the files dir, minus anything that looks like a database or a secret
    assert [f["name"] for f in actions.list_local_files()] == ["ok.txt"]
    assert actions.read_local_file("ok.txt") == "fine"
    for bad in ("../pai.db", "../pai.db-wal", "../audit.db", "../vault-key", str(tmp_path / "pai.db"), ".."):
        with pytest.raises(ValueError, match="escapes allowed directory"):
            actions._safe_path(bad)
    for bad in ("copy.db", "x.db-wal", "id.key", "litellm.env", "my-secret.txt", "sub/audit.db"):
        with pytest.raises(ValueError, match="protected"):
            actions._safe_path(bad)
    with pytest.raises(ValueError):
        actions.list_local_files("..")

    # the API refuses too, and a proposed write or delete of the vault never gets queued
    assert client.get("/api/tools/files/read", params={"filepath": "../pai.db"}).status_code == 400
    assert client.get("/api/tools/files", params={"directory": ".."}).status_code == 400
    assert client.post("/api/tools/files/write", json={"filepath": "../audit.db", "content": "x"}).status_code == 400
    assert client.post("/api/tools/files/write", json={"filepath": "pai.db", "content": "x"}).status_code == 400
    assert (tmp_path / "audit.db").read_text(encoding="utf-8") == "secret"


def test_file_delete_executor_is_confined(client, tmp_path, monkeypatch):
    import main
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))
    (tmp_path / "audit.db").write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError):
        actions._execute_delete_local_file({"filepath": "../audit.db"})
    assert (tmp_path / "audit.db").exists()
    (tmp_path / "files").mkdir()
    (tmp_path / "files" / "old.txt").write_text("bye", encoding="utf-8")
    assert actions._execute_delete_local_file({"filepath": "old.txt"})["deleted"] is True
    with pytest.raises(FileNotFoundError):  # deleting nothing is not reported as a delete
        actions._execute_delete_local_file({"filepath": "old.txt"})
