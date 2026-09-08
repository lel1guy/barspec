"""S1 auth: owner PIN gate (stdlib only — no dnf deps for the live service).

- PIN stored as pbkdf2_hmac (sha256, 260k iters, per-PIN salt) — same
  brute-force resistance class as bcrypt, zero installs.
- Sessions are HMAC-signed cookies (owner + expiry); the signing secret is
  random, generated on first setup, persisted in settings.
- Everything under /api is gated once a PIN exists; /api/auth/* stays open.
"""
import hashlib
import hmac
import os
import secrets
import time

import db

_ITER = 260_000
_COOKIE = "barspec_sesh"
_MAX_AGE = 60 * 60 * 24 * 14  # 14 days; re-enter after that

PIN_KEY = "auth.pin_hash"
SECRET_KEY = "auth.secret"


def _derive(pin: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, _ITER)


def hash_pin(pin: str) -> str:
    salt = os.urandom(16)
    return f"pbkdf2${_ITER}${salt.hex()}${_derive(pin, salt).hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    try:
        _, iters, salt_hex, hash_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expect = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False
    got = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, int(iters))
    return hmac.compare_digest(got, expect)


def _secret() -> str:
    s = db.get_setting(SECRET_KEY)
    if not s:
        s = secrets.token_hex(32)
        db.set_setting_value(SECRET_KEY, s)
    return s


def pin_is_set() -> bool:
    return bool(db.get_setting(PIN_KEY))


STAFF_PIN_KEY = "auth.staff_pin"


def sign_token(role: str = "owner") -> str:
    exp = int(time.time()) + _MAX_AGE
    payload = f"{role}.{exp}"
    sig = hmac.new(_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def token_role(value: str | None) -> str | None:
    """'owner' | 'staff' | None. None also covers expired/forged cookies."""
    if not cookie_valid(value):
        return None
    return value.split(".")[0]


def cookie_valid(value: str | None) -> bool:
    if not value:
        return False
    parts = value.split(".")
    if len(parts) != 3:
        return False
    payload, exp, sig = parts[0], parts[1], parts[2]
    if payload not in ("owner", "staff"):
        return False
    expect = hmac.new(_secret().encode(), f"{payload}.{exp}".encode(),
                      hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expect):
        return False
    return int(exp) > time.time()


def make_cookie(name: str = _COOKIE, role: str = "owner") -> str:
    return (f"{name}={sign_token(role)}; Path=/; HttpOnly; SameSite=Lax; "
            f"Max-Age={_MAX_AGE}")


def clear_cookie(name: str = _COOKIE) -> str:
    return f"{name}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
