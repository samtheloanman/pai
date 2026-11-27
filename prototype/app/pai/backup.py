"""Backup, restore, export and import for the PAI vault.

    python -m pai.backup create  <dir>        encrypted snapshot of the vault and audit log -> one .tar file
    python -m pai.backup verify  <file.tar>   opens it with the current key and checks the audit chain
    python -m pai.backup restore <file.tar>   puts a snapshot back (stop the app first); keeps the old files aside
    python -m pai.backup export  <file.json>  your profile, rules and memories as readable JSON (NOT encrypted)
    python -m pai.backup import  <file.json>  adds those back into this vault; existing entries are kept

A backup is useless without the vault key and the key is never inside the backup. Keep them in different places.
Snapshots use SQLite's online backup, so `create` is safe while the app runs.
"""
import argparse
import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
import time
from contextlib import closing

from pai import store, vault, vaultkey

FILES = ("pai.db", "audit.db")
FORMAT = 1
EXPORT_TABLES = ("profile", "rules", "memories")  # login data, devices and pending actions are never exported


def _data_dir() -> str:
    return os.environ.get("DATA_DIR", "/data")


def _open(path: str, migrations=None):
    return store.connect(path, key=vaultkey.get(), migrations=migrations)


def _audit_migrations():
    from pai import audit
    return audit.MIGRATIONS


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _snapshot(src: str, dst: str) -> None:
    """Online copy that stays encrypted with the same key."""
    key = vaultkey.get().replace("'", "''")
    import sqlcipher3 as sqlcipher
    with closing(sqlcipher.connect(src)) as a, closing(sqlcipher.connect(dst)) as b:
        a.execute(f"pragma key = '{key}'")
        b.execute(f"pragma key = '{key}'")
        a.backup(b)


