import json

from .database import SessionLocal
from .models import (
    AccountMetricSnapshot,
    PublicationJob,
    PublicationMetricSnapshot,
    PublicationStatus,
    TikTokConnection,
    utcnow,
)
from .publishing_worker import access_token_for
from .tiktok_client import TikTokApiError, get_tiktok_client


def sync_publication_metrics(job_id: str) -> str:
    with SessionLocal() as db:
        job = db.get(PublicationJob, job_id)
        if job is None:
            return "missing"
        if job.status not in {
            PublicationStatus.PUBLISHED.value,
            PublicationStatus.MOCK_COMPLETE.value,
        }:
            return "not_published"
        connection = db.get(TikTokConnection, job.connection_id)
        if connection is None or connection.status != "active":
            return "connection_unavailable"
        scopes = set(json.loads(connection.scopes_json))
        if not connection.is_mock and "video.list" not in scopes:
            return "scope_not_authorized"
        provider_video_id = job.post_id or f"mock-{job.id}"
        client = get_tiktok_client()
        try:
            access_token = access_token_for(connection)
            videos = client.query_video_metrics(access_token, [provider_video_id])
            if not videos:
                return "provider_video_missing"
            video = videos[0]
            db.add(
                PublicationMetricSnapshot(
                    organization_id=job.organization_id,
                    publication_job_id=job.id,
                    provider_video_id=str(video.get("id") or provider_video_id),
                    view_count=max(0, int(video.get("view_count") or 0)),
                    like_count=max(0, int(video.get("like_count") or 0)),
                    comment_count=max(0, int(video.get("comment_count") or 0)),
                    share_count=max(0, int(video.get("share_count") or 0)),
                    source="mock_display_api" if connection.is_mock else "tiktok_display_api",
                    is_mock=connection.is_mock,
                    collected_at=utcnow(),
                )
            )
            if connection.is_mock or "user.info.stats" in scopes:
                account = client.query_account_metrics(access_token)
                db.add(
                    AccountMetricSnapshot(
                        organization_id=job.organization_id,
                        connection_id=connection.id,
                        follower_count=max(0, int(account.get("follower_count") or 0)),
                        following_count=max(0, int(account.get("following_count") or 0)),
                        likes_count=max(0, int(account.get("likes_count") or 0)),
                        video_count=max(0, int(account.get("video_count") or 0)),
                        source="mock_display_api" if connection.is_mock else "tiktok_display_api",
                        is_mock=connection.is_mock,
                        collected_at=utcnow(),
                    )
                )
            db.commit()
            return "synced"
        except TikTokApiError as error:
            return error.code
