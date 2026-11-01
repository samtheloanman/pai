#!/bin/sh
# Live-server e2e: fake LiteLLM + uvicorn on temp dirs, embedder off. Needs no docker.
cd "$(dirname "$0")" || exit 1
PY=${PY:-.venv/bin/python}
APP_PORT=${PAI_E2E_APP_PORT:-8099}
FAKE_PORT=${PAI_E2E_FAKE_PORT:-4999}
for p in $APP_PORT $FAKE_PORT; do
  if $PY -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1',$p))==0 else 1)"; then
    echo "run-e2e: port $p is already in use; refusing to run against another server (set PAI_E2E_APP_PORT / PAI_E2E_FAKE_PORT)" >&2
    exit 1
  fi
done
export PAI_E2E_BASE=http://127.0.0.1:$APP_PORT PAI_E2E_FAKE=http://127.0.0.1:$FAKE_PORT
T=$(mktemp -d)
FAKE_PID= APP_PID=
cleanup() { kill $FAKE_PID $APP_PID 2>/dev/null; rm -rf "$T"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
$PY tests/fake_litellm.py "$FAKE_PORT" & FAKE_PID=$!
AUDIT_CONTENT=0 DATA_DIR=$T PAI_SHARED_DIR=$T PAI_EMBED=off PAI_VAULT_KEY=e2e-test-key LITELLM_URL=$PAI_E2E_FAKE LITELLM_MASTER_KEY=sk-test \
  $PY -m uvicorn main:app --port "$APP_PORT" --log-level warning & APP_PID=$!
ok=
for i in $(seq 1 60); do
  kill -0 $APP_PID 2>/dev/null && kill -0 $FAKE_PID 2>/dev/null || break
  curl -sf "$PAI_E2E_BASE/api/health" >/dev/null && { ok=1; break; }
  sleep 0.5
done
if [ -z "$ok" ] || ! kill -0 $APP_PID 2>/dev/null || ! kill -0 $FAKE_PID 2>/dev/null; then
  echo "run-e2e: app or fake LiteLLM did not start" >&2
  exit 1
fi
PAI_E2E=1 $PY -m pytest -q -m e2e tests/test_e2e.py
