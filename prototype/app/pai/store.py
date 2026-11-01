"""SQLite storage with versioned, additive-only migrations (index = version - 1)."""
import sqlcipher3 as sqlcipher
import sqlite_vec

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
    # v3: small key/value table; records the embedding dimension once the first vector is stored
    "create table vault_meta (key text primary key, value text not null);",
]
SCHEMA_VERSION = len(MIGRATIONS)


class SchemaTooNew(Exception):
    """The database file was written by a newer PAI than this one."""


class VaultKeyError(Exception):
    """The vault is encrypted and the key is missing or wrong."""


def connect(path: str, key: str | None = None, migrations: list[str] | None = None):
    migrations = MIGRATIONS if migrations is None else migrations  # the audit db passes its own list
    latest = len(migrations)
    con = sqlcipher.connect(path)
    try:
        if key is not None:
            con.execute("pragma key = '" + key.replace("'", "''") + "'")  # quoted, never logged
        try:
            con.execute("select count(*) from sqlite_master").fetchone()  # probe: fails if the key is wrong or missing
        except sqlcipher.DatabaseError as e:
            # only SQLCipher's "not a database" means key problem; locks, I/O and other errors propagate unchanged
            if isinstance(e, sqlcipher.OperationalError) or "file is not a database" not in str(e):
                raise
            raise VaultKeyError("vault key is missing or wrong (file is not a database)") from e
        con.execute("pragma secure_delete = on")  # deleted text is overwritten in freed pages
        con.enable_load_extension(True)
        sqlite_vec.load(con)
        con.enable_load_extension(False)
        version = con.execute("pragma user_version").fetchone()[0]
        if version > latest:
            raise SchemaTooNew(f"database schema v{version} is newer than this app (v{latest})")
        for v in range(version, latest):
            # DDL and user_version are transactional in SQLite: a failed migration rolls back whole and is retried next start
            try:
                con.executescript(f"begin;\n{migrations[v]}\npragma user_version = {v + 1};\ncommit;")
            except Exception:
                con.rollback()
                raise
    except BaseException:
        con.close()
        raise
    return con
