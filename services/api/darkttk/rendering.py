from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import get_settings


@dataclass(frozen=True)
class RenderSceneInput:
    path: Path
    kind: str
    duration_ms: int


def ffmpeg_escape(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def build_ffmpeg_command(
    *,
    scenes: list[RenderSceneInput],
    narration_path: Path,
    captions_path: Path,
    output_path: Path,
    width: int,
    height: int,
    fps: int,
) -> list[str]:
    if not scenes:
        raise ValueError("At least one licensed scene is required")
    settings = get_settings()
    command = [settings.ffmpeg_path, "-y"]
    filters: list[str] = []
    labels: list[str] = []
    for index, scene in enumerate(scenes):
        duration = max(0.25, scene.duration_ms / 1000)
        if scene.kind == "image":
            command.extend(["-loop", "1", "-t", f"{duration:.3f}", "-i", str(scene.path)])
        elif scene.kind == "video":
            command.extend(["-stream_loop", "-1", "-t", f"{duration:.3f}", "-i", str(scene.path)])
        else:
            raise ValueError("Only image and video scenes are renderable")
        label = f"v{index}"
        filters.append(
            f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},setsar=1,trim=duration={duration:.3f},"
            f"setpts=PTS-STARTPTS[{label}]"
        )
        labels.append(f"[{label}]")
    audio_index = len(scenes)
    command.extend(["-i", str(narration_path)])
    concat = "".join(labels) + f"concat=n={len(scenes)}:v=1:a=0[base]"
    subtitle = (
        f"[base]subtitles=filename='{ffmpeg_escape(captions_path)}':"
        "force_style='FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Alignment=2,MarginV=260'[outv]"
    )
    command.extend(
        [
            "-filter_complex",
            ";".join(filters + [concat, subtitle]),
            "-map",
            "[outv]",
            "-map",
            f"{audio_index}:a",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-af",
            "loudnorm=I=-14:TP=-1:LRA=11",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_path),
        ]
    )
    return command


def run_ffmpeg(command: list[str]) -> None:
    settings = get_settings()
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=settings.render_timeout_seconds,
        check=False,
        shell=False,
    )
    if result.returncode != 0:
        tail = (result.stderr or "")[-2000:]
        raise RuntimeError(f"FFmpeg failed with code {result.returncode}: {tail}")


def preview_manifest(
    *,
    project_id: str,
    width: int,
    height: int,
    fps: int,
    scenes: list[dict[str, object]],
    captions: list[dict[str, object]],
    narration_asset_id: str | None,
) -> str:
    return json.dumps(
        {
            "kind": "darkttk-preview-manifest",
            "mock": True,
            "project_id": project_id,
            "canvas": {"width": width, "height": height, "fps": fps, "aspect_ratio": "9:16"},
            "narration_asset_id": narration_asset_id,
            "scenes": scenes,
            "captions": captions,
            "notice": "Manifesto de prévia local; não é um vídeo final renderizado.",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
