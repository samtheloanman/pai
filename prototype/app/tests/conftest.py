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


@pytest.fixture
def audit_db(tmp_path, monkeypatch):
    """Isolated audit file; the audit module reads DATA_DIR on every call so nothing else is cached."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("AUDIT_CONTENT", raising=False)
    from pai import audit
    return audit


@pytest.fixture
def client(audit_db):
    from fastapi.testclient import TestClient
    import main
    path = os.path.join(main.DATA_DIR, "pai.db")
    if os.path.exists(path):
        os.remove(path)  # each test starts with an empty vault
    return TestClient(main.app)


class _Resp:
    def __init__(self, status=200, body=None, content=b""):
        self.status_code, self._body, self.content, self.text = status, body or {}, content, str(body)

    def json(self):
        return self._body


class MockLitellm:
    """Stands in for LiteLLM at the httpx layer, so main.llm/transcribe/speak run for real."""
    def __init__(self):
        self.reply = "hello there"
        self.usage = {"prompt_tokens": 11, "completion_tokens": 7}
        self.status = 200
        self.calls = []

    def post(self, url, **kw):
        self.calls.append((url, kw))
        if self.status != 200:
            return _Resp(self.status, {"error": "boom"})
        if url.endswith("/chat/completions"):
            body = {"choices": [{"message": {"content": self.reply}}]}
            if self.usage:
                body["usage"] = self.usage
            return _Resp(200, body)
        if url.endswith("/audio/transcriptions"):
            return _Resp(200, {"text": "heard words"})
        return _Resp(200, content=b"mp3")


@pytest.fixture
def mock_litellm(monkeypatch):
    import main
    m = MockLitellm()

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, **kw): return m.post(url, **kw)

    monkeypatch.setattr(main.httpx, "AsyncClient", FakeClient)
    return m
