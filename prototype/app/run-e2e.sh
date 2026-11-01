#!/bin/sh
# Live-server e2e: fake LiteLLM + uvicorn on temp dirs, embedder off. Needs no docker.
cd "$(dirname "$0")" || exit 1
PY=${PY:-.venv/bin/python}
T=$(mktemp -d)
trap 'kill $FAKE_PID $APP_PID 2>/dev/null; rm -rf "$T"' EXIT
$PY tests/fake_litellm.py 4999 & FAKE_PID=$!
DATA_DIR=$T PAI_SHARED_DIR=$T PAI_EMBED=off PAI_VAULT_KEY=e2e-test-key LITELLM_URL=http://127.0.0.1:4999 LITELLM_MASTER_KEY=sk-test \
  $PY -m uvicorn main:app --port 8099 --log-level warning & APP_PID=$!
for i in $(seq 1 60); do curl -sf http://127.0.0.1:8099/api/health >/dev/null && break; sleep 0.5; done
PAI_E2E=1 $PY -m pytest -q -m e2e tests/test_e2e.py
