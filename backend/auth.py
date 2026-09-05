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

from fastapi import Header, HTTPException

TOKEN_TTL_SECONDS = 8 * 60 * 60  # 8 hours -- one working day


def config() -> tuple[str, str, str]:
    """(staff_id, password, secret); raises if any piece is missing."""
    staff_id = os.environ.get("STAFF_ID", "").strip()
    password = os.environ.get("STAFF_PASSWORD", "")
    secret = os.environ.get("TOKEN_SECRET", "").strip()

    missing = [
        name
        for name, value in (
            ("STAFF_ID", staff_id),
            ("STAFF_PASSWORD", password),
            ("TOKEN_SECRET", secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Authentication is misconfigured -- set " + ", ".join(missing)
            + " (a `.env` file next to main.py is fine; see backend/.env.example)."
        )
    if len(secret) < 16:
        raise RuntimeError(
            "TOKEN_SECRET is too short -- use at least 16 characters, "
            "preferably 32+ from `python -c \"import secrets; print(secrets.token_urlsafe(32))\"`."
        )
    return staff_id, password, secret


def login(staff_id: str, password: str) -> str:
    """Issue a signed token if the credentials match the configured ones."""
    expected_id, expected_pw, secret = config()

    id_ok = hmac.compare_digest(staff_id.strip().encode(), expected_id.encode())
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
