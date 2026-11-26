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


@pytest.fixture(autouse=True)
def fast_auth(monkeypatch):
    """Cheap Argon2 parameters and fresh login throttles per test. Production parameters live in pai/auth.py."""
    from argon2 import PasswordHasher
    from pai import auth
    monkeypatch.setattr(auth, "HASHER", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))
    auth.reset_throttles()


@pytest.fixture
def anon(audit_db):
    """A client with no login, on an empty vault with no owner."""
    from fastapi.testclient import TestClient
    import main
    path = os.path.join(main.DATA_DIR, "pai.db")
    if os.path.exists(path):
        os.remove(path)  # each test starts with an empty vault
    return TestClient(main.app)


PASS = "correct horse battery staple"


def sign_in(c):
    """Sign a client in on whatever vault DATA_DIR points at now (creates the owner on an empty vault)."""
    c.cookies.clear()
    path = "/api/auth/login" if c.get("/api/auth/status").json()["owner"] else "/api/auth/setup"
    r = c.post(path, json={"passphrase": PASS})
    assert r.status_code == 200, r.text
    return c


@pytest.fixture
def client(anon):
    """Signed in as the owner (the session cookie stays on this client)."""
    return sign_in(anon)


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
        self.fail = None  # url suffix that raises an httpx error
        self.chat_body = None  # override the 200 chat body
        self.error_body = {"error": "boom"}
        self.calls = []

    def post(self, url, **kw):
        self.calls.append((url, kw))
        if self.fail and url.endswith(self.fail):
            import httpx
            raise httpx.ConnectError(f"cannot reach {url}")
        if self.status != 200:
            return _Resp(self.status, self.error_body)
        if self.chat_body is not None and url.endswith("/chat/completions"):
            return _Resp(200, self.chat_body)
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


@pytest.fixture
def vault(client, tmp_path, monkeypatch):
    """Fresh empty vault + isolated /shared dir for provider tests."""
    monkeypatch.setenv("PAI_SHARED_DIR", str(tmp_path / "shared"))
    return client