def create(out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = os.path.join(out_dir, f"pai-backup-{stamp}.tar")
    with tempfile.TemporaryDirectory(dir=out_dir) as tmp:
        manifest = {"format": FORMAT, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "schema_version": store.SCHEMA_VERSION, "files": {}}
        for name in FILES:
            src = os.path.join(_data_dir(), name)
            if not os.path.exists(src):
                continue
            _snapshot(src, os.path.join(tmp, name))
            manifest["files"][name] = _sha256(os.path.join(tmp, name))
        if "pai.db" not in manifest["files"]:
            raise SystemExit(f"no vault at {_data_dir()}/pai.db")
        fd, part = tempfile.mkstemp(dir=out_dir, suffix=".part")
        os.close(fd)
        with tarfile.open(part, "w") as t:
            data = json.dumps(manifest, indent=2).encode()
            info = tarfile.TarInfo("manifest.json"); info.size = len(data); info.mtime = int(time.time())
            t.addfile(info, io.BytesIO(data))
            for name in manifest["files"]:
                t.add(os.path.join(tmp, name), arcname=name)
        os.chmod(part, 0o600)
        os.replace(part, out)
    return out


def _extract(path: str, into: str) -> dict:
    """Only the expected plain files; no links, no paths."""
    with tarfile.open(path) as t:
        members = {m.name: m for m in t.getmembers()}
        if set(members) - {"manifest.json", *FILES} or "manifest.json" not in members:
            raise SystemExit("not a PAI backup (unexpected contents)")
        for m in members.values():
            if not m.isfile():
                raise SystemExit("not a PAI backup (unexpected entry type)")
            with t.extractfile(m) as src, open(os.path.join(into, m.name), "wb") as dst:
                dst.write(src.read())
    with open(os.path.join(into, "manifest.json")) as f:
        manifest = json.load(f)
    for name, digest in manifest.get("files", {}).items():
        if name not in FILES or _sha256(os.path.join(into, name)) != digest:
            raise SystemExit(f"backup is damaged: {name} does not match its checksum")
    return manifest


def _check(folder: str, manifest: dict) -> dict:
    if manifest.get("format") != FORMAT:
        raise SystemExit(f"unknown backup format {manifest.get('format')}")
    if manifest.get("schema_version", 0) > store.SCHEMA_VERSION:
        raise SystemExit("this backup comes from a newer PAI; update PAI before restoring it")
    try:
        with closing(_open(os.path.join(folder, "pai.db"))) as con:
            memories = con.execute("select count(*) from memories").fetchone()[0]
    except store.VaultKeyError:
        raise SystemExit("the current vault key does not open this backup") from None
    audit_ok = None
    if "audit.db" in manifest["files"]:
        saved = os.environ.get("DATA_DIR")
        os.environ["DATA_DIR"] = folder
        try:
            from pai import audit
            audit_ok = audit.verify() is None
        finally:
            if saved is None:
                os.environ.pop("DATA_DIR", None)
            else:
                os.environ["DATA_DIR"] = saved
    return {"created": manifest["created"], "memories": memories, "audit_chain_ok": audit_ok}


def verify(path: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        return _check(tmp, _extract(path, tmp))


def restore(path: str) -> str:
    """Returns the folder the replaced files were moved to. Nothing is deleted."""
    data = _data_dir()
    with tempfile.TemporaryDirectory(dir=data) as tmp:
        manifest = _extract(path, tmp)
        _check(tmp, manifest)
        aside = os.path.join(data, f"pre-restore-{time.strftime('%Y%m%d-%H%M%S')}")
        os.makedirs(aside)
        for name in FILES:
            for suffix in ("", "-wal", "-shm"):
                cur = os.path.join(data, name + suffix)
                if os.path.exists(cur):
                    os.replace(cur, os.path.join(aside, name + suffix))
            if name in manifest["files"]:
                os.replace(os.path.join(tmp, name), os.path.join(data, name))
    return aside


def export_json(out: str) -> dict:
    with closing(_open(os.path.join(_data_dir(), "pai.db"))) as con:
        doc = {"format": FORMAT, "kind": "pai-export",
               "exported": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "profile": dict(con.execute("select key, value from profile")),
               "rules": (con.execute("select text from rules where id = 1").fetchone() or [""])[0],
               "memories": [{"text": t, "created": c} for t, c in con.execute("select text, created from memories order by id")]}
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    return {"profile": len(doc["profile"]), "memories": len(doc["memories"]), "rules": bool(doc["rules"])}


def import_json(path: str, replace: bool = False) -> dict:
    with open(path) as f:
        doc = json.load(f)
    if doc.get("kind") != "pai-export" or doc.get("format") != FORMAT:
        raise SystemExit("not a PAI export file")
    added = {"memories": 0, "profile": 0, "rules": False}
    with closing(_open(os.path.join(_data_dir(), "pai.db"))) as con:
        have = {t for (t,) in con.execute("select text from memories")}
        for m in doc.get("memories", []):
            text = str(m.get("text", "")).strip()
            if text and text not in have:
                vault.add_memory(con, text)
                have.add(text)
                added["memories"] += 1
        with con:
            for k, v in doc.get("profile", {}).items():
                verb = "insert or replace" if replace else "insert or ignore"
                added["profile"] += con.execute(f"{verb} into profile (key, value) values (?, ?)", (str(k), str(v))).rowcount
            rules = str(doc.get("rules") or "")
            current = (con.execute("select text from rules where id = 1").fetchone() or [""])[0]
            if rules and (replace or not current):
                con.execute("insert or replace into rules (id, text) values (1, ?)", (rules,))
                added["rules"] = True
    return added


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m pai.backup", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, arg in (("create", "dir"), ("verify", "file"), ("restore", "file"), ("export", "file"), ("import", "file")):
        sp = sub.add_parser(name)
        sp.add_argument(arg)
        if name == "import":
            sp.add_argument("--replace", action="store_true", help="overwrite profile answers and rules that already exist")
        if name == "restore":
            sp.add_argument("--yes", action="store_true", help="confirm the app is stopped")
    a = p.parse_args(argv)
    if a.cmd == "create":
        print(create(a.dir))
    elif a.cmd == "verify":
        print(json.dumps(verify(a.file)))
    elif a.cmd == "restore":
        if not a.yes:
            print("Stop the app first (docker compose stop app), then run again with --yes.", file=sys.stderr)
            return 2
        print(f"restored; the replaced files are in {restore(a.file)}")
    elif a.cmd == "export":
        print(json.dumps(export_json(a.file)))
        print("This file is NOT encrypted. Keep it private or delete it after use.", file=sys.stderr)
    else:
        print(json.dumps(import_json(a.file, a.replace)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
