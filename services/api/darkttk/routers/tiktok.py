import hmac
import json
import secrets
import time
from datetime import timedelta, timezone
from hashlib import sha256
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select

from ..audit import write_audit
from ..config import get_settings
from ..dependencies import AuthContext, CurrentAuth, DbSession, require_roles
from ..models import (
    MediaAsset,
    Notification,
    PublicationEvent,
    PublicationJob,
    PublicationStatus,
    RenderJob,
    Role,
    ScheduledSlot,
    TikTokConnection,
    TikTokConnectionStatus,
    TikTokOAuthState,
    TikTokWebhookReceipt,
    VideoProject,
    utcnow,
)
from ..publishing_worker import (
    TERMINAL_STATUSES,
    access_token_for,
    add_event,
    execute_publication_job,
    notify,
)
from ..queueing import enqueue_publication
from ..tiktok_client import TikTokApiError, get_tiktok_client
from ..tiktok_schemas import (
    CreatorInfoResponse,
    OAuthAuthorizeResponse,
    PublicationCreateRequest,
    PublicationEventResponse,
    PublicationJobResponse,
    PublicationRetryRequest,
    TikTokConnectionResponse,
)
from ..token_crypto import TokenCipher

router = APIRouter(prefix="/v1/tiktok", tags=["TikTok"])
CONNECT_ROLES = (Role.ADMIN.value, Role.MANAGER.value)
PUBLISH_ROLES = (Role.ADMIN.value, Role.MANAGER.value)
SCOPES = "user.info.basic,user.info.stats,video.list,video.publish,video.upload"


def provider_error(error: TikTokApiError) -> HTTPException:
    return HTTPException(
        status_code=503 if error.retryable else 422,
        detail={"code": error.code, "message": str(error), "log_id": error.log_id},
    )


def connection_response(connection: TikTokConnection) -> TikTokConnectionResponse:
    return TikTokConnectionResponse(
        id=connection.id,
        open_id=connection.open_id,
        display_name=connection.display_name,
        avatar_url=connection.avatar_url,
        scopes=json.loads(connection.scopes_json),
        status=connection.status,
        is_mock=connection.is_mock,
        access_expires_at=connection.access_expires_at,
        refresh_expires_at=connection.refresh_expires_at,
        creator_info_fetched_at=connection.creator_info_fetched_at,
    )


def owned_connection(db: DbSession, organization_id: str, connection_id: str) -> TikTokConnection:
    connection = db.scalar(
        select(TikTokConnection).where(
            TikTokConnection.id == connection_id,
            TikTokConnection.organization_id == organization_id,
        )
    )
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return connection


def job_response(
    db: DbSession, job: PublicationJob, *, include_events: bool = False
) -> PublicationJobResponse:
    events: list[PublicationEventResponse] = []
    if include_events:
        rows = db.scalars(
            select(PublicationEvent)
            .where(PublicationEvent.publication_job_id == job.id)
            .order_by(PublicationEvent.created_at)
        )
        events = [PublicationEventResponse.model_validate(item) for item in rows]
    return PublicationJobResponse(
        id=job.id,
        video_project_id=job.video_project_id,
        scheduled_slot_id=job.scheduled_slot_id,
        connection_id=job.connection_id,
        publish_mode=job.publish_mode,
        status=job.status,
        caption=job.caption,
        privacy_level=job.privacy_level,
        scheduled_for=job.scheduled_for,
        publish_id=job.publish_id,
        post_id=job.post_id,
        attempts=job.attempts,
        error_code=job.error_code,
        error_message=job.error_message,
        is_mock=job.is_mock,
        created_at=job.created_at,
        updated_at=job.updated_at,
        events=events,
    )


