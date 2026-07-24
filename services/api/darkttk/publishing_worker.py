import json
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

from .config import get_settings
from .database import SessionLocal
from .models import (
    MediaAsset,
    Notification,
    PublicationEvent,
    PublicationJob,
    PublicationStatus,
    ScheduledSlot,
    TikTokConnection,
    TikTokConnectionStatus,
    VideoProject,
    utcnow,
)
from .storage import LocalObjectStorage
from .tiktok_client import TikTokApiError, get_tiktok_client
from .token_crypto import TokenCipher

TERMINAL_STATUSES = {
    PublicationStatus.PUBLISHED.value,
    PublicationStatus.FAILED.value,
    PublicationStatus.DEAD_LETTER.value,
    PublicationStatus.CANCELLED.value,
    PublicationStatus.INBOX_DELIVERED.value,
    PublicationStatus.MOCK_COMPLETE.value,
}
NON_RETRYABLE_REASONS = {
    "auth_removed",
    "scope_not_authorized",
    "invalid_param",
    "duration_check_failed",
    "frame_rate_check_failed",
    "picture_size_check_failed",
    "file_format_check_failed",
    "spam_risk",
    "spam_risk_text",
    "spam_risk_user_banned_from_posting",
    "unaudited_client_can_only_post_to_private_accounts",
    "privacy_level_option_mismatch",
}


def chunk_plan(size: int) -> tuple[int, int]:
    five_mb = 5 * 1024 * 1024
    ten_mb = 10 * 1024 * 1024
    if size < five_mb:
        return size, 1
    count = max(1, size // ten_mb)
    return (size if count == 1 else ten_mb), count


def add_event(
    db,
    job: PublicationJob,
    event_type: str,
    payload: dict[str, object] | None = None,
) -> None:
    db.add(
        PublicationEvent(
            organization_id=job.organization_id,
            publication_job_id=job.id,
            event_type=event_type,
            payload_json=json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":")),
        )
    )


def notify(db, job: PublicationJob, title: str, message: str) -> None:
    db.add(
        Notification(
            organization_id=job.organization_id,
            recipient_id=job.requested_by,
            kind="publication_status",
            title=title,
            message=message,
            entity_type="publication_job",
            entity_id=job.id,
        )
    )


def access_token_for(connection: TikTokConnection) -> str:
    cipher = TokenCipher()
    client = get_tiktok_client()
    now = utcnow()
    access = cipher.decrypt(connection.access_token_ciphertext)
    expires_at = connection.access_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    if expires_at > now + timedelta(minutes=5):
        return access
    refreshed = client.refresh(cipher.decrypt(connection.refresh_token_ciphertext))
    connection.access_token_ciphertext = cipher.encrypt(refreshed.access_token)
    connection.refresh_token_ciphertext = cipher.encrypt(refreshed.refresh_token)
    connection.access_expires_at = now + timedelta(seconds=refreshed.expires_in)
    connection.refresh_expires_at = now + timedelta(seconds=refreshed.refresh_expires_in)
    connection.scopes_json = json.dumps(refreshed.scopes)
    connection.status = TikTokConnectionStatus.ACTIVE.value
    return refreshed.access_token


def execute_publication_job(job_id: str) -> str:
    with SessionLocal() as db:
        job = db.get(PublicationJob, job_id)
        if job is None or job.status in TERMINAL_STATUSES:
            return "stop"
        connection = db.get(TikTokConnection, job.connection_id)
        slot = db.get(ScheduledSlot, job.scheduled_slot_id)
        project = db.get(VideoProject, job.video_project_id)
        asset = db.get(MediaAsset, job.output_asset_id)
        if not connection or connection.status != TikTokConnectionStatus.ACTIVE.value:
            _fail(db, job, "connection_unavailable", "A conexão TikTok não está ativa.", False)
            return "stop"
        if not slot or not project or not asset:
            _fail(db, job, "publication_dependency_missing", "Dados da publicação não foram encontrados.", False)
            return "stop"
        job.attempts += 1
        if job.is_mock:
            job.status = PublicationStatus.MOCK_COMPLETE.value
            add_event(db, job, "mock.completed", {"notice": "Nenhum conteúdo foi enviado ao TikTok."})
            notify(
                db,
                job,
                "Simulação de publicação concluída",
                f"“{project.title}” não foi enviado ao TikTok.",
            )
            db.commit()
            return "stop"
        try:
            if asset.mime_type != "video/mp4" or asset.is_mock:
                raise TikTokApiError(
                    "real_render_required",
                    "A publicação oficial exige um render MP4 real.",
                )
            media_path = LocalObjectStorage().resolve(asset.storage_key)
            size = media_path.stat().st_size
            if size > 4 * 1024 * 1024 * 1024:
                raise TikTokApiError("video_too_large", "O vídeo excede 4 GB.")
            client = get_tiktok_client()
            access_token = access_token_for(connection)
            chunk_size, chunk_count = chunk_plan(size)
            job.status = PublicationStatus.INITIALIZING.value
            add_event(db, job, "provider.initializing")
            db.commit()
            post_info = {
                "title": job.caption,
                "privacy_level": job.privacy_level,
                "disable_comment": job.disable_comment,
                "disable_duet": job.disable_duet,
                "disable_stitch": job.disable_stitch,
                "brand_content_toggle": job.brand_content_toggle,
                "brand_organic_toggle": job.brand_organic_toggle,
                "is_aigc": job.is_aigc,
            }
            initialized = client.initialize_video(
                access_token,
                mode=job.publish_mode,
                post_info=post_info,
                video_size=size,
                chunk_size=chunk_size,
                total_chunk_count=chunk_count,
            )
            job.publish_id = initialized.publish_id
            job.provider_log_id = initialized.log_id
            job.status = PublicationStatus.UPLOADING.value
            slot.status = "publishing"
            add_event(db, job, "provider.initialized", {"publish_id": initialized.publish_id})
            db.commit()
            if not initialized.upload_url:
                raise TikTokApiError("upload_url_missing", "TikTok não retornou URL de upload.")
            client.upload_video(
                initialized.upload_url,
                Path(media_path),
                chunk_size=chunk_size,
                total_chunk_count=chunk_count,
            )
            job.status = PublicationStatus.PROCESSING.value
            add_event(db, job, "media.uploaded")
            db.commit()
            return "poll"
        except TikTokApiError as error:
            if error.code in {"access_token_invalid", "auth_removed"}:
                connection.status = TikTokConnectionStatus.EXPIRED.value
                connection.last_error_code = error.code
            _fail(db, job, error.code, str(error), error.retryable)
            return (
                "retry"
                if error.retryable and job.status != PublicationStatus.DEAD_LETTER.value
                else "stop"
            )
        except Exception as error:
            _fail(db, job, type(error).__name__, str(error), True)
            return "retry" if job.status != PublicationStatus.DEAD_LETTER.value else "stop"


