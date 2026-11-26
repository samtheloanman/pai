"""Owner login, sessions and paired devices (plan Phase 1)."""
import time

import pytest
from fastapi.testclient import TestClient

import main
from pai import audit, auth

PASS = "correct horse battery staple"
PUBLIC = {"/api/health", "/api/auth/status", "/api/auth/setup", "/api/auth/login", "/api/auth/pair"}


def kinds():
    return [e["kind"] for e in reversed(audit.entries(limit=200))]


def api_routes():
    for r in main.app.routes:
        path = getattr(r, "path", "")
        if path.startswith("/api/"):
            for m in sorted(getattr(r, "methods", set()) - {"HEAD", "OPTIONS"}):
                yield m, path


@pytest.fixture
def paired(client):
    """A second client that has paired as a device using a code the owner created."""
    code = client.post("/api/devices/pairing").json()["code"]
    phone = TestClient(main.app)
    r = phone.post("/api/auth/pair", json={"code": code, "name": "Sam's phone"})
    assert r.status_code == 200, r.text
    return phone, r.json()


# --- first boot ------------------------------------------------------------------------------------------------

def test_fresh_box_has_no_owner_and_no_default_password(anon):
    assert anon.get("/api/auth/status").json() == {"owner": False, "signed_in": False, "device": None}
    assert anon.post("/api/auth/login", json={"passphrase": ""}).status_code == 401
    assert anon.post("/api/auth/login", json={"passphrase": "admin"}).status_code == 401


def test_setup_creates_the_owner_once_and_signs_in(anon):
    r = anon.post("/api/auth/setup", json={"passphrase": PASS})
    assert r.status_code == 200
    assert anon.get("/api/auth/status").json()["signed_in"] is True
    assert anon.get("/api/memories").status_code == 200
    again = TestClient(main.app).post("/api/auth/setup", json={"passphrase": "another long passphrase"})
    assert again.status_code == 409
    assert "owner_created" in kinds()


def test_setup_rejects_a_short_passphrase(anon):
    assert anon.post("/api/auth/setup", json={"passphrase": "short"}).status_code == 400
    assert anon.get("/api/auth/status").json()["owner"] is False


def test_passphrase_is_stored_as_argon2id_never_in_clear(anon):
    anon.post("/api/auth/setup", json={"passphrase": PASS})
    from contextlib import closing
    with closing(main.db()) as con:
        stored = con.execute("select pass_hash from owner").fetchone()[0]
    assert stored.startswith("$argon2id$") and PASS not in stored


# --- every data route needs a login ----------------------------------------------------------------------------

def test_every_api_route_refuses_an_anonymous_request(anon):
    anon.post("/api/auth/setup", json={"passphrase": PASS})
    stranger = TestClient(main.app)
    checked = 0
    for method, path in api_routes():
        if path in PUBLIC:
            continue
        r = stranger.request(method, path.replace("{mid}", "1").replace("{aid}", "x").replace("{did}", "x"))
        assert r.status_code == 401, (method, path, r.status_code)
        checked += 1
    assert checked > 25


def test_routes_refuse_before_any_owner_exists(anon):
    assert anon.get("/api/memories").status_code == 401
    assert anon.get("/api/health").status_code == 200


def test_the_web_app_shell_still_loads_without_login(anon):
    assert anon.get("/api/health").status_code == 200
    assert anon.get("/static/manifest.json").status_code == 200


# --- login, logout, sessions -----------------------------------------------------------------------------------

def test_login_logout_round_trip_and_audit(client):
    other = TestClient(main.app)
    assert other.post("/api/auth/login", json={"passphrase": "wrong passphrase here"}).status_code == 401
    r = other.post("/api/auth/login", json={"passphrase": auth_pass(client)})
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/" in cookie
    assert other.get("/api/memories").status_code == 200
    assert other.post("/api/auth/logout").status_code == 200
    assert other.get("/api/memories").status_code == 401
    k = kinds()
    assert {"auth_login_failed", "auth_login", "auth_logout"} <= set(k)
    assert all(auth_pass(client) not in str(e) for e in audit.entries(limit=200))


def test_cookie_is_secure_behind_https(client):
    r = TestClient(main.app).post("/api/auth/login", json={"passphrase": auth_pass(client)},
                                  headers={"X-Forwarded-Proto": "https"})
    assert "secure" in r.headers["set-cookie"].lower()


def test_session_token_is_stored_hashed(client):
    token = client.cookies.get(auth.COOKIE)
    from contextlib import closing
    with closing(main.db()) as con:
        stored = [row[0] for row in con.execute("select token_hash from auth_tokens")]
    assert token and token not in stored and auth.hash_token(token) in stored


def test_expired_session_is_refused(client, monkeypatch):
    real = time.time
    monkeypatch.setattr(auth.time, "time", lambda: real() + auth.SESSION_TTL + 60)
    assert client.get("/api/memories").status_code == 401


