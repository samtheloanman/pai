"""A 256-bit random hex key is used as a raw SQLCipher key: no PBKDF2 on every open.

PBKDF2 (256k iterations, ~0.4 s) only helps low-entropy passphrases. `openssl rand -hex 32` keys already carry
256 bits, so stretching them costs a few hundred ms per connection for no security gain.
"""
import time
from contextlib import closing

import pytest
import sqlcipher3

from pai import store

HEX_KEY = "ab" * 32


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "v.db")


def test_hex_key_opens_without_kdf(path):
    store.connect(path, key=HEX_KEY).close()
    start = time.perf_counter()
    for _ in range(5):
        store.connect(path, key=HEX_KEY).close()
    assert (time.perf_counter() - start) / 5 < 0.05  # passphrase mode takes ~0.4 s per open


def test_hex_key_db_is_not_readable_as_a_passphrase(path):
    with closing(store.connect(path, key=HEX_KEY)) as con:
        con.execute("insert into memories (id, text) values (1, 'secret')")
        con.commit()
    con = sqlcipher3.connect(path)
    con.execute("pragma key = '" + HEX_KEY + "'")  # the old passphrase derivation must not open it
    with pytest.raises(sqlcipher3.DatabaseError):
        con.execute("select count(*) from sqlite_master").fetchone()
    con.close()


def test_passphrase_db_with_hex_key_is_rekeyed_once(path):
    # a vault created before this change: same hex key, but used as a passphrase
    con = sqlcipher3.connect(path)
    con.execute("pragma key = '" + HEX_KEY + "'")
    con.execute("create table keep (x)")
    con.execute("insert into keep values ('still here')")
    con.commit()
    con.close()
    with closing(store.connect(path, key=HEX_KEY)) as con:
        assert con.execute("select x from keep").fetchone()[0] == "still here"
    start = time.perf_counter()
    with closing(store.connect(path, key=HEX_KEY)) as con:  # now raw: fast
        assert con.execute("select x from keep").fetchone()[0] == "still here"
    assert time.perf_counter() - start < 0.05


def test_non_hex_key_still_works_as_passphrase(path):
    with closing(store.connect(path, key="an old passphrase")) as con:
        con.execute("insert into memories (id, text) values (1, 'x')")
        con.commit()
    with closing(store.connect(path, key="an old passphrase")) as con:
        assert con.execute("select text from memories").fetchone()[0] == "x"


def test_wrong_hex_key_is_still_a_key_error(path):
    store.connect(path, key=HEX_KEY).close()
    with pytest.raises(store.VaultKeyError):
        store.connect(path, key="cd" * 32)
