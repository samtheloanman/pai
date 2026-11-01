#!/bin/sh
# Runs the backend tests in the same Python the image uses; no local Python needed.
cd "$(dirname "$0")" && docker run --rm -v "$PWD":/app -w /app python:3.12-slim \
  sh -c "pip install -q -r requirements.txt && pytest -q tests"