def save_connection(
    db: DbSession,
    *,
    organization_id: str,
    user_id: str,
    tokens,
    is_mock: bool,
) -> TikTokConnection:
    now = utcnow()
    cipher = TokenCipher()
    connection = db.scalar(
        select(TikTokConnection).where(
            TikTokConnection.organization_id == organization_id,
            TikTokConnection.open_id == tokens.open_id,
        )
    )
    if connection is None:
        connection = TikTokConnection(
            organization_id=organization_id,
            connected_by=user_id,
            open_id=tokens.open_id,
            access_token_ciphertext="",
            refresh_token_ciphertext="",
            access_expires_at=now,
            refresh_expires_at=now,
        )
        db.add(connection)
    connection.connected_by = user_id
    connection.access_token_ciphertext = cipher.encrypt(tokens.access_token)
    connection.refresh_token_ciphertext = cipher.encrypt(tokens.refresh_token)
    connection.scopes_json = json.dumps(tokens.scopes)
    connection.access_expires_at = now + timedelta(seconds=tokens.expires_in)
    connection.refresh_expires_at = now + timedelta(seconds=tokens.refresh_expires_in)
    connection.status = TikTokConnectionStatus.ACTIVE.value
    connection.is_mock = is_mock
    connection.last_error_code = None
    db.flush()
    return connection


@router.get("/oauth/authorize", response_model=OAuthAuthorizeResponse)
def authorize_tiktok(
    db: DbSession,
    context: AuthContext = Depends(require_roles(*CONNECT_ROLES)),
    redirect_after: str = Query(default="/"),
):
    settings = get_settings()
    if settings.tiktok_mode != "official":
        raise HTTPException(
            status_code=409,
            detail={"code": "official_mode_required", "message": "Ative TIKTOK_MODE=official."},
        )
    if not settings.tiktok_client_key or not settings.tiktok_redirect_uri:
        raise HTTPException(
            status_code=503,
            detail={"code": "provider_not_configured", "message": "Configure o aplicativo TikTok."},
        )
    if not redirect_after.startswith("/") or redirect_after.startswith("//"):
        raise HTTPException(status_code=422)
    raw_state = secrets.token_urlsafe(32)
    expires_at = utcnow() + timedelta(minutes=10)
    db.add(
        TikTokOAuthState(
            state_hash=sha256(raw_state.encode()).hexdigest(),
            organization_id=context.membership.organization_id,
            user_id=context.user.id,
            redirect_after=redirect_after,
            expires_at=expires_at,
        )
    )
    db.commit()
    query = urlencode(
        {
            "client_key": settings.tiktok_client_key,
            "scope": SCOPES,
            "response_type": "code",
            "redirect_uri": settings.tiktok_redirect_uri,
            "state": raw_state,
        }
    )
    return OAuthAuthorizeResponse(
        authorization_url=f"{settings.tiktok_authorize_url}?{query}",
        expires_at=expires_at,
    )


@router.get("/oauth/callback", response_model=TikTokConnectionResponse)
def oauth_callback(code: str, state: str, db: DbSession):
    now = utcnow()
    state_row = db.scalar(
        select(TikTokOAuthState).where(
            TikTokOAuthState.state_hash == sha256(state.encode()).hexdigest()
        )
    )
    if state_row is None or state_row.consumed_at is not None:
        raise HTTPException(status_code=400, detail={"code": "invalid_oauth_state"})
    expiry = state_row.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry < now:
        raise HTTPException(status_code=400, detail={"code": "expired_oauth_state"})
    state_row.consumed_at = now
    try:
        client = get_tiktok_client()
        tokens = client.exchange_code(code)
        connection = save_connection(
            db,
            organization_id=state_row.organization_id,
            user_id=state_row.user_id,
            tokens=tokens,
            is_mock=client.is_mock,
        )
        write_audit(
            db,
            organization_id=state_row.organization_id,
            actor_id=state_row.user_id,
            action="tiktok.connected",
            entity_type="tiktok_connection",
            entity_id=connection.id,
            metadata={"scopes": tokens.scopes},
        )
        db.commit()
        return connection_response(connection)
    except TikTokApiError as error:
        db.commit()
        raise provider_error(error) from error


