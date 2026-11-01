import json
import os
import stat

import pytest
import yaml
from contextlib import closing

import main
from pai import audit, blocks, providers, store
from pai.routing import Route

CHAT = Route("chat", 2, .9)
WARNING = "Cloud models see what you send. Free tiers may log prompts. Names and secrets are blocked or kept on this box."


def test_migration_adds_tables_additively(vault):
    with closing(main.db()) as con:
        assert con.execute("pragma user_version").fetchone()[0] == store.SCHEMA_VERSION
        for t in ("providers", "settings"):
            assert con.execute("select count(*) from sqlite_master where name = ?", (t,)).fetchone()[0] == 1


def test_key_without_switch_stays_local(vault):
    providers.save_key("openrouter", "sk-or-test")
    assert providers.choose_model("hello", CHAT, want_cloud=True) == "pai-chat"


def test_switch_and_key_but_not_requested_stays_local(vault):
    providers.save_key("openrouter", "sk-or-test"); providers.set_cloud_enabled(True)
    assert providers.choose_model("hello", CHAT) == "pai-chat"


def test_switch_without_key_stays_local(vault):
    providers.set_cloud_enabled(True)
    assert providers.choose_model("hello", CHAT, want_cloud=True) == "pai-chat"


def test_all_conditions_choose_cloud_and_block_overrides(vault):
    providers.save_key("openrouter", "sk-or-test"); providers.set_cloud_enabled(True)
    assert providers.choose_model("hello", CHAT, want_cloud=True) == "pai-cloud"
    assert providers.choose_model("card 4111 1111 1111 1111", CHAT, want_cloud=True) == "pai-chat"


def test_off_limits_from_interview_blocks(vault):
    vault.post("/api/interview", json={"key": "off_limits", "value": "my divorce; health, taxes\nkids"})
    providers.save_key("openrouter", "sk-or-test"); providers.set_cloud_enabled(True)
    assert providers.choose_model("help with my Divorce", CHAT, want_cloud=True) == "pai-chat"
    assert providers.choose_model("about taxes", CHAT, want_cloud=True) == "pai-chat"
    assert providers.choose_model("write a poem", CHAT, want_cloud=True) == "pai-cloud"


def test_rendered_config_has_only_keyed_providers(vault):
    providers.save_key("nvidia", "nvapi-test")
    text = providers.render_litellm_config()
    cfg = yaml.safe_load(text)
    names = {m["litellm_params"]["model"].split("/")[0] for m in cfg["model_list"]}
    assert "nvidia_nim" in names and "openrouter" not in names
    assert "nvapi-test" not in text
    assert "os.environ/PAI_KEY_NVIDIA" in text


def test_config_keeps_base_models_and_picks_first_cloud(vault):
    providers.save_key("huggingface", "hf_x"); providers.save_key("openrouter", "k1")
    cfg = yaml.safe_load(providers.render_litellm_config())
    got = [m["model_name"] for m in cfg["model_list"]]
    assert got[:4] == ["pai-chat", "pai-decide", "pai-stt", "pai-tts"]
    cloud = [m for m in cfg["model_list"] if m["model_name"] == "pai-cloud"]
    assert len(cloud) == 1 and cloud[0]["litellm_params"]["model"].startswith("openrouter/")
    assert cfg["litellm_settings"] == {"telemetry": False}
    assert providers.cloud_provider() == "openrouter"


def test_no_keys_no_cloud_alias(vault):
    cfg = yaml.safe_load(providers.render_litellm_config())
    assert "pai-cloud" not in [m["model_name"] for m in cfg["model_list"]]


def test_env_render_quotes_values(vault):
    providers.save_key("openrouter", "ab'c$d")
    assert providers.render_env() == "PAI_KEY_OPENROUTER='ab'\"'\"'c$d'\n"


def test_custom_model_used(vault):
    providers.save_key("nvidia", "k"); providers.save_model("nvidia", "nvidia_nim/other/model")
    cfg = yaml.safe_load(providers.render_litellm_config())
    assert [m for m in cfg["model_list"] if m["model_name"] == "pai-cloud"][0]["litellm_params"]["model"] == "nvidia_nim/other/model"


def test_api_never_returns_key_and_writes_files(vault, tmp_path):
    r = vault.put("/api/providers", json={"name": "openrouter", "key": "sk-or-SECRET123"})
    assert r.status_code == 200 and r.json()["restart_required"] is True
    assert vault.put("/api/providers/cloud", json={"enabled": True}).json()["restart_required"] is True
    g = vault.get("/api/providers")
    assert "SECRET123" not in g.text and g.json()["warning"] == WARNING and g.json()["cloud_enabled"] is True
    row = [p for p in g.json()["providers"] if p["name"] == "openrouter"][0]
    assert row == {"name": "openrouter", "has_key": True, "model": None, "cloud": True} or row["has_key"] is True
    shared = tmp_path / "shared"
    env = shared / "litellm.env"
    assert "PAI_KEY_OPENROUTER" in env.read_text()
    assert stat.S_IMODE(env.stat().st_mode) == 0o600
    assert "SECRET123" not in (shared / "litellm.generated.yaml").read_text()
    names = {p["name"]: p["cloud"] for p in g.json()["providers"]}
    assert names["ollama"] is False and names["openrouter"] is True


