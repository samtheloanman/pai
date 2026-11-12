#!/bin/sh
# 1-Click Bootstrap Installer for PAI (Personal AI OS) Prototype
# Validates host RAM, sets up macOS Keychain vault key, validates model volumes,
# starts the stack via scripts/pai-up, and verifies health check.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "=========================================================="
echo "          PAI Prototype 1-Click Installer                 "
echo "=========================================================="

# -----------------------------------------------------------------------------
# 1. Check Docker and Docker Compose availability
# -----------------------------------------------------------------------------
echo "[1/6] Checking Docker and Docker Compose availability..."

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: 'docker' CLI not found. Please install Docker Desktop or Docker Engine." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Error: Docker daemon is not running. Please start Docker and retry." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Error: Docker Compose V2 ('docker compose') is required but not found." >&2
  exit 1
fi

DOCKER_VER="$(docker --version 2>/dev/null || echo 'docker')"
COMPOSE_VER="$(docker compose version --short 2>/dev/null || echo 'v2')"
echo "  ✓ Docker active: ${DOCKER_VER} (Compose ${COMPOSE_VER})"

# -----------------------------------------------------------------------------
# 2. Check host RAM and resources
# -----------------------------------------------------------------------------
echo "[2/6] Checking host RAM and resources..."

HOST_RAM_GB=0
if [ "$(uname -s)" = "Darwin" ]; then
  MEM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
  HOST_RAM_GB=$((MEM_BYTES / 1024 / 1024 / 1024))
elif [ -f /proc/meminfo ]; then
  MEM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
  HOST_RAM_GB=$((MEM_KB / 1024 / 1024))
fi

DOCKER_MEM_BYTES=$(docker info --format '{{.MemTotal}}' 2>/dev/null || docker info --format '{{.TotalMemory}}' 2>/dev/null || echo 0)
DOCKER_MEM_GB=$((DOCKER_MEM_BYTES / 1024 / 1024 / 1024))

echo "  Host RAM: ${HOST_RAM_GB} GB | Docker Engine Memory: ${DOCKER_MEM_GB} GB"

if [ "$HOST_RAM_GB" -eq 0 ]; then
  echo "  i Note: Host RAM size could not be detected automatically."
elif [ "$HOST_RAM_GB" -lt 8 ]; then
  echo "  ! Warning: Host RAM is ${HOST_RAM_GB} GB (< 8 GB minimum recommended for local LLM)." >&2
elif [ "$HOST_RAM_GB" -ge 32 ]; then
  echo "  ✓ Host RAM is optimal (${HOST_RAM_GB} GB; capable of running Qwen3-30B-A3B if configured)."
else
  echo "  ✓ Host RAM is sufficient for default Qwen3-4B local model (${HOST_RAM_GB} GB)."
fi

# -----------------------------------------------------------------------------
# 3. Ensure PAI_VAULT_KEY exists or create/import one into macOS Keychain
# -----------------------------------------------------------------------------
echo "[3/6] Ensuring PAI_VAULT_KEY and environment configuration..."

if [ ! -f .env ]; then
  echo "  Creating .env from .env.example..."
  cp .env.example .env
fi

# Ensure COMPOSE_PROJECT_NAME is defined
if ! grep -q "^COMPOSE_PROJECT_NAME=" .env; then
  echo "COMPOSE_PROJECT_NAME=pai-mvp" >> .env
fi

# Ensure LITELLM_MASTER_KEY is set and not default dummy key
CURRENT_MASTER_KEY="$(grep '^LITELLM_MASTER_KEY=' .env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]' || true)"
if [ -z "$CURRENT_MASTER_KEY" ] || [ "$CURRENT_MASTER_KEY" = "sk-change-me" ]; then
  NEW_MASTER_KEY="sk-$(openssl rand -hex 16)"
  if grep -q "^LITELLM_MASTER_KEY=" .env; then
    TMP_ENV=$(mktemp)
    sed "s|^LITELLM_MASTER_KEY=.*|LITELLM_MASTER_KEY=${NEW_MASTER_KEY}|" .env > "$TMP_ENV" && mv "$TMP_ENV" .env
  else
    echo "LITELLM_MASTER_KEY=${NEW_MASTER_KEY}" >> .env
  fi
  echo "  Generated new LITELLM_MASTER_KEY in .env"
fi

# macOS Keychain management or headless fallback
if command -v security >/dev/null 2>&1 && [ "$(uname -s)" = "Darwin" ]; then
  if security find-generic-password -s pai-vault-key >/dev/null 2>&1; then
    echo "  ✓ Vault key already present in macOS Keychain (pai-vault-key)."
  else
    ENV_KEY="$(grep '^PAI_VAULT_KEY=' .env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]' || true)"
    if [ -n "$ENV_KEY" ]; then
      echo "  Importing PAI_VAULT_KEY from .env into macOS Keychain..."
      printf '%s\n' "$ENV_KEY" | "$SCRIPT_DIR/pai-up" import-key
    else
      echo "  Creating new random PAI_VAULT_KEY in macOS Keychain..."
      "$SCRIPT_DIR/pai-up" new-key
    fi
    echo "  ✓ Vault key stored in macOS Keychain."
  fi
  export PAI_VAULT_KEY="$(security find-generic-password -s pai-vault-key -w 2>/dev/null || true)"
