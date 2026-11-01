import re
import sqlite3
from contextlib import closing

import pytest

from pai import store


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "a.db")


def test_fresh_db_is_at_current_version(path):
    with closing(store.connect(path)) as con:
        assert con.execute("pragma user_version").fetchone()[0] == store.SCHEMA_VERSION


def test_newer_schema_is_refused(path):
    with closing(store.connect(path)) as con:
        con.execute(f"pragma user_version = {store.SCHEMA_VERSION + 1}")
    with pytest.raises(store.SchemaTooNew):
        store.connect(path)


def test_migrations_are_additive_only():
    for sql in store.MIGRATIONS:
        code = re.sub(r"--[^\n]*|/\*.*?\*/", "", sql, flags=re.S)
        assert not re.search(r"\b(drop|rename)\b", code, re.I)


def test_fts_tracks_insert_update_delete(path):
    with closing(store.connect(path)) as con:
        hits = lambda q: [r[0] for r in con.execute("select rowid from memories_fts where memories_fts match ?", (q,))]
        con.execute("insert into memories (id, text) values (1, 'dentist on Fridays')")
        assert hits("dentist") == [1]
        con.execute("update memories set text = 'coffee latte' where id = 1")
        assert hits("dentist") == [] and hits("coffee") == [1]
        con.execute("delete from memories where id = 1")
        assert hits("coffee") == []


def test_v1_db_upgrades_and_backfills_fts(path):
    with closing(sqlite3.connect(path)) as old:
        old.executescript(store.MIGRATIONS[0])
        old.execute("pragma user_version = 1")
        old.execute("insert into memories (text) values ('legacy dentist note')")
        old.commit()
    with closing(store.connect(path)) as con:
        assert con.execute("pragma user_version").fetchone()[0] == store.SCHEMA_VERSION
        assert con.execute("select count(*) from memories_fts where memories_fts match 'dentist'").fetchone()[0] == 1


def test_failed_migration_rolls_back_and_retries(path, monkeypatch):
    base = store.SCHEMA_VERSION
    good = "create table extra (a text); create table extra2 (b text);"
    monkeypatch.setattr(store, "MIGRATIONS", [*store.MIGRATIONS, good + " this is not sql;"])
    monkeypatch.setattr(store, "SCHEMA_VERSION", len(store.MIGRATIONS))
    with pytest.raises(store.sqlcipher.Error):
        store.connect(path)
    with closing(sqlite3.connect(path)) as raw:
        assert raw.execute("pragma user_version").fetchone()[0] == base
        names = {r[0] for r in raw.execute("select name from sqlite_master")}
    assert "extra" not in names and "extra2" not in names
    monkeypatch.setattr(store, "MIGRATIONS", [*store.MIGRATIONS[:-1], good])
    with closing(store.connect(path)) as con:
        assert con.execute("pragma user_version").fetchone()[0] == base + 1
