from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from .config import get_settings

MIME_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "video/mp4": ".mp4",
    "audio/wav": ".wav",
    "audio/mpeg": ".mp3",
    "text/plain": ".txt",
    "application/json": ".json",
}
KIND_MIMES = {
    "image": {"image/png", "image/jpeg"},
    "video": {"video/mp4"},
    "audio": {"audio/wav", "audio/mpeg"},
    "caption": {"text/plain"},
    "render": {"video/mp4", "application/json"},
    "document": {"application/json", "text/plain"},
}


@dataclass(frozen=True)
class StoredObject:
    key: str
    size_bytes: int
    sha256: str
    mime_type: str


def detected_mime(header: bytes) -> str | None:
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "video/mp4"
    if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        return "audio/wav"
    if header.startswith(b"ID3") or header[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"
    return None


class LocalObjectStorage:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root = Path(self.settings.media_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _destination(self, organization_id: str, kind: str, extension: str) -> tuple[str, Path]:
        key = f"org/{organization_id}/{kind}/{uuid4().hex}{extension}"
        destination = (self.root / key).resolve()
        if self.root not in destination.parents:
            raise ValueError("Invalid storage path")
        destination.parent.mkdir(parents=True, exist_ok=True)
        return key, destination

    async def save_upload(
        self, upload: UploadFile, *, organization_id: str, kind: str
    ) -> StoredObject:
        claimed = (upload.content_type or "").lower()
        if claimed not in KIND_MIMES.get(kind, set()):
            raise ValueError("Unsupported media type for asset kind")
        extension = MIME_EXTENSIONS[claimed]
        key, destination = self._destination(organization_id, kind, extension)
        digest = sha256()
        size = 0
        header = b""
        try:
            with destination.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    if not header:
                        header = chunk[:32]
                    size += len(chunk)
                    if size > self.settings.max_upload_bytes:
                        raise ValueError("Upload exceeds configured size limit")
                    digest.update(chunk)
                    output.write(chunk)
            actual = detected_mime(header)
            if actual != claimed:
                raise ValueError("File signature does not match declared media type")
            return StoredObject(key, size, digest.hexdigest(), actual)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    def save_bytes(
        self,
        content: bytes,
        *,
        organization_id: str,
        kind: str,
        mime_type: str,
    ) -> StoredObject:
        if mime_type not in KIND_MIMES.get(kind, set()):
            raise ValueError("Unsupported media type for asset kind")
        key, destination = self._destination(
            organization_id, kind, MIME_EXTENSIONS[mime_type]
        )
        destination.write_bytes(content)
        return StoredObject(key, len(content), sha256(content).hexdigest(), mime_type)

    def resolve(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents or not path.is_file():
            raise FileNotFoundError(key)
        return path

    def delete(self, key: str) -> None:
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid storage path")
        path.unlink(missing_ok=True)