def test_a_forged_or_garbage_token_is_refused(client):
    bad = TestClient(main.app, cookies={auth.COOKIE: "not-a-real-token"})
    assert bad.get("/api/memories").status_code == 401
    assert TestClient(main.app).get("/api/memories", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_cross_site_writes_with_the_cookie_are_refused(client):
    r = client.post("/api/rules", json={"text": "x"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert client.get("/api/memories", headers={"Origin": "https://evil.example"}).status_code == 200  # reads are safe


# --- rate limiting ---------------------------------------------------------------------------------------------

def test_repeated_wrong_passphrases_lock_login(client):
    other = TestClient(main.app)
    for _ in range(auth.FREE_ATTEMPTS):
        assert other.post("/api/auth/login", json={"passphrase": "wrong passphrase here"}).status_code == 401
    r = other.post("/api/auth/login", json={"passphrase": auth_pass(client)})
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1


def test_lockout_expires(client, monkeypatch):
    other = TestClient(main.app)
    for _ in range(auth.FREE_ATTEMPTS):
        other.post("/api/auth/login", json={"passphrase": "wrong passphrase here"})
    real = time.time
    monkeypatch.setattr(auth.time, "time", lambda: real() + auth.MAX_LOCK + 1)
    assert other.post("/api/auth/login", json={"passphrase": auth_pass(client)}).status_code == 200


def test_repeated_wrong_pairing_codes_lock_pairing(client):
    phone = TestClient(main.app)
    for _ in range(auth.FREE_ATTEMPTS):
        assert phone.post("/api/auth/pair", json={"code": "AAAAA-AAAAA", "name": "x"}).status_code == 401
    code = client.post("/api/devices/pairing").json()["code"]
    assert phone.post("/api/auth/pair", json={"code": code, "name": "x"}).status_code == 429


# --- devices ---------------------------------------------------------------------------------------------------

def test_pairing_code_shape_and_expiry(client):
    r = client.post("/api/devices/pairing").json()
    assert len(r["code"]) == 11 and r["code"][5] == "-" and r["expires_in"] == auth.PAIRING_TTL


def test_paired_device_can_use_the_api_with_its_cookie_or_token(paired):
    phone, body = paired
    assert phone.get("/api/memories").status_code == 200
    assert phone.get("/api/auth/status").json()["device"] == "Sam's phone"
    bearer = TestClient(main.app).get("/api/memories", headers={"Authorization": f"Bearer {body['token']}"})
    assert bearer.status_code == 200


def test_pairing_code_works_once(client):
    code = client.post("/api/devices/pairing").json()["code"]
    assert TestClient(main.app).post("/api/auth/pair", json={"code": code, "name": "a"}).status_code == 200
    assert TestClient(main.app).post("/api/auth/pair", json={"code": code, "name": "b"}).status_code == 401


def test_pairing_code_accepts_lower_case_and_no_dash(client):
    code = client.post("/api/devices/pairing").json()["code"]
    loose = code.replace("-", "").lower()
    assert TestClient(main.app).post("/api/auth/pair", json={"code": loose, "name": "a"}).status_code == 200


def test_expired_pairing_code_is_refused(client, monkeypatch):
    code = client.post("/api/devices/pairing").json()["code"]
    real = time.time
    monkeypatch.setattr(auth.time, "time", lambda: real() + auth.PAIRING_TTL + 1)
    assert TestClient(main.app).post("/api/auth/pair", json={"code": code, "name": "a"}).status_code == 401


def test_devices_are_listed_and_revoking_cuts_access(client, paired):
    phone, body = paired
    devices = client.get("/api/devices").json()
    assert [d["name"] for d in devices] == ["Sam's phone"]
    assert set(devices[0]) == {"id", "name", "created", "last_seen"}
    assert client.delete(f"/api/devices/{body['device_id']}").status_code == 200
    assert phone.get("/api/memories").status_code == 401
    assert client.get("/api/devices").json() == []
    assert {"device_pairing_started", "device_paired", "device_revoked"} <= set(kinds())


def test_revoking_an_unknown_device_is_404(client):
    assert client.delete("/api/devices/nope").status_code == 404


def test_device_name_is_bounded(client):
    code = client.post("/api/devices/pairing").json()["code"]
    r = TestClient(main.app).post("/api/auth/pair", json={"code": code, "name": "x" * 500})
    assert r.status_code == 422


def test_pairing_code_is_stored_hashed(client):
    code = client.post("/api/devices/pairing").json()["code"]
    from contextlib import closing
    with closing(main.db()) as con:
        stored = [row[0] for row in con.execute("select code_hash from pairing_codes")]
    assert code not in stored and code.replace("-", "") not in stored


# --- the Capacitor app (Phase 2) talks to the box cross-origin with a device token ---------------------------

def test_cors_allows_only_the_app_origins(client):
    ok = client.options("/api/memories", headers={"Origin": "capacitor://localhost", "Access-Control-Request-Method": "GET",
                                                  "Access-Control-Request-Headers": "authorization"})
    assert ok.headers.get("access-control-allow-origin") == "capacitor://localhost"
    assert ok.headers.get("access-control-allow-credentials") is None
    bad = client.options("/api/memories", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_bearer_write_from_the_app_origin_is_allowed(paired):
    _, body = paired
    r = TestClient(main.app).put("/api/rules", json={"text": "be brief"},
                                 headers={"Authorization": f"Bearer {body['token']}", "Origin": "capacitor://localhost"})
    assert r.status_code == 200


def auth_pass(_client):
    return PASS
