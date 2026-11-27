"""Backup, restore, export and import (pai/backup.py)."""
import json
import os
import tarfile
from contextlib import closing

import pytest

import main
from pai import audit, backup, store, vault


def memories():
    with closing(main.db()) as con:
        return [t for (t,) in con.execute("select text from memories order by id")]


@pytest.fixture
def box(client, tmp_path, monkeypatch):
    """A signed-in box with some data; DATA_DIR is the test's data dir."""
    data = main.DATA_DIR
    monkeypatch.setenv("DATA_DIR", data)
    with closing(main.db()) as con:
        vault.add_memory(con, "dentist is on Fridays")
        with con:
            con.execute("insert or replace into profile (key, value) values ('name', 'Sam')")
            con.execute("insert or replace into rules (id, text) values (1, 'be brief')")
    audit.record("memory_added", text="x")
    return tmp_path


def test_backup_round_trip_restores_the_vault(box, monkeypatch):
    out = backup.create(str(box / "bk"))
    assert os.stat(out).st_mode & 0o777 == 0o600
    with closing(main.db()) as con:
        vault.add_memory(con, "added after the backup")
    aside = backup.restore(out)
    assert memories() == ["dentist is on Fridays"]
    assert os.path.exists(os.path.join(aside, "pai.db"))  # the replaced vault is kept, not deleted
    assert audit.verify() is None


def test_backup_stays_encrypted(box):
    out = backup.create(str(box / "bk"))
    with tarfile.open(out) as t:
        raw = t.extractfile("pai.db").read()
    assert b"dentist" not in raw and not raw.startswith(b"SQLite format 3")


def test_verify_reports_contents_and_audit_chain(box):
    r = backup.verify(backup.create(str(box / "bk")))
    assert r["memories"] == 1 and r["audit_chain_ok"] is True


def test_verify_refuses_a_backup_made_with_another_key(box, monkeypatch):
    out = backup.create(str(box / "bk"))
    monkeypatch.setenv("PAI_VAULT_KEY", "a-different-key")
    with pytest.raises(SystemExit, match="does not open"):
        backup.verify(out)


def test_verify_refuses_a_damaged_backup(box, tmp_path):
    out = backup.create(str(box / "bk"))
    bad = tmp_path / "bad.tar"
    with tarfile.open(out) as src, tarfile.open(bad, "w") as dst:
        for m in src.getmembers():
            data = src.extractfile(m).read()
            if m.name == "pai.db":
                data = data[:-1] + bytes([data[-1] ^ 1])
            m.size = len(data)
            import io
            dst.addfile(m, io.BytesIO(data))
    with pytest.raises(SystemExit, match="damaged"):
        backup.verify(str(bad))


def test_restore_refuses_a_tar_with_unexpected_files(box, tmp_path):
    evil = tmp_path / "evil.tar"
    (tmp_path / "x").write_text("x")
    with tarfile.open(evil, "w") as t:
        t.add(tmp_path / "x", arcname="../../etc/passwd")
    with pytest.raises(SystemExit, match="not a PAI backup"):
        backup.restore(str(evil))


def test_restore_refuses_a_backup_from_a_newer_schema(box, monkeypatch):
    out = backup.create(str(box / "bk"))
    monkeypatch.setattr(store, "SCHEMA_VERSION", store.SCHEMA_VERSION - 1)
    with pytest.raises(SystemExit, match="newer PAI"):
        backup.restore(out)


def test_export_is_readable_and_leaves_out_login_data(box):
    out = box / "export.json"
    backup.export_json(str(out))
    doc = json.loads(out.read_text())
    assert doc["profile"]["name"] == "Sam" and doc["rules"] == "be brief"
    assert [m["text"] for m in doc["memories"]] == ["dentist is on Fridays"]
    assert "argon2" not in out.read_text() and "owner" not in doc
    assert os.stat(out).st_mode & 0o777 == 0o600


def test_import_adds_without_duplicates_and_keeps_existing(box):
    out = box / "export.json"
    backup.export_json(str(out))
    doc = json.loads(out.read_text())
    doc["memories"].append({"text": "new from the other box"})
    doc["profile"]["name"] = "Someone else"
    doc["rules"] = "be verbose"
    out.write_text(json.dumps(doc))
    r = backup.import_json(str(out))
    assert r == {"memories": 1, "profile": 0, "rules": False}
    assert memories() == ["dentist is on Fridays", "new from the other box"]
    assert main.profile()["name"] == "Sam"
    with closing(main.db()) as con:
        assert vault.search(con, "other box")  # imported memories are searchable


def test_import_replace_overwrites_profile_and_rules(box):
    out = box / "export.json"
    out.write_text(json.dumps({"format": 1, "kind": "pai-export", "profile": {"name": "Alex"}, "rules": "be verbose", "memories": []}))
    assert backup.import_json(str(out), replace=True)["rules"] is True
    assert main.profile()["name"] == "Alex"


def test_import_refuses_other_files(box):
    out = box / "x.json"
    out.write_text(json.dumps({"hello": 1}))
    with pytest.raises(SystemExit, match="not a PAI export"):
        backup.import_json(str(out))


def test_restore_needs_explicit_confirmation(box, capsys):
    assert backup.main(["restore", "whatever.tar"]) == 2
    assert "Stop the app first" in capsys.readouterr().err