@router.post(
    "/connections/mock",
    response_model=TikTokConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_mock_connection(
    db: DbSession,
    context: AuthContext = Depends(require_roles(*CONNECT_ROLES)),
):
    settings = get_settings()
    if settings.tiktok_mode != "mock":
        raise HTTPException(status_code=404)
    client = get_tiktok_client()
    connection = save_connection(
        db,
        organization_id=context.membership.organization_id,
        user_id=context.user.id,
        tokens=client.exchange_code("mock"),
        is_mock=True,
    )
    db.commit()
    return connection_response(connection)


@router.get("/connections", response_model=list[TikTokConnectionResponse])
def list_connections(context: CurrentAuth, db: DbSession):
    rows = db.scalars(
        select(TikTokConnection)
        .where(TikTokConnection.organization_id == context.membership.organization_id)
        .order_by(TikTokConnection.created_at.desc())
    )
    return [connection_response(item) for item in rows]


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect(
    connection_id: str,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*CONNECT_ROLES)),
):
    connection = owned_connection(db, context.membership.organization_id, connection_id)
    if connection.status == TikTokConnectionStatus.ACTIVE.value:
        try:
            get_tiktok_client().revoke(
                TokenCipher().decrypt(connection.access_token_ciphertext)
            )
        except TikTokApiError as error:
            if error.retryable:
                raise provider_error(error) from error
    connection.status = TikTokConnectionStatus.REVOKED.value
    connection.access_token_ciphertext = TokenCipher().encrypt("revoked")
    connection.refresh_token_ciphertext = TokenCipher().encrypt("revoked")
    write_audit(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        action="tiktok.disconnected",
        entity_type="tiktok_connection",
        entity_id=connection.id,
    )
    db.commit()


@router.post(
    "/connections/{connection_id}/creator-info",
    response_model=CreatorInfoResponse,
)
def refresh_creator_info(
    connection_id: str,
    context: CurrentAuth,
    db: DbSession,
):
    connection = owned_connection(db, context.membership.organization_id, connection_id)
    if connection.status != TikTokConnectionStatus.ACTIVE.value:
        raise HTTPException(status_code=409, detail={"code": "connection_inactive"})
    try:
        client = get_tiktok_client()
        info = client.creator_info(access_token_for(connection))
    except TikTokApiError as error:
        raise provider_error(error) from error
    fetched_at = utcnow()
    connection.creator_info_json = json.dumps(info, ensure_ascii=False, separators=(",", ":"))
    connection.creator_info_fetched_at = fetched_at
    connection.display_name = str(info.get("creator_nickname") or "") or connection.display_name
    connection.avatar_url = str(info.get("creator_avatar_url") or "") or None
    db.commit()
    return CreatorInfoResponse(
        connection_id=connection.id,
        creator_username=info.get("creator_username"),
        creator_nickname=info.get("creator_nickname"),
        creator_avatar_url=info.get("creator_avatar_url"),
        privacy_level_options=list(info.get("privacy_level_options") or []),
        comment_disabled=bool(info.get("comment_disabled")),
        duet_disabled=bool(info.get("duet_disabled")),
        stitch_disabled=bool(info.get("stitch_disabled")),
        max_video_post_duration_sec=int(info.get("max_video_post_duration_sec") or 0),
        is_mock=connection.is_mock,
        fetched_at=fetched_at,
    )


