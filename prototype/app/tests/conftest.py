import os
import sys
import tempfile

# Must run before any test module imports main.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["PAI_VAULT_KEY"] = "test-vault-key"

import hashlib

import pytest


def fake_embedding(text: str) -> list[float]:
    """Deterministic offline stand-in for the real model (384 dims, hashed bag of words)."""
    v = [0.0] * 384
    for w in text.lower().split():
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 384] += 1.0
    return v


@pytest.fixture(autouse=True)
def offline_embedder(monkeypatch):
    from pai import embed
    monkeypatch.setattr(embed, "embed", fake_embedding)
