import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select

from ..audit import write_audit
from ..captions import GeneratedCue, export_srt, export_vtt, generate_cues
from ..config import get_settings
from ..dependencies import AuthContext, CurrentAuth, DbSession, require_roles
from ..models import (
    AssetKind,
    CaptionCue,
    CaptionTrack,
    MediaAsset,
    MediaLicense,
    RenderJob,
    Role,
    Script,
    VideoProject,
    VideoScene,
    VoiceProfile,
)
from ..providers.registry import text_to_speech
from ..render_worker import execute_render_job
from ..storage import LocalObjectStorage
from ..video_schemas import (
    CaptionCueResponse,
    CaptionGenerateRequest,
    CaptionTrackResponse,
    LicenseType,
    MediaAssetResponse,
    NarrationCreateRequest,
    RenderJobResponse,
    RenderRequest,
    SceneCreateRequest,
    SceneUpdateRequest,
    SceneResponse,
    VideoProjectCreateRequest,
    VideoProjectResponse,
    VoiceProfileCreateRequest,
    VoiceProfileResponse,
)

router = APIRouter(prefix="/v1/video", tags=["Video"])
PRODUCTION_ROLES = (Role.ADMIN.value, Role.MANAGER.value, Role.EDITOR.value)
LICENSE_TYPES = {item.value for item in LicenseType}


def owned_script(db: DbSession, organization_id: str, script_id: str) -> Script:
    script = db.scalar(
        select(Script).where(
            Script.id == script_id,
            Script.organization_id == organization_id,
        )
    )
    if script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return script


def owned_asset(db: DbSession, organization_id: str, asset_id: str) -> MediaAsset:
    asset = db.scalar(
        select(MediaAsset).where(
            MediaAsset.id == asset_id,
            MediaAsset.organization_id == organization_id,
        )
    )
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return asset


def asset_response(db: DbSession, asset: MediaAsset) -> MediaAssetResponse:
    license_status = db.scalar(
        select(MediaLicense.status).where(MediaLicense.asset_id == asset.id)
    )
    return MediaAssetResponse(
        id=asset.id,
        kind=asset.kind,
        origin=asset.origin,
        original_filename=asset.original_filename,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        sha256=asset.sha256,
        duration_ms=asset.duration_ms,
        width=asset.width,
        height=asset.height,
        status=asset.status,
        provider_key=asset.provider_key,
        is_mock=asset.is_mock,
        license_status=license_status,
        created_at=asset.created_at,
    )


def caption_response(db: DbSession, track: CaptionTrack) -> CaptionTrackResponse:
    cues = list(
        db.scalars(
            select(CaptionCue)
            .where(CaptionCue.track_id == track.id)
            .order_by(CaptionCue.sequence)
        )
    )
    return CaptionTrackResponse(
        id=track.id,
        script_id=track.script_id,
        language=track.language,
        style=track.style,
        status=track.status,
        safe_area=json.loads(track.safe_area_json),
        cues=[
            CaptionCueResponse(
                sequence=cue.sequence,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                text=cue.text,
                highlights=json.loads(cue.highlight_words_json),
            )
            for cue in cues
        ],
        created_at=track.created_at,
    )


def project_response(db: DbSession, project: VideoProject) -> VideoProjectResponse:
    scenes = list(
        db.scalars(
            select(VideoScene)
            .where(VideoScene.video_project_id == project.id)
            .order_by(VideoScene.sequence)
        )
    )
    return VideoProjectResponse(
        id=project.id,
        script_id=project.script_id,
        title=project.title,
        status=project.status,
        width=project.width,
        height=project.height,
        fps=project.fps,
        duration_ms=project.duration_ms,
        template_key=project.template_key,
        narration_asset_id=project.narration_asset_id,
        caption_track_id=project.caption_track_id,
        preview_is_mock=project.status == "preview_mock",
        scenes=[
            SceneResponse(
                id=scene.id,
                sequence=scene.sequence,
                media_asset_id=scene.media_asset_id,
                start_ms=scene.start_ms,
                end_ms=scene.end_ms,
                trim_start_ms=scene.trim_start_ms,
                transition=scene.transition,
                motion=scene.motion,
                text_overlay=json.loads(scene.text_overlay_json),
            )
            for scene in scenes
        ],
        created_at=project.created_at,
    )


@router.get("/voices", response_model=list[VoiceProfileResponse])
def list_voices(context: CurrentAuth, db: DbSession):
    return list(
        db.scalars(
            select(VoiceProfile)
            .where(
                VoiceProfile.organization_id == context.membership.organization_id,
                VoiceProfile.active.is_(True),
            )
            .order_by(VoiceProfile.name)
        )
    )