def test_api_validation(vault):
    assert vault.put("/api/providers", json={"name": "nope", "key": "x"}).status_code == 400
    for bad in ("a b", "a\nb", "x" * 513):
        assert vault.put("/api/providers", json={"name": "openrouter", "key": bad}).status_code == 400
    assert vault.put("/api/providers", json={"name": "openrouter", "key": "  trimmed  "}).status_code == 200
    assert vault.put("/api/providers", json={"name": "openrouter", "key": ""}).status_code == 200
    assert vault.get("/api/providers").json()["providers"][0]["has_key"] is False


def test_model_change_alone_keeps_key(vault):
    vault.put("/api/providers", json={"name": "nvidia", "key": "k1"})
    vault.put("/api/providers", json={"name": "nvidia", "model": "nvidia_nim/x/y"})
    row = [p for p in vault.get("/api/providers").json()["providers"] if p["name"] == "nvidia"][0]
    assert row["has_key"] and row["model"] == "nvidia_nim/x/y"


def test_config_changed_audit_has_no_key_or_model(vault):
    vault.put("/api/providers", json={"name": "openrouter", "key": "sk-or-SECRET123", "model": "openrouter/secret/model"})
    vault.put("/api/providers", json={"name": "openrouter", "key": ""})
    vault.put("/api/providers/cloud", json={"enabled": True})
    vault.put("/api/providers/cloud", json={"enabled": False})
    entries = [e for e in vault.get("/api/activity?limit=50").json() if e["kind"] == "config_changed"]
    blob = json.dumps(entries)
    assert "SECRET123" not in blob and "secret/model" not in blob
    acts = [e["fields"]["action"] for e in entries if e["fields"].get("what") == "providers"]
    assert {"key_set", "model_set", "key_removed", "cloud_on", "cloud_off"} <= set(acts)


def test_files_written_only_when_changed(vault, tmp_path):
    vault.put("/api/providers", json={"name": "openrouter", "key": "k"})
    p = tmp_path / "shared" / "litellm.generated.yaml"
    m = p.stat().st_mtime_ns
    vault.put("/api/providers", json={"name": "openrouter", "key": "k"})
    assert p.stat().st_mtime_ns == m


SENT = ("PROFILE-SENTINEL", "RULE-SENTINEL", "MEMORY-SENTINEL")


def _setup_cloud(vault):
    vault.post("/api/interview", json={"key": "name", "value": "PROFILE-SENTINEL"})
    vault.put("/api/rules", json={"text": "RULE-SENTINEL"})
    main.add_memory("MEMORY-SENTINEL favourite colour is teal")
    vault.put("/api/providers", json={"name": "openrouter", "key": "k"})
    vault.put("/api/providers/cloud", json={"enabled": True})


def test_cloud_payload_has_no_owner_context_and_is_audited(vault, mock_litellm):
    _setup_cloud(vault)
    r = vault.post("/api/chat", json={"message": "what is my favourite colour teal", "history": [{"role": "user", "content": "hi"}], "cloud": True})
    assert r.status_code == 200
    url, kw = [c for c in mock_litellm.calls if kw_model(c) == "pai-cloud"][0]
    sent = json.dumps(kw["json"])
    assert not any(s in sent for s in SENT)
    assert kw["json"]["messages"][0]["content"] == providers.CLOUD_SYSTEM
    ev = vault.get("/api/activity?limit=50").json()
    out = [e for e in ev if e["kind"] == "outbound"]
    assert out and out[0]["fields"]["pai.provider"] == "openrouter" and out[0]["fields"]["pai.masked_fields"] == 0
    assert "teal" not in json.dumps(out)


def kw_model(call):
    return call[1].get("json", {}).get("model")


def test_blocked_history_keeps_everything_local(vault, mock_litellm):
    _setup_cloud(vault)
    r = vault.post("/api/chat", json={"message": "hello", "history": [{"role": "user", "content": "card 4111 1111 1111 1111"}], "cloud": True})
    assert r.status_code == 200 and r.json()["reply"].startswith("I kept that on this box: card number")
    assert all(kw_model(c) != "pai-cloud" for c in mock_litellm.calls)
    assert not [e for e in vault.get("/api/activity?limit=50").json() if e["kind"] == "outbound"]


def test_cloud_not_used_unless_requested(vault, mock_litellm):
    _setup_cloud(vault)
    vault.post("/api/chat", json={"message": "write a poem"})
    assert all(kw_model(c) != "pai-cloud" for c in mock_litellm.calls)


def test_outbound_audit_failure_sends_nothing(vault, mock_litellm, monkeypatch):
    _setup_cloud(vault)
    real = audit.record
    def boom(kind, /, **f):
        if kind == "outbound":
            raise RuntimeError("down")
        return real(kind, **f)
    monkeypatch.setattr(audit, "record", boom)
    r = vault.post("/api/chat", json={"message": "write a poem", "cloud": True})
    assert r.status_code == 500 and r.json()["detail"] == "audit log unavailable"
    assert all(kw_model(c) != "pai-cloud" for c in mock_litellm.calls)
