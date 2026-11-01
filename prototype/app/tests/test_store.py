import re

import pytest

from pai import store


def test_fresh_db_is_at_current_version(tmp_path):
    con = store.connect(str(tmp_path / "a.db"))
    assert con.execute("pragma user_version").fetchone()[0] == store.SCHEMA_VERSION


def test_newer_schema_is_refused(tmp_path):
    p = str(tmp_path / "a.db")
    con = store.connect(p)
    con.execute(f"pragma user_version = {store.SCHEMA_VERSION + 1}")
    con.close()
    with pytest.raises(store.SchemaTooNew):
        store.connect(p)


def test_migrations_are_additive_only():
    for sql in store.MIGRATIONS:
        assert not re.search(r"\b(drop|rename)\b", sql, re.I)


def test_fts_tracks_insert_update_delete(tmp_path):
    con = store.connect(str(tmp_path / "a.db"))
    hits = lambda q: [r[0] for r in con.execute("select rowid from memories_fts where memories_fts match ?", (q,))]
    con.execute("insert into memories (id, text) values (1, 'dentist on Fridays')")
    assert hits("dentist") == [1]
    con.execute("update memories set text = 'coffee latte' where id = 1")
    assert hits("dentist") == [] and hits("coffee") == [1]
    con.execute("delete from memories where id = 1")
    assert hits("coffee") == []


def test_v1_db_upgrades_and_backfills_fts(tmp_path):
    import sqlite3
    p = str(tmp_path / "old.db")
    old = sqlite3.connect(p)
    old.executescript(store.MIGRATIONS[0])
    old.execute("pragma user_version = 1")
    old.execute("insert into memories (text) values ('legacy dentist note')")
    old.commit()
    old.close()
    con = store.connect(p)
    assert con.execute("pragma user_version").fetchone()[0] == store.SCHEMA_VERSION
    assert con.execute("select count(*) from memories_fts where memories_fts match 'dentist'").fetchone()[0] == 1
