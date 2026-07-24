from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
import time
from dataclasses import dataclass
from urllib.parse import quote
from urllib.request import Request, urlopen

from .config import get_settings
from .models import MfaCredential
from .token_crypto import TokenCipher


def random_token() -> str:
    return secrets.token_urlsafe(32)


def recovery_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _secret_bytes(secret: str) -> bytes:
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(padded, casefold=True)


def totp_code(secret: str, step: int | None = None) -> tuple[str, int]:
    current_step = step if step is not None else int(time.time() // 30)
    digest = hmac.new(
        _secret_bytes(secret),
        struct.pack(">Q", current_step),
        hashlib.sha1,
    ).digest()
    offset = digest[-1] & 0x0F
    number = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{number:06d}", current_step


def verify_totp(secret: str, value: str, *, last_used_step: int | None = None) -> int | None:
    normalized = value.replace(" ", "")
    current = int(time.time() // 30)
    for step in range(current - 1, current + 2):
        expected, _ = totp_code(secret, step)
        if hmac.compare_digest(normalized, expected) and (
            last_used_step is None or step > last_used_step
        ):
            return step
    return None


def provisioning_uri(secret: str, email: str) -> str:
    issuer = "DarkTTK"
    return (
        f"otpauth://totp/{quote(issuer)}:{quote(email)}"
        f"?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
    )


def generate_recovery_codes() -> list[str]:
    return [f"{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}" for _ in range(8)]


def set_recovery_codes(credential: MfaCredential, codes: list[str]) -> None:
    credential.recovery_codes_json = json.dumps(
        [recovery_digest(code) for code in codes], separators=(",", ":")
    )


def consume_mfa_code(credential: MfaCredential, value: str) -> bool:
    secret = TokenCipher().decrypt(credential.secret_ciphertext)
    step = verify_totp(secret, value, last_used_step=credential.last_used_step)
    if step is not None:
        credential.last_used_step = step
        return True
    code_hash = recovery_digest(value.strip().upper())
    hashes = json.loads(credential.recovery_codes_json or "[]")
    if code_hash not in hashes:
        return False
    hashes.remove(code_hash)
    credential.recovery_codes_json = json.dumps(hashes, separators=(",", ":"))
    return True


@dataclass(frozen=True)
class DeliveryResult:
    mode: str
    development_token: str | None = None


def deliver_password_recovery(email: str, raw_token: str) -> DeliveryResult:
    settings = get_settings()
    mode = settings.account_delivery_mode.lower()
    if mode == "mock":
        return DeliveryResult(mode="mock", development_token=raw_token)
    if mode == "resend":
        recovery_url = f"{settings.password_recovery_url}?token={quote(raw_token)}"
        payload = json.dumps(
            {
                "from": settings.account_email_from,
                "to": [email],
                "subject": "Redefina sua senha do DarkTTK",
                "html": (
                    "<p>Recebemos uma solicitação para redefinir sua senha.</p>"
                    f'<p><a href="{recovery_url}">Redefinir senha</a></p>'
                    "<p>Se não foi você, ignore esta mensagem.</p>"
                ),
            }
        ).encode("utf-8")
        request = Request(
            "https://api.resend.com/emails",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "DarkTTK/1.0",
            },
        )
        with urlopen(request, timeout=10) as response:
            if response.status < 200 or response.status >= 300:
                raise RuntimeError("password_recovery_delivery_failed")
        return DeliveryResult(mode="resend")
    return DeliveryResult(mode="disabled")
