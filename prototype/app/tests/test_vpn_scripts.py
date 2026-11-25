"""The private-network scripts: what the setup script may never do, and that the verify script fails loudly."""
import json
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

PROTO = Path(__file__).resolve().parents[2]
SETUP = PROTO / "setup-pai-vpn-gateway.sh"
VERIFY = PROTO / "verify-vpn-tunnel.sh"
DOCS = PROTO.parent / "docs"


def code_lines(path):
    return "\n".join(l for l in path.read_text().splitlines() if not l.lstrip().startswith("#"))


def test_setup_never_routes_the_lan_or_opens_ssh_or_pipes_a_download_into_a_shell():
    code = code_lines(SETUP)
    for banned in ("--advertise-exit-node", "--advertise-routes", "--ssh", "ip_forward = 1", "ip_forward=1"):
        assert banned not in code, banned
    assert not re.search(r"-[AI]\s+(POSTROUTING|FORWARD)", code), "must not add NAT or forwarding rules"
    assert not re.search(r"curl[^\n|]*\|\s*(sudo\s+)?(ba)?sh", code), "no curl | sh"
    assert not re.search(r"funnel\s+(?!reset)", code), "never publish to the internet"


@pytest.mark.parametrize("path", [SETUP, VERIFY, DOCS / "PAI-MESH-VPN-SETUP.md"], ids=lambda p: p.name)
def test_no_private_network_address_is_hardcoded(path):
    # 100.64.0.0/10 is the carrier-grade NAT range Tailscale assigns from: a real one identifies someone's machine
    found = re.findall(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b(?!/)", path.read_text())
    assert not found, found


def run(script, *args, env=None, path_dir=None):
    e = {"PATH": f"{path_dir}:/usr/local/bin:/usr/bin:/bin" if path_dir else "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp", **(env or {})}
    return subprocess.run(["bash", str(script), *args], capture_output=True, text=True, env=e, timeout=30)


def test_setup_dry_run_joins_with_safe_flags_and_keeps_the_key_off_the_command_line(tmp_path):
    stub(tmp_path, "tailscale", "exit 0")
    r = run(SETUP, "up", "--dry-run", env={"TS_AUTHKEY": "tskey-auth-SECRET"}, path_dir=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "tailscale up --reset" in r.stdout and "--accept-routes=false" in r.stdout
    assert "tskey-auth-SECRET" not in r.stdout + r.stderr
    assert "--auth-key file:" in r.stdout


def test_setup_dry_run_uses_the_headscale_server_when_given(tmp_path):
    stub(tmp_path, "tailscale", "exit 0")
    r = run(SETUP, "up", "--dry-run", env={"PAI_LOGIN_SERVER": "https://hs.example.org"}, path_dir=tmp_path)
    assert "--login-server https://hs.example.org" in r.stdout


def test_setup_dry_run_serve_publishes_loopback_over_https_and_resets_funnel(tmp_path):
    stub(tmp_path, "tailscale", "exit 0")
    r = run(SETUP, "serve", "--dry-run", path_dir=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "tailscale funnel reset" in r.stdout
    assert "tailscale serve --bg --https=443 http://127.0.0.1:8088" in r.stdout


def test_setup_rejects_a_hostile_port_or_hostname(tmp_path):
    assert run(SETUP, "serve", "--dry-run", env={"PAI_PORT": "8088; rm -rf /"}).returncode == 2
    assert run(SETUP, "up", "--dry-run", env={"PAI_HOSTNAME": "a b"}).returncode == 2


def stub(d, name, body):
    p = d / name
    p.write_text("#!/bin/bash\n" + body + "\n")
    p.chmod(p.stat().st_mode | stat.S_IXUSR)


def verify_env(tmp_path, *, state="Running", routes=(), ssh=False, funnel=False, listen="127.0.0.1:8088",
               health="200", memories="401", serve_target="http://127.0.0.1:8088"):
    status = {"BackendState": state, "Self": {"DNSName": "pai.example.ts.net."}}
    prefs = {"AdvertiseRoutes": list(routes), "RunSSH": ssh}
    fun = {"AllowFunnel": {"pai.example.ts.net:443": True}} if funnel else {}
    serve = {"Web": {"pai.example.ts.net:443": {"Handlers": {"/": {"Proxy": serve_target}}}}} if serve_target else {}
    stub(tmp_path, "tailscale", f"""case "$1 $2" in
  "status --json") echo '{json.dumps(status)}' ;;
  "debug prefs") echo '{json.dumps(prefs)}' ;;
  "funnel status") echo '{json.dumps(fun)}' ;;
  "serve status") echo '{json.dumps(serve)}' ;;
  "ping "*) exit 0 ;;
esac""")
    stub(tmp_path, "ss", f"echo 'LISTEN 0 4096 {listen} 0.0.0.0:*'")
    stub(tmp_path, "curl", f"""for a in "$@"; do u="$a"; done
case "$u" in */api/memories) printf '{memories}' ;; *) printf '{health}' ;; esac""")
    return tmp_path


def test_verify_passes_on_a_correct_box(tmp_path):
    r = run(VERIFY, path_dir=verify_env(tmp_path))
    assert r.returncode == 0, r.stdout
    assert "[FAIL]" not in r.stdout and "All checks passed." in r.stdout


@pytest.mark.parametrize("bad,needle", [
    ({"state": "Stopped"}, "not connected"),
    ({"routes": ["0.0.0.0/0", "::/0"]}, "advertising 2 route"),
    ({"routes": ["192.168.50.0/24"]}, "advertising 1 route"),
    ({"ssh": True}, "Tailscale SSH is on"),
    ({"funnel": True}, "Funnel is on"),
    ({"listen": "0.0.0.0:8088"}, "is open on"),
    ({"health": "000"}, "does not answer"),
    ({"serve_target": "http://127.0.0.1:22"}, "something other than the PAI app"),
    ({"memories": "200"}, "published but has no login"),
], ids=lambda v: v if isinstance(v, str) else None)
def test_verify_exits_non_zero_when_a_check_fails(tmp_path, bad, needle):
    r = run(VERIFY, path_dir=verify_env(tmp_path, **bad))
    assert r.returncode == 1, r.stdout
    assert needle in r.stdout


def test_verify_allows_no_login_only_while_unpublished(tmp_path):
    r = run(VERIFY, path_dir=verify_env(tmp_path, memories="200", serve_target=None))
    assert r.returncode == 0, r.stdout
    assert "[SKIP]" in r.stdout


def test_verify_fails_when_a_required_tool_is_missing(tmp_path):
    r = run(VERIFY, path_dir=tmp_path)
    assert r.returncode == 1 and "required" in r.stdout
