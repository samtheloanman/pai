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
    # v4: risky actions waiting for the owner's approval (see pai/actions.py)
    """
    create table actions (id text primary key, kind text not null, summary text not null, payload text not null,
                          status text not null, created real not null, expires real not null, result text);
    """,
    # v5: cloud/local provider keys (kept inside the encrypted vault) and small settings
    """
    create table providers (name text primary key, key text, model text, updated real);
    create table settings (key text primary key, value text);
    """,
    # v6: unified onboarding profile, personas, skills/tools, mobile nodes, and ingress connections
    """
    create table if not exists onboarding_profile (
        key text primary key not null,
        value text not null,
        category text not null default 'identity',
        compiled_hash text not null,
        updated_at text not null
    );
    create table if not exists agent_personas (
        persona_id text primary key not null,
        display_name text not null,
        system_prompt text not null,
        loop_mode text not null default 'react',
        preferred_model text not null default 'pai-chat',
        quiet_hours_json text not null default '{"start":"22:00","end":"07:00"}',
        active integer not null default 1
    );
    create table if not exists skills_and_tools (
        skill_id text primary key not null,
        title text not null,
        execution_plane text not null,
        schema_or_md text not null,
        risk_kind text not null default 'none',
        skillspector_score integer not null default 0,
        enabled_by_onboarding integer not null default 0
    );
    create table if not exists mobile_voice_nodes (
        node_id text primary key not null,
        platform text not null,
        tailscale_ip text not null,
        inference_mode text not null default 'hybrid_sse',
        on_device_model text not null default 'Qwen2.5-3B-Instruct-Q4_K_M.gguf',
        audio_aec_profile text not null default 'volocal_hw_aec',
        vad_barge_in_ms integer not null default 40,
        tts_voice text not null default 'af_heart',
        a11y_mcp_scope text not null default 'disabled'
    );
    create table if not exists connections_ingress (
        conn_id text primary key not null,
        conn_type text not null,
        door_plane text not null,
        privacy_tier text not null,
        endpoint_or_model text not null default 'local',
        secret_key text,
        enabled integer not null default 0,
        updated_at real not null
    );
    insert or ignore into onboarding_profile (key, value, category, compiled_hash, updated_at)
    select key, value,
           case when key in ('name','work','people') then 'identity'
                when key in ('off_limits','schedule') then 'boundary'
                when key in ('apps','tone') then 'stack'
                else 'optimization' end,
           key || ':' || value,
           strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    from profile;
    """,
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
