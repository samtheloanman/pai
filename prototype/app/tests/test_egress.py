"""The outbound allowlist LiteLLM's proxy enforces: only hosts the owner has turned on."""
import os

from pai import providers


def hosts():
    return providers.render_egress_allowlist().split()


def test_nothing_is_allowed_out_by_default(vault):
    assert hosts() == []


def test_a_stored_key_alone_allows_nothing(vault):
    providers.save_key("openrouter", "sk-or-test")
    assert hosts() == []


def test_cloud_on_allows_only_the_providers_that_have_a_key(vault):
    providers.save_key("openrouter", "sk-or-test"); providers.set_cloud_enabled(True)
    assert hosts() == ["openrouter.ai"]
    providers.save_key("nvidia", "nvapi-test")
    assert hosts() == ["integrate.api.nvidia.com", "openrouter.ai"]


def test_turning_cloud_off_closes_the_door_again(vault):
    providers.save_key("openrouter", "sk-or-test"); providers.set_cloud_enabled(True); providers.set_cloud_enabled(False)
    assert hosts() == []


def test_an_external_local_backend_allows_just_its_host(vault):
    providers.set_setting("ollama_base", "http://host.docker.internal:11434")
    providers.save_model("ollama", "ollama/gemma3:4b")
    assert hosts() == ["host.docker.internal"]


def test_a_malformed_backend_address_is_never_written(vault):
    providers.set_setting("ollama_base", "http://evil.example .other.example/\n.everything")
    providers.save_model("ollama", "ollama/gemma3:4b")
    assert hosts() == []


def test_write_files_writes_the_allowlist(vault, tmp_path, monkeypatch):
    monkeypatch.setenv("PAI_SHARED_DIR", str(tmp_path))
    providers.save_key("openrouter", "sk-or-test"); providers.set_cloud_enabled(True)
    providers.write_files()
    assert (tmp_path / "egress-allowlist.txt").read_text() == "openrouter.ai\n"
    assert os.stat(tmp_path / "egress-allowlist.txt").st_mode & 0o777 == 0o644
