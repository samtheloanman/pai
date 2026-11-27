#!/bin/sh
# Quick start from the repo root: the same stack and installer as prototype/ (llama.cpp + LiteLLM + Speaches + app).
# prototype/scripts/install.sh creates prototype/.env, stores the vault key outside the repo (macOS Keychain,
# systemd-creds, or ~/.config/pai/vault-key with mode 0600), starts the stack on 127.0.0.1 and checks health.
set -eu
exec "$(cd "$(dirname "$0")" && pwd)/prototype/scripts/install.sh" "$@"
