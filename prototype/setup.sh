#!/usr/bin/env bash
set -euo pipefail

# PAI One-Line Setup & Orchestrator
# Usage: curl -sSL https://get.pai.local/setup.sh | bash -s -- [options]
# Or locally: ./setup.sh

echo "========================================"
echo "      PAI Appliance Orchestrator        "
echo "        Your AI. Your house.            "
echo "========================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 1. Environment pre-flight
if [ ! -f .env ]; then
  echo "[+] Generating .env configuration..."
  cp .env.example .env
  MASTER_KEY="sk-$(openssl rand -hex 16)"
  sed -i '' "s/sk-change-me/${MASTER_KEY}/" .env 2>/dev/null || sed -i "s/sk-change-me/${MASTER_KEY}/" .env
fi

# 1b. Vault key: kept outside .env (Keychain / systemd-creds / 0600 file, see scripts/pai-up).
#     An old PAI_VAULT_KEY line in .env is moved into the key store and removed from .env.
scripts/pai-up migrate-key
scripts/pai-up has-key || scripts/pai-up new-key

# 2. Start container stack
echo "[+] Starting PAI services (LiteLLM, Speaches, LLM, App)..."
scripts/pai-up --profile local up -d --build

# 3. Healthcheck loop
echo "[+] Awaiting service readiness..."
for i in {1..30}; do
  if curl -s -f http://127.0.0.1:8088/api/interview >/dev/null 2>&1; then
    echo ""
    echo "========================================"
    echo "   PAI is LIVE: http://localhost:8088   "
    echo "========================================"
    exit 0
  fi
  sleep 2
  printf "."
done

echo ""
echo "[!] Error: PAI startup timed out. Check: docker compose logs app"
exit 1
