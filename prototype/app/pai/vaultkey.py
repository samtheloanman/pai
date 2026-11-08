"""Where the vault key comes from, best source first: a file (Docker/Compose secret), a systemd credential, the env.

On the PAI OS image the credential is sealed to the TPM (systemd-creds) and arrives as $CREDENTIALS_DIRECTORY/vault-key.
On a dev Mac, scripts/pai-up reads it from the macOS Keychain and passes it as a Compose secret, so it never sits in
.env or in the container's environment. The env var stays as the fallback for tests and old setups.
A configured source that cannot be read is an error: it never falls back to a weaker one.
"""
import os


class NoVaultKey(Exception):
    pass


def get() -> str:
    path = os.environ.get("PAI_VAULT_KEY_FILE") or (
        os.path.join(os.environ["CREDENTIALS_DIRECTORY"], "vault-key") if os.environ.get("CREDENTIALS_DIRECTORY") else "")
    if path:
        try:
            with open(path) as f:
                key = f.read().strip()
        except OSError as e:
            raise NoVaultKey(f"cannot read the vault key file {path}: {e.strerror}") from None
    else:
        key = os.environ.get("PAI_VAULT_KEY", "")  # not stripped: it must stay byte-identical to the key already in use
    if not key.strip():
        raise NoVaultKey("no vault key: set PAI_VAULT_KEY_FILE, a systemd credential 'vault-key', or PAI_VAULT_KEY "
                         "(generate one with: openssl rand -hex 32; losing it means losing the vault)")
    return key