@router.post("/voices", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
def create_voice(
    payload: VoiceProfileCreateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*PRODUCTION_ROLES)),
):
    provider = text_to_speech()
    voice = VoiceProfile(
        organization_id=context.membership.organization_id,
        created_by=context.user.id,
        provider_key=provider.provider_key,
        is_mock=provider.is_mock,
        **payload.model_dump(),
    )
    db.add(voice)
    db.commit()
    return voice


@router.post(
    "/scripts/{script_id}/narration",
    response_model=MediaAssetResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_narration(
    script_id: str,
    payload: NarrationCreateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*PRODUCTION_ROLES)),
):
    script = owned_script(db, context.membership.organization_id, script_id)
    voice = db.scalar(
        select(VoiceProfile).where(
            VoiceProfile.id == payload.voice_profile_id,
            VoiceProfile.organization_id == context.membership.organization_id,
            VoiceProfile.active.is_(True),
        )
    )
    if voice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    provider = text_to_speech()
    audio = provider.synthesize(
        script.content,
        voice_id=voice.provider_voice_id,
        language=voice.language,
        speaking_rate=voice.speaking_rate,
    )
    storage = LocalObjectStorage()
    stored = storage.save_bytes(
        audio.content,
        organization_id=context.membership.organization_id,
        kind=AssetKind.AUDIO.value,
        mime_type=audio.mime_type,
    )
    existing = db.scalar(
        select(MediaAsset).where(
            MediaAsset.organization_id == context.membership.organization_id,
            MediaAsset.sha256 == stored.sha256,
        )
    )
    if existing is not None:
        storage.delete(stored.key)
        return asset_response(db, existing)
    asset = MediaAsset(
        organization_id=context.membership.organization_id,
        created_by=context.user.id,
        kind=AssetKind.AUDIO.value,
        origin="generated",
        original_filename=f"narration-{script.id}{audio.file_extension}",
        storage_key=stored.key,
        mime_type=stored.mime_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        duration_ms=audio.duration_ms,
        status="ready",
        provider_key=provider.provider_key,
        is_mock=provider.is_mock,
    )
    db.add(asset)
    db.commit()
    return asset_response(db, asset)


@router.post("/assets", response_model=MediaAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    file: Annotated[UploadFile, File()],
    kind: Annotated[str, Form()],
    license_type: Annotated[str, Form()],
    db: DbSession,
    context: AuthContext = Depends(require_roles(*PRODUCTION_ROLES)),
    source_url: Annotated[str | None, Form()] = None,
    attribution: Annotated[str | None, Form()] = None,
):
    if kind not in (AssetKind.IMAGE.value, AssetKind.VIDEO.value, AssetKind.AUDIO.value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_asset_kind", "message": "Tipo de ativo inválido."},
        )
    if license_type not in LICENSE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_license", "message": "Licença inválida."},
        )
    if license_type in ("licensed_stock", "public_domain", "explicit_permission") and not source_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "license_source_required", "message": "Informe a origem da licença."},
        )
    storage = LocalObjectStorage()
    try:
        stored = await storage.save_upload(
            file,
            organization_id=context.membership.organization_id,
            kind=kind,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "upload_rejected", "message": str(error)},
        ) from error
    existing = db.scalar(
        select(MediaAsset).where(
            MediaAsset.organization_id == context.membership.organization_id,
            MediaAsset.sha256 == stored.sha256,
        )
    )
    if existing is not None:
        storage.delete(stored.key)
        return asset_response(db, existing)
    asset = MediaAsset(
        organization_id=context.membership.organization_id,
        created_by=context.user.id,
        kind=kind,
        origin="user_upload",
        original_filename=(file.filename or "upload")[:255],
        storage_key=stored.key,
        mime_type=stored.mime_type,
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        status="ready",
    )
    db.add(asset)
    db.flush()
    db.add(
        MediaLicense(
            organization_id=context.membership.organization_id,
            asset_id=asset.id,
            license_type=license_type,
            source_url=source_url,
            attribution=attribution,
            status="valid",
            reviewed_by=context.user.id,
        )
    )
    db.commit()
    return asset_response(db, asset)


@router.get("/assets", response_model=list[MediaAssetResponse])
def list_assets(context: CurrentAuth, db: DbSession, kind: str | None = None, limit: int = 50):
    query = select(MediaAsset).where(
        MediaAsset.organization_id == context.membership.organization_id
    )
    if kind:
        query = query.where(MediaAsset.kind == kind)
    assets = list(
        db.scalars(query.order_by(MediaAsset.created_at.desc()).limit(min(max(limit, 1), 100)))
    )
    return [asset_response(db, asset) for asset in assets]