else
  ENV_KEY="$(grep '^PAI_VAULT_KEY=' .env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]' || true)"
  if [ -z "$ENV_KEY" ]; then
    echo "  Generating fresh PAI_VAULT_KEY in .env (non-macOS fallback)..."
    NEW_KEY="$(openssl rand -hex 32)"
    if grep -q "^PAI_VAULT_KEY=" .env; then
      TMP_ENV=$(mktemp)
      sed "s|^PAI_VAULT_KEY=.*|PAI_VAULT_KEY=${NEW_KEY}|" .env > "$TMP_ENV" && mv "$TMP_ENV" .env
    else
      echo "PAI_VAULT_KEY=${NEW_KEY}" >> .env
    fi
    ENV_KEY="$NEW_KEY"
  fi
  export PAI_VAULT_KEY="$ENV_KEY"
  echo "  ✓ Vault key configured in .env fallback."
fi

# -----------------------------------------------------------------------------
# 4. Validate or pull local GGUF models and Speaches models into volumes
# -----------------------------------------------------------------------------
echo "[4/6] Validating local GGUF models and Speaches models in volumes..."

PROJ_NAME="$(grep '^COMPOSE_PROJECT_NAME=' .env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]' || echo 'pai-mvp')"
[ -n "$PROJ_NAME" ] || PROJ_NAME="pai-mvp"

MODELS_VOL="${PROJ_NAME}_models"
VOICE_VOL="${PROJ_NAME}_voice"

# Ensure volumes exist with Compose labels to avoid warnings
docker volume inspect "$MODELS_VOL" >/dev/null 2>&1 || docker volume create --label "com.docker.compose.project=${PROJ_NAME}" --label "com.docker.compose.volume=models" "$MODELS_VOL" >/dev/null
docker volume inspect "$VOICE_VOL" >/dev/null 2>&1 || docker volume create --label "com.docker.compose.project=${PROJ_NAME}" --label "com.docker.compose.volume=voice" "$VOICE_VOL" >/dev/null

# Sync cache from alternative volume name if present
for ALT_PROJ in pai-mvp prototype; do
  if [ "$ALT_PROJ" != "$PROJ_NAME" ]; then
    if docker volume inspect "${ALT_PROJ}_models" >/dev/null 2>&1; then
      docker run --rm -v "${ALT_PROJ}_models:/src:ro" -v "${MODELS_VOL}:/dst" alpine sh -c 'cp -rn /src/* /dst/ 2>/dev/null || true'
    fi
    if docker volume inspect "${ALT_PROJ}_voice" >/dev/null 2>&1; then
      docker run --rm -v "${ALT_PROJ}_voice:/src:ro" -v "${VOICE_VOL}:/dst" alpine sh -c 'cp -rn /src/* /dst/ 2>/dev/null || true'
    fi
  fi
done

MODEL_HF="$(grep '^MODEL_HF=' .env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]' || true)"
[ -n "$MODEL_HF" ] || MODEL_HF="unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M"

# Pre-pull images if requested via --pull or PULL_MODELS=1
for arg in "$@"; do
  if [ "$arg" = "--pull" ]; then
    echo "  Pre-pulling local container images..."
    docker compose --profile local pull --ignore-pull-failures || true
    break
  fi
done

# Validate GGUF in volume cache
if docker run --rm -v "${MODELS_VOL}:/root/.cache/huggingface" ghcr.io/ggml-org/llama.cpp:server -cl 2>/dev/null | grep -q "Qwen3"; then
  echo "  ✓ GGUF model found in volume '${MODELS_VOL}'."
else
  echo "  i GGUF model weights will be pulled automatically by llama.cpp server on first start (${MODEL_HF})."
fi

# Validate Speaches voice models in volume cache
if docker run --rm -v "${VOICE_VOL}:/cache" alpine sh -c '[ -d /cache/models--Systran--faster-whisper-small ] && [ -d /cache/models--speaches-ai--Kokoro-82M-v1.0-ONNX ]' 2>/dev/null; then
  echo "  ✓ Speaches voice models verified in volume '${VOICE_VOL}'."
else
  echo "  i Speaches voice models will be automatically fetched on service startup."
fi

# -----------------------------------------------------------------------------
# 5. Start the stack with ./scripts/pai-up --profile local up -d
# -----------------------------------------------------------------------------
echo "[5/6] Starting PAI stack via ./scripts/pai-up --profile local up -d..."
"$SCRIPT_DIR/pai-up" --profile local up -d "$@"

# -----------------------------------------------------------------------------
# 6. Verify curl http://127.0.0.1:8088/api/health
# -----------------------------------------------------------------------------
PAI_PORT="$(grep '^PAI_PORT=' .env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]' || echo '8088')"
[ -n "$PAI_PORT" ] || PAI_PORT="8088"
HEALTH_URL="http://127.0.0.1:${PAI_PORT}/api/health"

echo "[6/6] Verifying PAI health check at ${HEALTH_URL}..."

MAX_WAIT_SECS=60
ELAPSED=0
HEALTHY=0

while [ "$ELAPSED" -lt "$MAX_WAIT_SECS" ]; do
  if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
    HEALTHY=1
    break
  fi
  sleep 1
  ELAPSED=$((ELAPSED + 1))
done

if [ "$HEALTHY" -eq 1 ]; then
  HEALTH_RESP="$(curl -s "$HEALTH_URL")"
  echo "  ✓ Health check passed: ${HEALTH_RESP}"
  echo ""
  echo "=========================================================="
  echo "PAI is ready!"
  echo "Open in your browser: http://127.0.0.1:${PAI_PORT}"
  echo "=========================================================="
else
  echo "Error: Health check timed out after ${MAX_WAIT_SECS} seconds." >&2
  docker compose logs --tail=50 app >&2
  exit 1
fi
