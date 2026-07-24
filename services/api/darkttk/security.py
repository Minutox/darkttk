from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from .config import get_settings

password_hash = PasswordHash.recommended()


@dataclass(frozen=True)
class TokenBundle:
    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_jti: str
    refresh_expires_at: datetime


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def token_digest(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def create_token_bundle(user_id: str, organization_id: str, role: str) -> TokenBundle:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    access_exp = now + timedelta(minutes=settings.access_token_minutes)
    refresh_exp = now + timedelta(days=settings.refresh_token_days)
    refresh_jti = str(uuid4())
    common = {
        "sub": user_id,
        "org": organization_id,
        "role": role,
        "iat": now,
        "iss": "darkttk-api",
        "aud": "darkttk-web",
    }
    access_token = jwt.encode(
        {**common, "type": "access", "jti": str(uuid4()), "exp": access_exp},
        settings.app_secret,
        algorithm="HS256",
    )
    refresh_token = jwt.encode(
        {**common, "type": "refresh", "jti": refresh_jti, "exp": refresh_exp},
        settings.app_secret,
        algorithm="HS256",
    )
    return TokenBundle(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_in=settings.access_token_minutes * 60,
        refresh_jti=refresh_jti,
        refresh_expires_at=refresh_exp,
    )


def decode_token(token: str, expected_type: str) -> dict[str, str]:
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.app_secret,
        algorithms=["HS256"],
        audience="darkttk-web",
        issuer="darkttk-api",
        options={"require": ["sub", "org", "role", "type", "jti", "exp"]},
    )
    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError("Unexpected token type")
    return payload