@router.post(
    "/scripts/{script_id}/captions",
    response_model=CaptionTrackResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_caption_track(
    script_id: str,
    payload: CaptionGenerateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*PRODUCTION_ROLES)),
):
    script = owned_script(db, context.membership.organization_id, script_id)
    duration_ms = payload.duration_ms or min(
        180_000, max(5_000, round(len(script.content.split()) / 2.4 * 1000))
    )
    generated = generate_cues(script.content, duration_ms, payload.words_per_cue)
    track = CaptionTrack(
        organization_id=context.membership.organization_id,
        script_id=script.id,
        created_by=context.user.id,
        language=payload.language,
        style=payload.style.value,
        status="ready",
    )
    db.add(track)
    db.flush()
    db.add_all(
        [
            CaptionCue(
                track_id=track.id,
                sequence=cue.sequence,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                text=cue.text,
                highlight_words_json=json.dumps(cue.highlights, ensure_ascii=False),
            )
            for cue in generated
        ]
    )
    db.commit()
    return caption_response(db, track)


@router.get("/captions/{track_id}", response_model=CaptionTrackResponse)
def get_caption_track(track_id: str, context: CurrentAuth, db: DbSession):
    track = db.scalar(
        select(CaptionTrack).where(
            CaptionTrack.id == track_id,
            CaptionTrack.organization_id == context.membership.organization_id,
        )
    )
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return caption_response(db, track)


@router.get("/captions/{track_id}/export/{format}")
def export_caption_track(track_id: str, format: str, context: CurrentAuth, db: DbSession):
    track = db.scalar(
        select(CaptionTrack).where(
            CaptionTrack.id == track_id,
            CaptionTrack.organization_id == context.membership.organization_id,
        )
    )
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    rows = list(
        db.scalars(
            select(CaptionCue)
            .where(CaptionCue.track_id == track.id)
            .order_by(CaptionCue.sequence)
        )
    )
    cues = [
        GeneratedCue(
            row.sequence,
            row.start_ms,
            row.end_ms,
            row.text,
            json.loads(row.highlight_words_json),
        )
        for row in rows
    ]
    if format == "srt":
        return PlainTextResponse(export_srt(cues), media_type="application/x-subrip")
    if format == "vtt":
        return PlainTextResponse(export_vtt(cues), media_type="text/vtt")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/projects", response_model=VideoProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: VideoProjectCreateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*PRODUCTION_ROLES)),
):
    script = owned_script(db, context.membership.organization_id, payload.script_id)
    if payload.narration_asset_id:
        narration = owned_asset(db, context.membership.organization_id, payload.narration_asset_id)
        if narration.kind != AssetKind.AUDIO.value:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    if payload.caption_track_id:
        caption = db.scalar(
            select(CaptionTrack).where(
                CaptionTrack.id == payload.caption_track_id,
                CaptionTrack.organization_id == context.membership.organization_id,
                CaptionTrack.script_id == script.id,
            )
        )
        if caption is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    project = VideoProject(
        organization_id=context.membership.organization_id,
        script_id=script.id,
        created_by=context.user.id,
        **payload.model_dump(exclude={"script_id"}),
    )
    db.add(project)
    db.commit()
    return project_response(db, project)


@router.get("/projects/{project_id}", response_model=VideoProjectResponse)
def get_project(project_id: str, context: CurrentAuth, db: DbSession):
    project = db.scalar(
        select(VideoProject).where(
            VideoProject.id == project_id,
            VideoProject.organization_id == context.membership.organization_id,
        )
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return project_response(db, project)


@router.post(
    "/projects/{project_id}/scenes",
    response_model=SceneResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_scene(
    project_id: str,
    payload: SceneCreateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*PRODUCTION_ROLES)),
):
    project = db.scalar(
        select(VideoProject).where(
            VideoProject.id == project_id,
            VideoProject.organization_id == context.membership.organization_id,
        )
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if payload.end_ms <= payload.start_ms:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_scene_range", "message": "O fim deve ser posterior ao início."},
        )
    asset = owned_asset(db, context.membership.organization_id, payload.media_asset_id)
    if asset.kind not in (AssetKind.IMAGE.value, AssetKind.VIDEO.value):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    license_record = db.scalar(
        select(MediaLicense).where(
            MediaLicense.asset_id == asset.id,
            MediaLicense.status == "valid",
        )
    )
    now = datetime.now(timezone.utc)
    if license_record is None or (
        license_record.valid_until is not None
        and license_record.valid_until.replace(tzinfo=license_record.valid_until.tzinfo or timezone.utc) < now
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "license_invalid", "message": "O ativo não possui licença válida."},
        )
    sequence = (
        db.scalar(
            select(func.max(VideoScene.sequence)).where(
                VideoScene.video_project_id == project.id
            )
        )
        or 0
    ) + 1
    scene = VideoScene(
        video_project_id=project.id,
        sequence=sequence,
        media_asset_id=asset.id,
        start_ms=payload.start_ms,
        end_ms=payload.end_ms,
        trim_start_ms=payload.trim_start_ms,
        transition=payload.transition,
        motion=payload.motion,
        text_overlay_json=json.dumps(payload.text_overlay, ensure_ascii=False),
    )
    db.add(scene)
    project.duration_ms = max(project.duration_ms or 0, payload.end_ms)
    project.status = "assembling"
    db.commit()
    return SceneResponse(
        id=scene.id,
        sequence=scene.sequence,
        media_asset_id=scene.media_asset_id,
        start_ms=scene.start_ms,
        end_ms=scene.end_ms,
        trim_start_ms=scene.trim_start_ms,
        transition=scene.transition,
        motion=scene.motion,
        text_overlay=payload.text_overlay,
    )


