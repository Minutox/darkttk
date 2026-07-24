from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import httpx

from .config import get_settings


class TikTokApiError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        log_id: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.log_id = log_id
        self.retryable = retryable


@dataclass(frozen=True)
class TikTokTokens:
    open_id: str
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int
    scopes: list[str]


@dataclass(frozen=True)
class TikTokPublishInit:
    publish_id: str
    upload_url: str | None
    log_id: str | None


@dataclass(frozen=True)
class TikTokPostStatus:
    status: str
    fail_reason: str | None
    post_ids: list[str]
    log_id: str | None


def _raise_for_api_error(response: httpx.Response) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError as error:
        raise TikTokApiError(
            "invalid_provider_response",
            "TikTok returned a non-JSON response.",
            retryable=response.status_code >= 500,
        ) from error
    error_data = payload.get("error") or {}
    if isinstance(error_data, str):
        code = error_data
        message = str(payload.get("error_description") or error_data)
        log_id = payload.get("log_id")
    else:
        code = str(error_data.get("code") or "ok")
        message = str(error_data.get("message") or "")
        log_id = error_data.get("log_id")
    if response.status_code >= 400 or code != "ok":
        retryable = (
            response.status_code == 429
            or response.status_code >= 500
            or code in {"internal_error", "rate_limit_exceeded", "temporarily_unavailable"}
        )
        raise TikTokApiError(code, message or code, log_id=log_id, retryable=retryable)
    return payload


class TikTokClient:
    is_mock = False

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base = self.settings.tiktok_api_base.rstrip("/")

    def _credentials(self) -> None:
        if not (
            self.settings.tiktok_client_key
            and self.settings.tiktok_client_secret
            and self.settings.tiktok_redirect_uri
        ):
            raise TikTokApiError(
                "provider_not_configured",
                "TikTok credentials and redirect URI are not configured.",
            )

    def exchange_code(self, code: str) -> TikTokTokens:
        self._credentials()
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{self.base}/v2/oauth/token/",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": self.settings.tiktok_client_key,
                    "client_secret": self.settings.tiktok_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.settings.tiktok_redirect_uri,
                },
            )
        payload = _raise_for_api_error(response)
        return self._tokens(payload)

    def refresh(self, refresh_token: str) -> TikTokTokens:
        self._credentials()
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{self.base}/v2/oauth/token/",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": self.settings.tiktok_client_key,
                    "client_secret": self.settings.tiktok_client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
        return self._tokens(_raise_for_api_error(response))

    def revoke(self, access_token: str) -> None:
        self._credentials()
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{self.base}/v2/oauth/revoke/",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": self.settings.tiktok_client_key,
                    "client_secret": self.settings.tiktok_client_secret,
                    "token": access_token,
                },
            )
        if response.status_code >= 400:
            _raise_for_api_error(response)

    def creator_info(self, access_token: str) -> dict[str, object]:
        payload = self._post_json(
            "/v2/post/publish/creator_info/query/", access_token, {}
        )
        return dict(payload.get("data") or {})

    def initialize_video(
        self,
        access_token: str,
        *,
        mode: str,
        post_info: dict[str, object],
        video_size: int,
        chunk_size: int,
        total_chunk_count: int,
    ) -> TikTokPublishInit:
        path = (
            "/v2/post/publish/video/init/"
            if mode == "direct_post"
            else "/v2/post/publish/inbox/video/init/"
        )
        body: dict[str, object] = {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunk_count,
            }
        }
        if mode == "direct_post":
            body["post_info"] = post_info
        payload = self._post_json(path, access_token, body)
        data = dict(payload.get("data") or {})
        error_data = dict(payload.get("error") or {})
        return TikTokPublishInit(
            publish_id=str(data["publish_id"]),
            upload_url=str(data["upload_url"]) if data.get("upload_url") else None,
            log_id=error_data.get("log_id"),
        )

    def upload_video(
        self,
        upload_url: str,
        path: Path,
        *,
        chunk_size: int,
        total_chunk_count: int,
    ) -> None:
        total = path.stat().st_size
        with path.open("rb") as source, httpx.Client(timeout=120) as client:
            offset = 0
            for index in range(total_chunk_count):
                remaining = total - offset
                read_size = remaining if index == total_chunk_count - 1 else chunk_size
                chunk = source.read(read_size)
                end = offset + len(chunk) - 1
                response = client.put(
                    upload_url,
                    headers={
                        "Content-Type": "video/mp4",
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"bytes {offset}-{end}/{total}",
                    },
                    content=chunk,
                )
                if response.status_code not in (200, 201, 206):
                    raise TikTokApiError(
                        "media_upload_failed",
                        f"TikTok media upload failed with HTTP {response.status_code}.",
                        retryable=response.status_code >= 500,
                    )
                offset = end + 1

    def fetch_status(self, access_token: str, publish_id: str) -> TikTokPostStatus:
        payload = self._post_json(
            "/v2/post/publish/status/fetch/",
            access_token,
            {"publish_id": publish_id},
        )
        data = dict(payload.get("data") or {})
        error_data = dict(payload.get("error") or {})
        raw_ids = data.get("publicaly_available_post_id") or []
        return TikTokPostStatus(
            status=str(data.get("status") or "UNKNOWN"),
            fail_reason=str(data["fail_reason"]) if data.get("fail_reason") else None,
            post_ids=[str(item) for item in raw_ids],
            log_id=error_data.get("log_id"),
        )

    def query_video_metrics(
        self, access_token: str, video_ids: list[str]
    ) -> list[dict[str, object]]:
        fields = "id,create_time,duration,title,like_count,comment_count,share_count,view_count"
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{self.base}/v2/video/query/",
                params={"fields": fields},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"filters": {"video_ids": video_ids[:20]}},
            )
        payload = _raise_for_api_error(response)
        return [dict(item) for item in dict(payload.get("data") or {}).get("videos") or []]

    def query_account_metrics(self, access_token: str) -> dict[str, object]:
        fields = "open_id,follower_count,following_count,likes_count,video_count"
        with httpx.Client(timeout=30) as client:
            response = client.get(
                f"{self.base}/v2/user/info/",
                params={"fields": fields},
                headers={"Authorization": f"Bearer {access_token}"},
            )
        payload = _raise_for_api_error(response)
        return dict(dict(payload.get("data") or {}).get("user") or {})

    def _post_json(
        self, path: str, access_token: str, body: dict[str, object]
    ) -> dict[str, object]:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{self.base}{path}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                json=body,
            )
        return _raise_for_api_error(response)

    @staticmethod
    def _tokens(payload: dict[str, object]) -> TikTokTokens:
        return TikTokTokens(
            open_id=str(payload["open_id"]),
            access_token=str(payload["access_token"]),
            refresh_token=str(payload["refresh_token"]),
            expires_in=int(payload["expires_in"]),
            refresh_expires_in=int(payload["refresh_expires_in"]),
            scopes=[item for item in str(payload.get("scope") or "").split(",") if item],
        )


