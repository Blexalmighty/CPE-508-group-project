"""Credentials, token issuing, and the dependency that gates /api/predict.

School-project-grade authentication, stated honestly: credentials are read
from the environment (or a `.env` file loaded by main.py), tokens are HMAC-
signed base64url payloads rather than JWTs, and the "secret" protects a demo
deployment, not a clinic.

The three important properties:

1. The secret never appears in the code or the repo -- .env is gitignored.
2. Missing configuration fails loud at startup, not silent and insecure.
3. Tokens expire, so a leaked token is only useful for a few hours.
"""

import base64
import hashlib
import hmac
import json
import os
import time
import secrets

from fastapi import Header, HTTPException
from typing import Optional

# Import database lazily to avoid circular imports at module import time.
def _get_db():
    try:
        import database

        return database
    except Exception:
        return None

TOKEN_TTL_SECONDS = 8 * 60 * 60  # 8 hours -- one working day
ADMIN_EMAIL = "blessedbaidoo79@gmail.com"


def config() -> tuple[str, str, str]:
    """(staff_id, password, secret).

    STAFF_ID and STAFF_PASSWORD are optional in the new workflow: user
    accounts are stored in the database and the token secret is the only
    required configuration. Return (staff_id, staff_password, token_secret).
    """
    staff_id = os.environ.get("STAFF_ID", ADMIN_EMAIL).strip() or ADMIN_EMAIL
    password = os.environ.get("STAFF_PASSWORD", "")
    secret = os.environ.get("TOKEN_SECRET", "").strip()

    if not secret:
        raise RuntimeError(
            "Authentication misconfigured -- set TOKEN_SECRET (see backend/.env.example)."
        )
    if len(secret) < 16:
        raise RuntimeError(
            "TOKEN_SECRET is too short -- use at least 16 characters, preferably 32+."
        )
    return staff_id, password, secret


def login(staff_id: str, password: str) -> str:
    """Issue a signed token if the credentials match the configured ones."""
    expected_id, expected_pw, secret = config()

    normalized_input = staff_id.strip()
    id_ok = hmac.compare_digest(normalized_input.lower().encode(), expected_id.lower().encode())
    pw_ok = hmac.compare_digest(password.encode(), expected_pw.encode())
    if not (id_ok and pw_ok):
        raise HTTPException(status_code=401, detail="Invalid staff ID or password.")

    payload = {"staff": expected_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).rstrip(b"=")
    signature = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).digest()
    tag = base64.urlsafe_b64encode(signature).rstrip(b"=")
    # "y2x" is an eyes-only marker; the format is ours, not a JWT.
    return "y2x." + body.decode() + "." + tag.decode()


def _issue_token(identity: str) -> str:
    """Issue a token for `identity` (staff or user email)."""
    secret = config()[2]
    payload = {"staff": identity, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    tag = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return "y2x." + body.decode() + "." + tag.decode()


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    """Return (hash_hex, salt_hex). Uses PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return dk.hex(), salt.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return hmac.compare_digest(dk, expected)


def user_login(email: str, password: str) -> str:
    """Authenticate a user account stored in the database and return a token."""
    db = _get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable for user authentication.")
    auth = db.get_user_auth(email)
    if not auth:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    if not verify_password(password, auth["password_salt"], auth["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return _issue_token(email)


def is_admin_identity(identity: str) -> bool:
    """Return True if identity string represents an admin account.

    Identity may be the configured STAFF_ID or a user email with `is_admin` flag.
    """
    if identity.lower() == ADMIN_EMAIL.lower():
        return True
    db = _get_db()
    if db is None:
        return False
    info = db.get_user_auth(identity)
    if not info:
        return False
    return bool(info.get("is_admin", False))


def authenticate(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: validate the Bearer token, return the staff id."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401, detail="Missing access token -- log in again."
        )
    token = authorization[7:].strip()
    try:
        _, body, signature = token.split(".")
        raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        tag = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
    except (ValueError, TypeError) as err:
        raise HTTPException(status_code=401, detail="Malformed access token.") from err

    expected = hmac.new(
        config()[2].encode(), body.encode(), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(tag, expected):
        raise HTTPException(status_code=401, detail="Invalid access token.")

    payload = json.loads(raw)
    if int(payload.get("exp", 0)) < time.time():
        raise HTTPException(status_code=401, detail="Session expired -- log in again.")

    return payload.get("staff", "staff")
