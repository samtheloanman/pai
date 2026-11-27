#!/bin/sh
# Runs the backend tests in the same Python the image uses; no local Python needed.
cd "$(dirname "$0")" && docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e PIP_CACHE_DIR=/tmp/pip -e PYTHONUSERBASE=/tmp/.local -e PYTHONDONTWRITEBYTECODE=1 -e PATH=/tmp/.local/bin:/usr/local/bin:/usr/bin:/bin -v "$PWD/../..":/r -w /r/prototype/app python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b \
  sh -c "pip install --user -q -r requirements.txt && pytest -q tests"
