"""scripts/pai-up: the vault key lives outside .env and reaches compose only through the shell that runs it.

Runs the real script against a copy of the prototype layout, with stub `docker`, `uname` and `systemd-creds`,
so nothing touches Docker, the Keychain or the real ~/.config/pai.
"""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

PAI_UP = Path(__file__).resolve().parents[2] / "scripts" / "pai-up"

FAKE_DOCKER = """#!/bin/sh
printf '%s\\n' "${PAI_VAULT_KEY:-}" > "$FAKE_OUT/key"
printf '%s\\n' "$*" > "$FAKE_OUT/args"
"""
# Mimics systemd 255 as a normal user: --user is unknown, only the TPM flavour works. "Encryption" is a marker prefix.
FAKE_CREDS = """#!/bin/sh
[ "$1" = --with-key=tpm2 ] || exit 1
shift
case "$1" in
  encrypt) { printf 'SEALED:'; cat; } > "$4" ;;
  decrypt) sed 's/^SEALED://' "$3" ;;
  *) exit 1 ;;
esac
"""
BROKEN_CREDS = "#!/bin/sh\nexit 1\n"


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "proto"
    (root / "scripts").mkdir(parents=True)
    shutil.copy(PAI_UP, root / "scripts" / "pai-up")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for name, body in {"docker": FAKE_DOCKER, "uname": "#!/bin/sh\necho Linux\n", "systemd-creds": BROKEN_CREDS}.items():
        (bin_ / name).write_text(body)
        (bin_ / name).chmod(0o755)
    out = tmp_path / "out"
    out.mkdir()
    e = {"PATH": f"{bin_}:/usr/bin:/bin", "HOME": str(tmp_path / "home"), "FAKE_OUT": str(out)}
    return root, bin_, out, e


def run(root, e, *args, stdin=None):
    return subprocess.run([str(root / "scripts" / "pai-up"), *args], env=e, input=stdin,
                          capture_output=True, text=True, cwd=root)


def keyfile(e):
    return Path(e["HOME"]) / ".config" / "pai" / "vault-key"


def test_new_key_falls_back_to_0600_file_outside_env(env):
    root, _, out, e = env
    r = run(root, e, "new-key")
    assert r.returncode == 0, r.stderr
    kf = keyfile(e)
    assert stat.S_IMODE(kf.stat().st_mode) == 0o600
    assert stat.S_IMODE(kf.parent.stat().st_mode) == 0o700
    key = kf.read_text().strip()
    assert len(key) == 64
    assert not (root / ".env").exists()
    assert key not in r.stdout + r.stderr  # never printed

    r = run(root, e, "--profile", "local", "up", "-d")
    assert r.returncode == 0, r.stderr
    assert (out / "key").read_text().strip() == key
    assert (out / "args").read_text().strip() == "compose --profile local up -d"


def test_new_key_refuses_to_replace(env):
    root, _, _, e = env
    assert run(root, e, "new-key").returncode == 0
    before = keyfile(e).read_text()
    r = run(root, e, "new-key")
    assert r.returncode == 1 and "refusing" in r.stderr
    assert keyfile(e).read_text() == before


def test_systemd_creds_preferred_when_it_works(env):
    root, bin_, out, e = env
    (bin_ / "systemd-creds").write_text(FAKE_CREDS)
    assert run(root, e, "new-key").returncode == 0
    cred = keyfile(e).with_name("vault-key.cred")
    assert cred.read_text().startswith("SEALED:")
    assert stat.S_IMODE(cred.stat().st_mode) == 0o600
    assert not keyfile(e).exists()
    assert run(root, e, "up").returncode == 0
    assert (out / "key").read_text().strip() == cred.read_text().removeprefix("SEALED:")


def test_migrate_moves_key_out_of_env(env):
    root, _, out, e = env
    (root / ".env").write_text("LITELLM_MASTER_KEY=sk-x\nPAI_VAULT_KEY=abc123\nMODEL_HF=m\n")
    r = run(root, e, "migrate-key")
    assert r.returncode == 0, r.stderr
    assert "removed the line" in r.stdout
    assert (root / ".env").read_text() == "LITELLM_MASTER_KEY=sk-x\nMODEL_HF=m\n"
    assert keyfile(e).read_text().strip() == "abc123"  # same key, so the existing vault still opens
    assert run(root, e, "up").returncode == 0
    assert (out / "key").read_text().strip() == "abc123"
    assert run(root, e, "migrate-key").returncode == 0  # idempotent


def test_migrate_refuses_when_keys_differ(env):
    root, _, _, e = env
    assert run(root, e, "import-key", stdin="stored\n").returncode == 0
    (root / ".env").write_text("PAI_VAULT_KEY=other\n")
    r = run(root, e, "migrate-key")
    assert r.returncode == 1 and "differs" in r.stderr
    assert (root / ".env").read_text() == "PAI_VAULT_KEY=other\n"
    assert keyfile(e).read_text().strip() == "stored"


def test_legacy_env_key_still_starts_with_warning(env):
    root, _, out, e = env
    (root / ".env").write_text("PAI_VAULT_KEY=legacy\n")
    r = run(root, e, "up")
    assert r.returncode == 0 and "migrate-key" in r.stderr
    assert (out / "key").read_text().strip() == "legacy"


def test_no_key_anywhere_fails(env):
    root, _, out, e = env
    r = run(root, e, "up")
    assert r.returncode == 1 and "new-key" in r.stderr
    assert not (out / "args").exists()