@router.patch(
    "/projects/{project_id}/scenes/{scene_id}",
    response_model=SceneResponse,
)
def update_scene(
    project_id: str,
    scene_id: str,
    payload: SceneUpdateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*PRODUCTION_ROLES)),
):
    project = db.scalar(
        select(VideoProject).where(
            VideoProject.id == project_id,
            VideoProject.organization_id == context.membership.organization_id,
        )
    )
    scene = db.scalar(
        select(VideoScene).where(
            VideoScene.id == scene_id,
            VideoScene.video_project_id == project_id,
        )
    )
    if project is None or scene is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    changes = payload.model_dump(exclude_unset=True)
    start_ms = changes.get("start_ms", scene.start_ms)
    end_ms = changes.get("end_ms", scene.end_ms)
    if end_ms <= start_ms:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_scene_range"},
        )
    overlay = changes.pop("text_overlay", None)
    for key, value in changes.items():
        setattr(scene, key, value)
    if overlay is not None:
        scene.text_overlay_json = json.dumps(overlay, ensure_ascii=False)
    project.status = "assembling"
    db.flush()
    project.duration_ms = db.scalar(
        select(func.max(VideoScene.end_ms)).where(
            VideoScene.video_project_id == project.id
        )
    )
    write_audit(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        action="video.scene_updated",
        entity_type="video_scene",
        entity_id=scene.id,
        metadata={"project_id": project.id, "fields": sorted(payload.model_fields_set)},
    )
    db.commit()
    return SceneResponse(
        id=scene.id,
        sequence=scene.sequence,
        media_asset_id=scene.media_asset_id,
        start_ms=scene.start_ms,
        end_ms=scene.end_ms,
        trim_start_ms=scene.trim_start_ms,
        transition=scene.transition,
        motion=scene.motion,
        text_overlay=json.loads(scene.text_overlay_json),
    )


@router.post("/projects/{project_id}/render", response_model=RenderJobResponse)
def request_render(
    project_id: str,
    payload: RenderRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*PRODUCTION_ROLES)),
):
    project = db.scalar(
        select(VideoProject).where(
            VideoProject.id == project_id,
            VideoProject.organization_id == context.membership.organization_id,
        )
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    scenes = list(
        db.scalars(
            select(VideoScene)
            .where(VideoScene.video_project_id == project.id)
            .order_by(VideoScene.sequence)
        )
    )
    if not scenes or not project.narration_asset_id or not project.caption_track_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "project_incomplete",
                "message": "Adicione cena, narração e legenda antes de renderizar.",
            },
        )
    render_payload = json.dumps(
        {
            "project": project.id,
            "script": project.script_id,
            "narration": project.narration_asset_id,
            "captions": project.caption_track_id,
            "template": project.template_key,
            "scenes": [
                [scene.media_asset_id, scene.start_ms, scene.end_ms, scene.transition, scene.motion]
                for scene in scenes
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    payload_hash = sha256(render_payload.encode("utf-8")).hexdigest()
    existing = db.scalar(
        select(RenderJob).where(RenderJob.idempotency_key == payload.idempotency_key)
    )
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "idempotency_conflict", "message": "A chave já foi usada com outro projeto."},
            )
        return existing
    job = RenderJob(
        organization_id=context.membership.organization_id,
        video_project_id=project.id,
        requested_by=context.user.id,
        idempotency_key=payload.idempotency_key,
        payload_hash=payload_hash,
        status="queued",
    )
    db.add(job)
    project.status = "queued"
    db.commit()
    if get_settings().render_mode == "mock":
        execute_render_job(job.id)
        db.refresh(job)
    else:
        from ..queueing import enqueue_render

        try:
            enqueue_render(job.id)
        except Exception as error:
            job.status = "dispatch_failed"
            job.error_code = "queue_unavailable"
            job.error_message = str(error)[:500]
            db.commit()
    return job


@router.get("/render-jobs/{job_id}", response_model=RenderJobResponse)
def get_render_job(job_id: str, context: CurrentAuth, db: DbSession):
    job = db.scalar(
        select(RenderJob).where(
            RenderJob.id == job_id,
            RenderJob.organization_id == context.membership.organization_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return job