@router.post(
    "/schedule/{slot_id}/publication-jobs",
    response_model=PublicationJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_publication_job(
    slot_id: str,
    payload: PublicationCreateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*PUBLISH_ROLES)),
):
    settings = get_settings()
    organization_id = context.membership.organization_id
    slot = db.scalar(
        select(ScheduledSlot).where(
            ScheduledSlot.id == slot_id,
            ScheduledSlot.organization_id == organization_id,
            ScheduledSlot.status.in_(("reserved", "ready", "failed")),
        )
    )
    if slot is None:
        raise HTTPException(status_code=404)
    project = db.scalar(
        select(VideoProject).where(
            VideoProject.id == slot.video_project_id,
            VideoProject.organization_id == organization_id,
        )
    )
    connection = owned_connection(db, organization_id, payload.connection_id)
    if connection.status != TikTokConnectionStatus.ACTIVE.value:
        raise HTTPException(status_code=409, detail={"code": "connection_inactive"})
    scopes = set(json.loads(connection.scopes_json))
    needed_scope = "video.publish" if payload.publish_mode.value == "direct_post" else "video.upload"
    if needed_scope not in scopes:
        raise HTTPException(status_code=409, detail={"code": "scope_not_authorized"})
    if not connection.creator_info_json or not connection.creator_info_fetched_at:
        raise HTTPException(status_code=409, detail={"code": "creator_info_required"})
    fetched_at = connection.creator_info_fetched_at
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    if fetched_at < utcnow() - timedelta(minutes=10):
        raise HTTPException(status_code=409, detail={"code": "creator_info_stale"})
    creator = json.loads(connection.creator_info_json)
    if payload.publish_mode.value == "direct_post":
        options = set(creator.get("privacy_level_options") or [])
        if payload.privacy_level not in options:
            raise HTTPException(status_code=422, detail={"code": "privacy_level_option_mismatch"})
        if not settings.tiktok_app_audited and not connection.is_mock and payload.privacy_level != "SELF_ONLY":
            raise HTTPException(
                status_code=422,
                detail={"code": "unaudited_client_requires_self_only"},
            )
        if creator.get("comment_disabled") and payload.allow_comment:
            raise HTTPException(status_code=422, detail={"code": "comments_disabled_by_creator"})
        if creator.get("duet_disabled") and payload.allow_duet:
            raise HTTPException(status_code=422, detail={"code": "duet_disabled_by_creator"})
        if creator.get("stitch_disabled") and payload.allow_stitch:
            raise HTTPException(status_code=422, detail={"code": "stitch_disabled_by_creator"})
    if project is None:
        raise HTTPException(status_code=404)
    max_duration = int(creator.get("max_video_post_duration_sec") or 0)
    if max_duration and (project.duration_ms or 0) > max_duration * 1000:
        raise HTTPException(status_code=422, detail={"code": "duration_exceeds_creator_limit"})
    render_statuses = ("succeeded", "mock_ready") if connection.is_mock else ("succeeded",)
    render = db.scalar(
        select(RenderJob)
        .where(
            RenderJob.video_project_id == project.id,
            RenderJob.status.in_(render_statuses),
            RenderJob.output_asset_id.is_not(None),
        )
        .order_by(RenderJob.created_at.desc())
        .limit(1)
    )
    if render is None:
        raise HTTPException(status_code=409, detail={"code": "publishable_render_required"})
    asset = db.get(MediaAsset, render.output_asset_id)
    if asset is None or (not connection.is_mock and (asset.mime_type != "video/mp4" or asset.is_mock)):
        raise HTTPException(status_code=409, detail={"code": "real_mp4_required"})
    canonical = json.dumps(
        {
            "slot": slot.id,
            "connection": connection.id,
            **payload.model_dump(mode="json", exclude={"idempotency_key"}),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    payload_hash = sha256(canonical.encode()).hexdigest()
    stored_key = f"{organization_id}:{payload.idempotency_key}"
    existing = db.scalar(
        select(PublicationJob).where(PublicationJob.idempotency_key == stored_key)
    )
    if existing:
        if existing.payload_hash != payload_hash:
            raise HTTPException(status_code=409, detail={"code": "idempotency_conflict"})
        return job_response(db, existing, include_events=True)
    job = PublicationJob(
        organization_id=organization_id,
        video_project_id=project.id,
        scheduled_slot_id=slot.id,
        connection_id=connection.id,
        requested_by=context.user.id,
        output_asset_id=asset.id,
        idempotency_key=stored_key,
        payload_hash=payload_hash,
        publish_mode=payload.publish_mode.value,
        caption=payload.caption,
        privacy_level=payload.privacy_level,
        disable_comment=not bool(payload.allow_comment),
        disable_duet=not bool(payload.allow_duet),
        disable_stitch=not bool(payload.allow_stitch),
        brand_content_toggle=payload.brand_content_toggle,
        brand_organic_toggle=payload.brand_organic_toggle,
        is_aigc=payload.is_aigc,
        consented_at=utcnow(),
        scheduled_for=slot.scheduled_for,
        status=PublicationStatus.QUEUED.value,
        is_mock=connection.is_mock,
    )
    db.add(job)
    db.flush()
    add_event(
        db,
        job,
        "publication.authorized",
        {
            "explicit_consent": True,
            "music_usage_confirmed": True,
            "privacy_level": payload.privacy_level,
        },
    )
    write_audit(
        db,
        organization_id=organization_id,
        actor_id=context.user.id,
        action="publication.authorized",
        entity_type="publication_job",
        entity_id=job.id,
        metadata={"slot_id": slot.id, "mode": job.publish_mode, "mock": job.is_mock},
    )
    db.commit()
    if connection.is_mock:
        execute_publication_job(job.id)
        db.refresh(job)
    else:
        try:
            scheduled_for = slot.scheduled_for
            if scheduled_for.tzinfo is None:
                scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)
            enqueue_publication(job.id, eta=max(utcnow(), scheduled_for))
        except Exception as error:
            job.status = PublicationStatus.FAILED.value
            job.error_code = "queue_unavailable"
            job.error_message = str(error)[:1000]
            db.commit()
    return job_response(db, job, include_events=True)


@router.get("/publication-jobs", response_model=list[PublicationJobResponse])
def list_publication_jobs(context: CurrentAuth, db: DbSession, limit: int = Query(50, ge=1, le=100)):
    jobs = db.scalars(
        select(PublicationJob)
        .where(PublicationJob.organization_id == context.membership.organization_id)
        .order_by(PublicationJob.created_at.desc())
        .limit(limit)
    )
    return [job_response(db, job) for job in jobs]


@router.get("/publication-jobs/{job_id}", response_model=PublicationJobResponse)
def get_publication_job(job_id: str, context: CurrentAuth, db: DbSession):
    job = db.scalar(
        select(PublicationJob).where(
            PublicationJob.id == job_id,
            PublicationJob.organization_id == context.membership.organization_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404)
    return job_response(db, job, include_events=True)


@router.post("/publication-jobs/{job_id}/cancel", response_model=PublicationJobResponse)
def cancel_publication(
    job_id: str,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*PUBLISH_ROLES)),
):
    job = db.scalar(
        select(PublicationJob).where(
            PublicationJob.id == job_id,
            PublicationJob.organization_id == context.membership.organization_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404)
    if job.status in TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail={"code": "publication_terminal"})
    if job.publish_id and not job.is_mock:
        raise HTTPException(
            status_code=409,
            detail={"code": "provider_processing_cannot_cancel"},
        )
    job.status = PublicationStatus.CANCELLED.value
    slot = db.get(ScheduledSlot, job.scheduled_slot_id)
    if slot:
        slot.status = "reserved"
    add_event(db, job, "publication.cancelled")
    db.commit()
    return job_response(db, job, include_events=True)


