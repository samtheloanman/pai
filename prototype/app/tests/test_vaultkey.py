import pytest

from pai import vaultkey


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    for v in ("PAI_VAULT_KEY", "PAI_VAULT_KEY_FILE", "CREDENTIALS_DIRECTORY"):
        monkeypatch.delenv(v, raising=False)


def test_env_is_the_fallback(monkeypatch):
    monkeypatch.setenv("PAI_VAULT_KEY", "from-env")
    assert vaultkey.get() == "from-env"


def test_file_beats_env_and_is_stripped(monkeypatch, tmp_path):
    f = tmp_path / "k"; f.write_text("from-file\n")
    monkeypatch.setenv("PAI_VAULT_KEY", "from-env"); monkeypatch.setenv("PAI_VAULT_KEY_FILE", str(f))
    assert vaultkey.get() == "from-file"


def test_systemd_credential_is_found(monkeypatch, tmp_path):
    (tmp_path / "vault-key").write_text("from-cred")
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(tmp_path))
    assert vaultkey.get() == "from-cred"


def test_missing_or_empty_is_an_error_not_a_blank_key(monkeypatch, tmp_path):
    with pytest.raises(vaultkey.NoVaultKey):
        vaultkey.get()
    f = tmp_path / "k"; f.write_text("  \n")
    monkeypatch.setenv("PAI_VAULT_KEY_FILE", str(f))
    with pytest.raises(vaultkey.NoVaultKey):
        vaultkey.get()


def test_unreadable_file_does_not_fall_back_silently(monkeypatch, tmp_path):
    monkeypatch.setenv("PAI_VAULT_KEY", "from-env"); monkeypatch.setenv("PAI_VAULT_KEY_FILE", str(tmp_path / "nope"))
    with pytest.raises(vaultkey.NoVaultKey):
        vaultkey.get()
