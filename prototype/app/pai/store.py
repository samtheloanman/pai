"""SQLite storage with versioned, additive-only migrations (index = version - 1)."""
import sqlite3

MIGRATIONS: list[str] = [
    # v1: the prototype schema
    """
    create table if not exists profile (key text primary key, value text not null);
    create table if not exists memories (id integer primary key, text text not null, created text default current_timestamp);
    create table if not exists rules (id integer primary key check (id = 1), text text not null);
    """,
    # v2: full-text index over memories, kept in sync by triggers, backfilled from existing rows
    """
    create virtual table memories_fts using fts5(text, content='memories', content_rowid='id');
    insert into memories_fts (rowid, text) select id, text from memories;
    create trigger memories_ai after insert on memories begin
        insert into memories_fts (rowid, text) values (new.id, new.text);
    end;
    create trigger memories_ad after delete on memories begin
        insert into memories_fts (memories_fts, rowid, text) values ('delete', old.id, old.text);
    end;
    create trigger memories_au after update on memories begin
        insert into memories_fts (memories_fts, rowid, text) values ('delete', old.id, old.text);
        insert into memories_fts (rowid, text) values (new.id, new.text);
    end;
    """,
]
SCHEMA_VERSION = len(MIGRATIONS)


class SchemaTooNew(Exception):
    """The database file was written by a newer PAI than this one."""


def connect(path: str, key: str | None = None) -> sqlite3.Connection:  # key is accepted but ignored until SQLCipher lands (Task 2)
    con = sqlite3.connect(path)
    version = con.execute("pragma user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        con.close()
        raise SchemaTooNew(f"database schema v{version} is newer than this app (v{SCHEMA_VERSION})")
    for v in range(version, SCHEMA_VERSION):
        # executescript commits first; user_version is set after each step so a crash resumes at the failed one
        con.executescript(MIGRATIONS[v])
        con.execute(f"pragma user_version = {v + 1}")
    return con