@router.post("/publication-jobs/{job_id}/retry", response_model=PublicationJobResponse)
def retry_publication(
    job_id: str,
    payload: PublicationRetryRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*PUBLISH_ROLES)),
):
    job = db.scalar(
        select(PublicationJob).where(
            PublicationJob.id == job_id,
            PublicationJob.organization_id == context.membership.organization_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404)
    if job.status not in {
        PublicationStatus.FAILED.value,
        PublicationStatus.DEAD_LETTER.value,
    }:
        raise HTTPException(status_code=409, detail={"code": "publication_not_retryable"})
    job.status = PublicationStatus.QUEUED.value
    job.attempts = 0
    job.error_code = None
    job.error_message = None
    job.publish_id = None
    job.post_id = None
    job.consented_at = utcnow()
    slot = db.get(ScheduledSlot, job.scheduled_slot_id)
    if slot:
        slot.status = "scheduled"
    add_event(db, job, "publication.requeued", {"fresh_consent": True})
    db.commit()
    if job.is_mock:
        execute_publication_job(job.id)
    else:
        try:
            enqueue_publication(job.id, eta=utcnow())
        except Exception as error:
            job.status = PublicationStatus.FAILED.value
            job.error_code = "queue_unavailable"
            job.error_message = str(error)[:1000]
            db.commit()
    db.refresh(job)
    return job_response(db, job, include_events=True)


@router.post("/webhooks", status_code=status.HTTP_200_OK)
async def tiktok_webhook(request: Request, db: DbSession):
    settings = get_settings()
    raw = await request.body()
    signature_header = request.headers.get("TikTok-Signature", "")
    parts = dict(
        item.split("=", 1) for item in signature_header.split(",") if "=" in item
    )
    timestamp = parts.get("t", "")
    signature = parts.get("s", "")
    try:
        timestamp_value = int(timestamp)
    except ValueError as error:
        raise HTTPException(status_code=401, detail={"code": "invalid_webhook_signature"}) from error
    expected = hmac.new(
        settings.tiktok_client_secret.encode(),
        timestamp.encode() + b"." + raw,
        sha256,
    ).hexdigest()
    if (
        not settings.tiktok_client_secret
        or not hmac.compare_digest(expected, signature)
        or abs(int(time.time()) - timestamp_value) > settings.webhook_tolerance_seconds
    ):
        raise HTTPException(status_code=401, detail={"code": "invalid_webhook_signature"})
    delivery_hash = sha256(raw).hexdigest()
    if db.scalar(
        select(TikTokWebhookReceipt.id).where(
            TikTokWebhookReceipt.delivery_hash == delivery_hash
        )
    ):
        return {"received": True, "duplicate": True}
    payload = json.loads(raw)
    event_type = str(payload.get("event") or "unknown")
    raw_content = payload.get("content") or {}
    content = json.loads(raw_content) if isinstance(raw_content, str) else raw_content
    receipt = TikTokWebhookReceipt(
        delivery_hash=delivery_hash,
        event_type=event_type,
        open_id=payload.get("user_openid"),
        payload_json=raw.decode("utf-8"),
    )
    db.add(receipt)
    if event_type == "authorization.removed":
        connection = db.scalar(
            select(TikTokConnection).where(
                TikTokConnection.open_id == payload.get("user_openid")
            )
        )
        if connection:
            connection.status = TikTokConnectionStatus.REVOKED.value
    publish_id = content.get("publish_id")
    job = (
        db.scalar(select(PublicationJob).where(PublicationJob.publish_id == publish_id))
        if publish_id
        else None
    )
    if job:
        add_event(db, job, f"webhook.{event_type}", content)
        slot = db.get(ScheduledSlot, job.scheduled_slot_id)
        project = db.get(VideoProject, job.video_project_id)
        if event_type in {"post.publish.complete", "post.publish.publicly_available"}:
            job.status = PublicationStatus.PUBLISHED.value
            job.post_id = str(content.get("post_id") or "") or job.post_id
            if slot:
                slot.status = "published"
            if project:
                project.status = "published"
                notify(db, job, "Publicação confirmada", f"“{project.title}” foi publicado pelo TikTok.")
        elif event_type == "post.publish.inbox_delivered":
            job.status = PublicationStatus.INBOX_DELIVERED.value
            if slot:
                slot.status = "ready"
            if project:
                notify(db, job, "Rascunho entregue no TikTok", f"Finalize “{project.title}” no aplicativo TikTok.")
        elif event_type == "post.publish.failed":
            job.status = PublicationStatus.FAILED.value
            job.error_code = str(content.get("reason") or "provider_failed")
            if slot:
                slot.status = "failed"
            notify(db, job, "Falha na publicação", "O TikTok informou uma falha no processamento.")
    receipt.processed = True
    db.commit()
    return {"received": True}
