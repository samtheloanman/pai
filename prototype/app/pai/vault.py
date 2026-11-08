"""Encrypted-vault memory: add and hybrid (FTS5 BM25 + sqlite-vec) search."""
import re
from typing import Callable

import sqlite_vec

from .store import VaultKeyError  # noqa: F401  (re-exported)

RRF_K = 60


def _vec_table(con, dim: int) -> None:
    """Create the vec0 table on the first embedding; later vectors must match its dimension."""
    row = con.execute("select value from vault_meta where key = 'embed_dim'").fetchone()
    if row:
        if int(row[0]) != dim:
            raise ValueError(f"embedding has {dim} dimensions, vault expects {row[0]}")
        return
    con.execute(f"create virtual table memories_vec using vec0(embedding float[{dim}])")
    con.execute("create trigger memories_vec_ad after delete on memories begin delete from memories_vec where rowid = old.id; end")
    con.execute("insert into vault_meta (key, value) values ('embed_dim', ?)", (str(dim),))


def add_memory(con, text: str, embed: Callable[[str], list[float]] | None = None) -> int:
    with con:  # one transaction: memory, FTS rows (triggers) and vector
        mid = con.execute("insert into memories (text) values (?)", (text,)).lastrowid
        if embed:
            vec = embed(text)
            _vec_table(con, len(vec))
            con.execute("insert into memories_vec (rowid, embedding) values (?, ?)", (mid, sqlite_vec.serialize_float32(vec)))
    return mid


def _fts_query(q: str) -> str:
    # quote every token so user text like  foo"  or  AND  is data, not FTS5 syntax; OR for recall
    # tokens under 3 chars (is, my, on) are dropped unless numeric: they match nearly everything
    return " OR ".join('"' + t + '"' for t in re.findall(r"\w+", q) if len(t) > 2 or t.isdigit())


def search(con, query: str, limit: int = 5, embed: Callable[[str], list[float]] | None = None) -> list[str]:
    ranks: list[list[int]] = []
    if m := _fts_query(query):
        ranks.append([r[0] for r in con.execute(
            "select rowid from memories_fts where memories_fts match ? order by rank limit ?", (m, limit * 4))])
    if embed and con.execute("select 1 from vault_meta where key = 'embed_dim'").fetchone():
        vec = embed(query)
        if len(vec) == int(con.execute("select value from vault_meta where key = 'embed_dim'").fetchone()[0]):
            ranks.append([r[0] for r in con.execute(
                "select rowid from memories_vec where embedding match ? and k = ?", (sqlite_vec.serialize_float32(vec), limit * 4))])
    score: dict[int, float] = {}
    for lst in ranks:
        for i, mid in enumerate(lst):
            score[mid] = score.get(mid, 0.0) + 1.0 / (RRF_K + i + 1)
    top = sorted(score, key=lambda m: -score[m])[:limit]
    texts = dict(con.execute(f"select id, text from memories where id in ({','.join('?' * len(top))})", top)) if top else {}
    return [texts[m] for m in top if m in texts]