class MockTikTokClient:
    is_mock = True

    def exchange_code(self, code: str) -> TikTokTokens:
        return self._tokens()

    def refresh(self, refresh_token: str) -> TikTokTokens:
        return self._tokens()

    def revoke(self, access_token: str) -> None:
        return None

    def creator_info(self, access_token: str) -> dict[str, object]:
        return {
            "creator_username": "darkttk_mock",
            "creator_nickname": "Conta TikTok simulada",
            "creator_avatar_url": None,
            "privacy_level_options": [
                "PUBLIC_TO_EVERYONE",
                "MUTUAL_FOLLOW_FRIENDS",
                "SELF_ONLY",
            ],
            "comment_disabled": False,
            "duet_disabled": False,
            "stitch_disabled": False,
            "max_video_post_duration_sec": 600,
            "mock": True,
        }

    def initialize_video(self, *args, **kwargs) -> TikTokPublishInit:
        return TikTokPublishInit(f"mock-publish-{uuid4().hex}", None, "mock-log")

    def upload_video(self, *args, **kwargs) -> None:
        return None

    def fetch_status(self, access_token: str, publish_id: str) -> TikTokPostStatus:
        return TikTokPostStatus("PUBLISH_COMPLETE", None, [], "mock-log")

    def query_video_metrics(
        self, access_token: str, video_ids: list[str]
    ) -> list[dict[str, object]]:
        results = []
        for video_id in video_ids:
            seed = sum(ord(character) for character in video_id)
            views = 12_000 + seed * 17
            results.append(
                {
                    "id": video_id,
                    "view_count": views,
                    "like_count": int(views * 0.082),
                    "comment_count": int(views * 0.006),
                    "share_count": int(views * 0.014),
                }
            )
        return results

    def query_account_metrics(self, access_token: str) -> dict[str, object]:
        return {
            "follower_count": 28_460,
            "following_count": 164,
            "likes_count": 918_200,
            "video_count": 186,
        }

    @staticmethod
    def _tokens() -> TikTokTokens:
        return TikTokTokens(
            open_id="mock-open-id",
            access_token=f"mock-access-{uuid4().hex}",
            refresh_token=f"mock-refresh-{uuid4().hex}",
            expires_in=86_400,
            refresh_expires_in=31_536_000,
            scopes=[
                "user.info.basic",
                "user.info.stats",
                "video.list",
                "video.publish",
                "video.upload",
            ],
        )


def get_tiktok_client() -> TikTokClient | MockTikTokClient:
    mode = get_settings().tiktok_mode
    if mode == "mock":
        return MockTikTokClient()
    if mode == "official":
        return TikTokClient()
    raise TikTokApiError(
        "publishing_disabled",
        "TikTok publishing is disabled until official credentials are configured.",
    )
