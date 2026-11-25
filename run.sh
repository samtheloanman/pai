#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "===================================================="
echo "        PAI OS — Sovereign Desktop AI Companion      "
echo "===================================================="

# Check docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is required. Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Each install gets its own vault key. Earlier versions shipped one default key in docker-compose.yml, which is
# public and so protects nothing.
LEGACY_PUBLIC_KEY="18ca26418558ea06e8859fa79967800c82f717c1198f0d48bb856df335d02036"
if [ -z "${PAI_VAULT_KEY:-}" ] && ! grep -q '^PAI_VAULT_KEY=[^[:space:]]' .env 2>/dev/null; then
    VOLUMES="$(docker volume ls -q)"  # captured first: piping straight into a quiet grep under pipefail can report a false "no match"
    if grep -q '_pai_data$' <<<"$VOLUMES"; then
        echo "Error: an existing PAI vault was found, and no PAI_VAULT_KEY is set." >&2
        echo "  If it was created before this version it is encrypted with the old published default key." >&2
        echo "  To keep that data, add this line to .env (the key is public, so treat the vault as unprotected):" >&2
        echo "    PAI_VAULT_KEY=$LEGACY_PUBLIC_KEY" >&2
        echo "  To start fresh instead, remove the old data volume, then run this script again." >&2
        exit 1
    fi
    ( umask 077; printf 'PAI_VAULT_KEY=%s\n' "$(openssl rand -hex 32)" >> .env )
    echo "==> Created your vault key in .env. Back it up: there is no recovery without it."
fi

echo "==> Starting PAI OS + Local Ollama..."
docker compose up -d

echo "==> Pulling lightweight default model (gemma3:4b)..."
docker compose exec -T ollama ollama pull gemma3:4b || true

echo ""
echo "✨ PAI OS is running!"
echo "🌐 Open your browser: http://localhost:8088"
echo ""
