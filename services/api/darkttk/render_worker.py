from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from tempfile import TemporaryDirectory

from sqlalchemy import select

from .captions import GeneratedCue, export_srt
from .config import get_settings
from .database import SessionLocal
from .models import (
    CaptionCue,
    MediaAsset,
    MediaLicense,
    RenderJob,
    VideoProject,
    VideoScene,
)
from .rendering import RenderSceneInput, build_ffmpeg_command, preview_manifest, run_ffmpeg
from .storage import LocalObjectStorage


def execute_render_job(job_id: str) -> None:
    settings = get_settings()
    storage = LocalObjectStorage()
    with SessionLocal() as db:
        job = db.get(RenderJob, job_id)
        if job is None or job.status not in ("queued", "retrying"):
            return
        project = db.get(VideoProject, job.video_project_id)
        if project is None:
            job.status = "failed"
            job.error_code = "project_missing"
            db.commit()
            return
        job.status = "running"
        job.attempts += 1
        job.progress = 5
        db.commit()
        try:
            scenes = list(
                db.scalars(
                    select(VideoScene)
                    .where(VideoScene.video_project_id == project.id)
                    .order_by(VideoScene.sequence)
                )
            )
            cues = list(
                db.scalars(
                    select(CaptionCue)
                    .where(CaptionCue.track_id == project.caption_track_id)
                    .order_by(CaptionCue.sequence)
                )
            )
            if not scenes:
                raise ValueError("project_has_no_scenes")
            if not project.narration_asset_id or not project.caption_track_id:
                raise ValueError("project_missing_narration_or_captions")
            validated_assets: list[tuple[VideoScene, MediaAsset]] = []
            now = datetime.now(timezone.utc)
            for scene in scenes:
                asset = db.get(MediaAsset, scene.media_asset_id)
                license_record = db.scalar(
                    select(MediaLicense).where(
                        MediaLicense.asset_id == scene.media_asset_id,
                        MediaLicense.status == "valid",
                    )
                )
                valid_until = license_record.valid_until if license_record else None
                if valid_until is not None and valid_until.tzinfo is None:
                    valid_until = valid_until.replace(tzinfo=timezone.utc)
                if asset is None or license_record is None or (
                    valid_until is not None and valid_until < now
                ):
                    raise ValueError("scene_asset_or_license_invalid")
                validated_assets.append((scene, asset))

            if settings.render_mode == "mock":
                manifest = preview_manifest(
                    project_id=project.id,
                    width=project.width,
                    height=project.height,
                    fps=project.fps,
                    narration_asset_id=project.narration_asset_id,
                    scenes=[
                        {
                            "sequence": scene.sequence,
                            "asset_id": scene.media_asset_id,
                            "start_ms": scene.start_ms,
                            "end_ms": scene.end_ms,
                            "transition": scene.transition,
                            "motion": scene.motion,
                        }
                        for scene in scenes
                    ],
                    captions=[
                        {
                            "sequence": cue.sequence,
                            "start_ms": cue.start_ms,
                            "end_ms": cue.end_ms,
                            "text": cue.text,
                        }
                        for cue in cues
                    ],
                )
                stored = storage.save_bytes(
                    manifest.encode("utf-8"),
                    organization_id=job.organization_id,
                    kind="render",
                    mime_type="application/json",
                )
                asset = MediaAsset(
                    organization_id=job.organization_id,
                    created_by=job.requested_by,
                    kind="render",
                    origin="generated",
                    original_filename=f"preview-{project.id}.json",
                    storage_key=stored.key,
                    mime_type=stored.mime_type,
                    size_bytes=stored.size_bytes,
                    sha256=stored.sha256,
                    status="ready",
                    provider_key="mock-render-v1",
                    is_mock=True,
                )
                db.add(asset)
                db.flush()
                job.output_asset_id = asset.id
                job.status = "mock_ready"
                job.progress = 100
                project.status = "preview_mock"
                project.preview_manifest_json = manifest
                db.commit()
                return

            narration = db.get(MediaAsset, project.narration_asset_id)
            if narration is None:
                raise ValueError("narration_asset_missing")
            render_inputs: list[RenderSceneInput] = []
            for scene, asset in validated_assets:
                render_inputs.append(
                    RenderSceneInput(
                        path=storage.resolve(asset.storage_key),
                        kind=asset.kind,
                        duration_ms=scene.end_ms - scene.start_ms,
                    )
                )
            generated_cues = [
                GeneratedCue(
                    cue.sequence,
                    cue.start_ms,
                    cue.end_ms,
                    cue.text,
                    json.loads(cue.highlight_words_json),
                )
                for cue in cues
            ]
            with TemporaryDirectory() as temp_dir:
                from pathlib import Path

                captions_path = Path(temp_dir) / "captions.srt"
                output_path = Path(temp_dir) / "render.mp4"
                captions_path.write_text(export_srt(generated_cues), encoding="utf-8")
                command = build_ffmpeg_command(
                    scenes=render_inputs,
                    narration_path=storage.resolve(narration.storage_key),
                    captions_path=captions_path,
                    output_path=output_path,
                    width=project.width,
                    height=project.height,
                    fps=project.fps,
                )
                run_ffmpeg(command)
                content = output_path.read_bytes()
            stored = storage.save_bytes(
                content,
                organization_id=job.organization_id,
                kind="render",
                mime_type="video/mp4",
            )
            asset = MediaAsset(
                organization_id=job.organization_id,
                created_by=job.requested_by,
                kind="render",
                origin="generated",
                original_filename=f"render-{project.id}.mp4",
                storage_key=stored.key,
                mime_type=stored.mime_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                status="ready",
                provider_key="ffmpeg",
                is_mock=False,
            )
            db.add(asset)
            db.flush()
            job.output_asset_id = asset.id
            job.status = "succeeded"
            job.progress = 100
            project.status = "review"
            db.commit()
        except Exception as error:
            job.status = "failed"
            job.error_code = type(error).__name__
            job.error_message = str(error)[:1000]
            job.progress = 0
            db.commit()
