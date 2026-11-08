#!/usr/bin/env bash
set -euo pipefail

echo "===================================================="
echo "        PAI OS — Sovereign Desktop AI Companion      "
echo "===================================================="

# Check docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is required. Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "==> Starting PAI OS + Local Ollama..."
docker compose up -d

echo "==> Pulling lightweight default model (gemma3:4b)..."
docker compose exec -T ollama ollama pull gemma3:4b || true

echo ""
echo "✨ PAI OS is running!"
echo "🌐 Open your browser: http://localhost:8088"
echo ""
