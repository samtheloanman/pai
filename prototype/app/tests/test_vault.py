import os
import sqlite3

import pytest

from pai import store, vault


def test_file_is_unreadable_without_key(tmp_path):
    p = str(tmp_path / "v.db"); store.connect(p, key="k1").close()
    with pytest.raises(vault.VaultKeyError):
        store.connect(p, key=None)


def test_wrong_key_refuses(tmp_path):
    p = str(tmp_path / "v.db"); store.connect(p, key="k1").close()
    with pytest.raises(vault.VaultKeyError):
        store.connect(p, key="k2")
    assert len(list(tmp_path.iterdir())) == 1   # no second vault created


def test_file_on_disk_is_not_plain_sqlite(tmp_path):
    p = tmp_path / "v.db"; con = store.connect(str(p), key="k"); vault.add_memory(con, "secret dentist"); con.close()
    assert not p.read_bytes().startswith(b"SQLite format 3")
    raw = sqlite3.connect(str(p))
    with pytest.raises(sqlite3.DatabaseError):
        raw.execute("select count(*) from sqlite_master").fetchone()
    raw.close()


def test_key_with_quotes_is_safe(tmp_path):
    p = str(tmp_path / "v.db"); key = "it's\"; drop table memories; --"
    store.connect(p, key=key).close()
    store.connect(p, key=key).close()


def test_keyword_search_finds_exact_terms(tmp_path):
    con = store.connect(str(tmp_path / "v.db"), key="k")
    for t in ["invoice 4471 from Acme", "dentist on Fridays", "Jo prefers calls before 11"]:
        vault.add_memory(con, t)
    assert vault.search(con, "4471")[0] == "invoice 4471 from Acme"


def test_search_survives_quotes_and_operators(tmp_path):
    con = store.connect(str(tmp_path / "v.db"), key="k")
    vault.add_memory(con, "Jo said call back AND confirm")
    for q in ['foo"', "AND", 'NOT "x', "a OR", "(", "*", "col:val", ""]:
        assert isinstance(vault.search(con, q), list)
    assert vault.search(con, "call AND")[0] == "Jo said call back AND confirm"


def test_hybrid_merges_vector_hits(tmp_path):
    con = store.connect(str(tmp_path / "v.db"), key="k")
    fake = lambda s: [1.0, 0.0] if "tooth" in s or "dentist" in s else [0.0, 1.0]
    vault.add_memory(con, "dentist on Fridays", embed=fake)
    vault.add_memory(con, "oat latte", embed=fake)
    assert vault.search(con, "tooth pain", embed=fake)[0] == "dentist on Fridays"


def test_hybrid_dedupes_fts_and_vector_hit(tmp_path):
    con = store.connect(str(tmp_path / "v.db"), key="k")
    fake = lambda s: [1.0, 0.0]
    vault.add_memory(con, "dentist on Fridays", embed=fake)
    assert vault.search(con, "dentist", embed=fake) == ["dentist on Fridays"]


def test_vector_dimension_mismatch_rejected_and_rolled_back(tmp_path):
    con = store.connect(str(tmp_path / "v.db"), key="k")
    vault.add_memory(con, "a", embed=lambda s: [1.0, 0.0])
    with pytest.raises(ValueError):
        vault.add_memory(con, "b", embed=lambda s: [1.0, 0.0, 0.0])
    assert con.execute("select count(*) from memories").fetchone()[0] == 1


def test_locked_db_is_not_reported_as_wrong_key(tmp_path):
    p = str(tmp_path / "v.db"); store.connect(p, key="k").close()
    holder = store.connect(p, key="k")
    holder.execute("begin exclusive")
    try:
        with pytest.raises(store.sqlcipher.OperationalError):
            store.connect(p, key="k")
    finally:
        holder.rollback(); holder.close()


def test_garbage_file_reports_key_error_and_creates_nothing(tmp_path):
    p = tmp_path / "v.db"; p.write_bytes(os.urandom(4096))  # SQLCipher says "file is not a database" for this
    with pytest.raises(vault.VaultKeyError):
        store.connect(str(p), key="k")
    assert len(list(tmp_path.iterdir())) == 1


def test_forget_removes_vector_row(tmp_path):
    con = store.connect(str(tmp_path / "v.db"), key="k")
    fake = lambda s: [1.0, 0.0]
    mid = vault.add_memory(con, "dentist on Fridays", embed=fake)
    with con:
        con.execute("delete from memories where id = ?", (mid,))
    assert con.execute("select count(*) from memories_vec").fetchone()[0] == 0
    assert vault.search(con, "dentist", embed=fake) == []


def test_secure_delete_is_on(tmp_path):
    # simplest honest check: the pragma is on for a fresh vault connection (SQLite then zeroes deleted content in freed pages)
    con = store.connect(str(tmp_path / "v.db"), key="k")
    assert con.execute("pragma secure_delete").fetchone()[0] == 1
