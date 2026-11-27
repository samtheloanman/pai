"""Owner login, sessions and paired devices.

One owner per box, created at first boot; there is no default password. The passphrase is hashed with Argon2id.
Browser sessions and paired devices each get a random token: the box stores only its SHA-256, and the client keeps
the token in an HttpOnly, SameSite=Strict cookie (or sends it as `Authorization: Bearer` from the phone app).
Pairing codes are single use, short lived and stored hashed. Failed logins and failed pairings are throttled.
All state lives in the encrypted vault (tables added by store migration v7).
"""
import hashlib
import hmac
import secrets
import threading
import time
from contextlib import closing

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

COOKIE = "pai_session"
MIN_PASSPHRASE = 12
SESSION_TTL = 30 * 24 * 3600    # browser login
DEVICE_TTL = 180 * 24 * 3600    # paired phone or laptop
PAIRING_TTL = 10 * 60
FREE_ATTEMPTS = 5               # failures before the lockout starts
MAX_LOCK = 15 * 60
SEEN_EVERY = 60                 # update last_seen at most once a minute per token
HASHER = PasswordHasher()       # Argon2id, library defaults (RFC 9106 low-memory profile)
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L


def _db():
    import main  # late import: main owns the vault path, and imports this module
    return main.db()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# --- throttling ------------------------------------------------------------------------------------------------

class Throttle:
    """Box-wide failure counter. Not per IP: behind `tailscale serve` every request arrives from 127.0.0.1."""

    def __init__(self):
        self.lock = threading.Lock()
        self.failures = 0
        self.last = 0.0

    def wait(self) -> int:
        """Seconds until the next attempt is allowed (0 = now)."""
        with self.lock:
            if self.failures < FREE_ATTEMPTS:
                return 0
            lock = min(2 ** (self.failures - FREE_ATTEMPTS), MAX_LOCK)
            return max(0, int(self.last + lock - time.time() + 0.999))

    def fail(self) -> None:
        with self.lock:
            self.failures += 1
            self.last = time.time()

    def ok(self) -> None:
        with self.lock:
            self.failures = 0


LOGIN, PAIRING = Throttle(), Throttle()


def reset_throttles() -> None:
    LOGIN.ok(); PAIRING.ok()


# --- owner -----------------------------------------------------------------------------------------------------

def owner_exists() -> bool:
    with closing(_db()) as con:
        return con.execute("select count(*) from owner").fetchone()[0] > 0


def create_owner(passphrase: str) -> bool:
    """False if an owner already exists. The insert is guarded by the table's single-row check."""
    h = HASHER.hash(passphrase)
    with closing(_db()) as con, con:
        cur = con.execute("insert or ignore into owner (id, pass_hash, created) values (1, ?, ?)", (h, time.time()))
        return cur.rowcount == 1


def check_passphrase(passphrase: str) -> bool:
    with closing(_db()) as con:
        row = con.execute("select pass_hash from owner where id = 1").fetchone()
    if not row:
        HASHER.hash(passphrase)  # same cost whether or not an owner exists
        return False
    try:
        HASHER.verify(row[0], passphrase)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    if HASHER.check_needs_rehash(row[0]):
        with closing(_db()) as con, con:
            con.execute("update owner set pass_hash = ? where id = 1", (HASHER.hash(passphrase),))
    return True


# --- tokens ----------------------------------------------------------------------------------------------------

def issue(device_id: str | None = None) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    ttl = DEVICE_TTL if device_id else SESSION_TTL
    now = time.time()
    with closing(_db()) as con, con:
        con.execute("insert into auth_tokens (token_hash, device_id, created, expires, last_seen) values (?,?,?,?,?)",
                    (hash_token(token), device_id, now, now + ttl, now))
    return token, ttl


def lookup(token: str | None) -> dict | None:
    """The session for a token, or None. Expired tokens are deleted on sight."""
    if not token or len(token) > 200:
        return None
    th, now = hash_token(token), time.time()
    with closing(_db()) as con, con:
        row = con.execute("""select t.token_hash, t.device_id, t.expires, t.last_seen, d.name
                             from auth_tokens t left join devices d on d.id = t.device_id
                             where t.token_hash = ?""", (th,)).fetchone()
        if not row or not hmac.compare_digest(row[0], th):
            return None
        if row[2] <= now:
            con.execute("delete from auth_tokens where token_hash = ?", (th,))
            return None
        if now - row[3] > SEEN_EVERY:
            con.execute("update auth_tokens set last_seen = ? where token_hash = ?", (now, th))
            if row[1]:
                con.execute("update devices set last_seen = ? where id = ?", (now, row[1]))
    return {"device_id": row[1], "device": row[4]}


def revoke_token(token: str | None) -> None:
    if token:
        with closing(_db()) as con, con:
            con.execute("delete from auth_tokens where token_hash = ?", (hash_token(token),))


# --- devices ---------------------------------------------------------------------------------------------------

def _norm(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def new_pairing_code() -> str:
    raw = "".join(secrets.choice(_ALPHABET) for _ in range(10))
    now = time.time()
    with closing(_db()) as con, con:
        con.execute("delete from pairing_codes where expires <= ? or used is not null", (now,))
        con.execute("insert into pairing_codes (code_hash, created, expires) values (?,?,?)",
                    (hash_token(raw), now, now + PAIRING_TTL))
    return f"{raw[:5]}-{raw[5:]}"


def redeem_pairing_code(code: str, name: str) -> str | None:
    """Device id on success. The code is marked used in the same transaction that checks it."""
    now = time.time()
    with closing(_db()) as con, con:
        cur = con.execute("update pairing_codes set used = ? where code_hash = ? and used is null and expires > ?",
                          (now, hash_token(_norm(code)), now))
        if cur.rowcount != 1:
            return None
        did = secrets.token_hex(8)
        con.execute("insert into devices (id, name, created, last_seen) values (?,?,?,?)", (did, name, now, now))
    return did


def list_devices() -> list[dict]:
    with closing(_db()) as con:
        rows = con.execute("select id, name, created, last_seen from devices order by created").fetchall()
    return [{"id": i, "name": n, "created": c, "last_seen": s} for i, n, c, s in rows]


def revoke_device(did: str) -> bool:
    with closing(_db()) as con, con:
        con.execute("delete from auth_tokens where device_id = ?", (did,))
        return con.execute("delete from devices where id = ?", (did,)).rowcount == 1
