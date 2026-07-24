import base64
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken

from .config import get_settings


class TokenCipher:
    def __init__(self) -> None:
        settings = get_settings()
        source = settings.encryption_key or settings.app_secret
        if settings.app_env == "production" and not settings.encryption_key:
            raise RuntimeError("ENCRYPTION_KEY is required in production")
        key = base64.urlsafe_b64encode(sha256(source.encode("utf-8")).digest())
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as error:
            raise RuntimeError("Unable to decrypt stored secret") from error
