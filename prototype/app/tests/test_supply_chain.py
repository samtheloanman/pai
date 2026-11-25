"""Supply-chain and exposure lint for the Compose files, the Dockerfile and the helper scripts.

LiteLLM's floating tags (latest, main-latest, main-stable) pointed at a malicious image on 2026-10-21
(https://docs.litellm.ai/blog/security-incident-oct-21-2026). Every image is pinned by digest so a moved
tag cannot change what runs.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = [ROOT / "docker-compose.yml", ROOT / "prototype" / "docker-compose.yml"]
DOCKERFILES = [ROOT / "prototype" / "app" / "Dockerfile"]
SCRIPTS = [ROOT / "run.sh", ROOT / "prototype" / "setup.sh", ROOT / "prototype" / "scripts" / "install.sh",
           ROOT / "prototype" / "app" / "run-tests.sh", ROOT / "prototype" / "app" / "run-e2e.sh"]
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
# Digest LiteLLM published as the compromised ghcr.io/berriai/litellm index.
COMPROMISED = "1bbcb1443bc962e45f5aad53fe3d2c30600e0379715fb6c664cdd3ac126c339e"
# An image reference inside a shell script: a registry path, or a bare official image with a tag.
SCRIPT_IMAGE = re.compile(r"(?<![\w./-])((?:ghcr\.io|docker\.io|gcr\.io|quay\.io)/[\w./-]+(?::[\w.-]+)?|(?:alpine|python|node|ubuntu|debian):[\w.-]+)(@sha256:[0-9a-f]+)?")


def services(path):
    return (yaml.safe_load(path.read_text()) or {}).get("services", {})


@pytest.mark.parametrize("path", COMPOSE, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_compose_image_is_pinned_by_digest(path):
    unpinned = {n: s["image"] for n, s in services(path).items() if "image" in s and not DIGEST.search(s["image"])}
    assert not unpinned, f"pin by digest (image:tag@sha256:...): {unpinned}"


@pytest.mark.parametrize("path", DOCKERFILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_dockerfile_base_is_pinned_by_digest(path):
    stages, unpinned = set(), []
    for line in path.read_text().splitlines():
        m = re.match(r"\s*FROM\s+(\S+)(?:\s+AS\s+(\S+))?", line, re.I)
        if not m:
            continue
        if m.group(1) not in stages and not DIGEST.search(m.group(1)):
            unpinned.append(m.group(1))
        if m.group(2):
            stages.add(m.group(2))
    assert not unpinned, f"pin base images by digest: {unpinned}"


@pytest.mark.parametrize("path", [p for p in SCRIPTS if p.exists()], ids=lambda p: str(p.relative_to(ROOT)))
def test_scripts_run_only_pinned_images(path):
    text = path.read_text()
    unpinned = [m.group(1) for m in SCRIPT_IMAGE.finditer(text) if not m.group(2)]
    assert not unpinned, f"pin by digest: {unpinned}"
    assert not re.search(r"\b(?:run|-v \S+)\s+alpine\s", text), "bare 'alpine' image: pin it by digest"


def test_no_file_references_the_compromised_litellm_digest_or_a_floating_litellm_tag():
    for path in COMPOSE + [ROOT / "prototype" / "README.md", ROOT / "INSTALL.md"]:
        text = path.read_text()
        assert COMPROMISED not in text, path
        assert not re.search(r"litellm:(latest|main-latest|main-stable)(?!\S*@sha256)", text), path


@pytest.mark.parametrize("path", COMPOSE, ids=lambda p: str(p.relative_to(ROOT)))
def test_published_ports_bind_to_loopback_only(path):
    exposed = {n: p for n, s in services(path).items() for p in s.get("ports", []) if not str(p).startswith("127.0.0.1:")}
    assert not exposed, f"bind to 127.0.0.1 so nothing listens on the LAN: {exposed}"


@pytest.mark.parametrize("path", COMPOSE, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_default_vault_key_is_committed(path):
    assert not re.search(r"PAI_VAULT_KEY[^\n]*:-[0-9a-fA-F]{16,}", path.read_text()), \
        "a default vault key in a public repo protects nothing: require the owner's key"


def test_litellm_has_no_route_out_except_the_allowlist_proxy():
    cfg = yaml.safe_load(COMPOSE[1].read_text())
    lite = cfg["services"]["litellm"]
    assert lite.get("networks") == ["internal"], "litellm must sit only on the internal network"
    assert cfg["networks"]["internal"].get("internal") is True
    env = lite["environment"]
    assert env["HTTPS_PROXY"] == env["HTTP_PROXY"] == "http://egress:3128"
    assert {"llm", "speaches"} <= set(env["NO_PROXY"].split(","))
    egress = cfg["services"]["egress"]
    assert "internal" in egress["networks"] and len(egress["networks"]) == 2
    assert "ports" not in egress, "the proxy is for litellm only; never publish it"


def test_proxy_config_allows_only_the_allowlist():
    conf = (ROOT / "prototype" / "egress" / "squid.conf").read_text()
    rules = [l.split("#")[0].strip() for l in conf.splitlines() if l.strip().startswith("http_access")]
    assert rules[-1] == "http_access deny all"
    assert [r for r in rules if r.startswith("http_access allow")] == ["http_access allow allowed"]
    assert 'acl allowed dstdomain "/run/egress/allow.txt"' in conf