def poll_publication_job(job_id: str) -> bool:
    with SessionLocal() as db:
        job = db.get(PublicationJob, job_id)
        if (
            job is None
            or job.status in TERMINAL_STATUSES
            or not job.publish_id
        ):
            return False
        connection = db.get(TikTokConnection, job.connection_id)
        slot = db.get(ScheduledSlot, job.scheduled_slot_id)
        project = db.get(VideoProject, job.video_project_id)
        if not connection or not slot or not project:
            _fail(db, job, "publication_dependency_missing", "Dados da publicação não foram encontrados.", False)
            return False
        try:
            client = get_tiktok_client()
            result = client.fetch_status(access_token_for(connection), job.publish_id)
            job.provider_log_id = result.log_id or job.provider_log_id
            add_event(
                db,
                job,
                f"provider.{result.status.lower()}",
                {"fail_reason": result.fail_reason, "post_ids": result.post_ids},
            )
            if result.status == "PUBLISH_COMPLETE":
                if job.is_mock:
                    job.status = PublicationStatus.MOCK_COMPLETE.value
                else:
                    job.status = PublicationStatus.PUBLISHED.value
                    job.post_id = result.post_ids[0] if result.post_ids else None
                    slot.status = "published"
                    project.status = "published"
                    notify(db, job, "Publicação confirmada", f"“{project.title}” foi publicado pelo TikTok.")
                db.commit()
                return False
            if result.status == "SEND_TO_USER_INBOX":
                job.status = PublicationStatus.INBOX_DELIVERED.value
                slot.status = "ready"
                notify(
                    db,
                    job,
                    "Rascunho entregue no TikTok",
                    f"Finalize “{project.title}” no aplicativo TikTok.",
                )
                db.commit()
                return False
            if result.status == "FAILED":
                retryable = (result.fail_reason or "") not in NON_RETRYABLE_REASONS
                _fail(
                    db,
                    job,
                    result.fail_reason or "provider_failed",
                    "O TikTok rejeitou ou não concluiu a publicação.",
                    retryable,
                )
                return retryable and job.status != PublicationStatus.DEAD_LETTER.value
            job.status = PublicationStatus.PROCESSING.value
            db.commit()
            return True
        except TikTokApiError as error:
            _fail(db, job, error.code, str(error), error.retryable)
            return error.retryable and job.status != PublicationStatus.DEAD_LETTER.value


def mark_publication_poll_timeout(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(PublicationJob, job_id)
        if job and job.status not in TERMINAL_STATUSES:
            job.attempts = get_settings().publishing_max_attempts
            _fail(
                db,
                job,
                "provider_confirmation_timeout",
                "O TikTok não confirmou o processamento dentro do prazo operacional.",
                True,
            )


def _fail(
    db,
    job: PublicationJob,
    code: str,
    message: str,
    retryable: bool,
) -> None:
    max_attempts = get_settings().publishing_max_attempts
    if retryable:
        job.attempts += 1
    job.error_code = code[:120]
    job.error_message = message[:1000]
    job.status = (
        PublicationStatus.PROCESSING.value
        if retryable and job.attempts < max_attempts
        else PublicationStatus.DEAD_LETTER.value
        if retryable
        else PublicationStatus.FAILED.value
    )
    add_event(db, job, "publication.error", {"code": code, "retryable": retryable})
    if job.status in {PublicationStatus.FAILED.value, PublicationStatus.DEAD_LETTER.value}:
        slot = db.get(ScheduledSlot, job.scheduled_slot_id)
        if slot:
            slot.status = "failed"
        notify(db, job, "Falha na publicação", message[:300])
    db.commit()
