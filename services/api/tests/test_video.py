from uuid import uuid4

from fastapi.testclient import TestClient

from darkttk.main import app


def prepared_script(client: TestClient) -> tuple[dict[str, str], dict[str, object]]:
    suffix = uuid4().hex[:8]
    registered = client.post(
        "/v1/auth/register",
        json={
            "email": f"video-{suffix}@example.com",
            "display_name": "Editora de Vídeo",
            "password": "Senha#Segura2026",
            "organization_name": f"Vídeo {suffix}",
        },
    )
    assert registered.status_code == 201, registered.text
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    niches = client.get("/v1/content/niches", headers=headers)
    niche_id = next(item["id"] for item in niches.json() if item["slug"] == "engenharia")
    idea = client.post(
        "/v1/content/ideas/generate",
        headers=headers,
        json={
            "niche_id": niche_id,
            "topic": "Como estruturas distribuem cargas com segurança",
            "objective": "educar com clareza",
        },
    )
    assert idea.status_code == 201, idea.text
    script = client.post(
        f"/v1/content/ideas/{idea.json()['id']}/scripts/generate",
        headers=headers,
        json={"style": "documentary", "duration_seconds": 30},
    )
    assert script.status_code == 201, script.text
    return headers, script.json()


def test_video_pipeline_creates_mock_preview_with_licensed_asset():
    with TestClient(app) as client:
        headers, script = prepared_script(client)

        voice = client.post(
            "/v1/video/voices",
            headers=headers,
            json={"name": "Narrador neutro"},
        )
        assert voice.status_code == 201, voice.text
        assert voice.json()["is_mock"] is True

        narration = client.post(
            f"/v1/video/scripts/{script['id']}/narration",
            headers=headers,
            json={"voice_profile_id": voice.json()["id"]},
        )
        assert narration.status_code == 201, narration.text
        assert narration.json()["mime_type"] == "audio/wav"
        assert narration.json()["is_mock"] is True

        captions = client.post(
            f"/v1/video/scripts/{script['id']}/captions",
            headers=headers,
            json={"style": "dynamic", "duration_ms": 30_000, "words_per_cue": 5},
        )
        assert captions.status_code == 201, captions.text
        assert captions.json()["cues"]
        exported = client.get(
            f"/v1/video/captions/{captions.json()['id']}/export/srt",
            headers=headers,
        )
        assert exported.status_code == 200
        assert "-->" in exported.text

        image = client.post(
            "/v1/video/assets",
            headers=headers,
            data={"kind": "image", "license_type": "user_owned"},
            files={"file": ("scene.png", b"\x89PNG\r\n\x1a\nDarkTTK", "image/png")},
        )
        assert image.status_code == 201, image.text
        assert image.json()["license_status"] == "valid"

        project = client.post(
            "/v1/video/projects",
            headers=headers,
            json={
                "script_id": script["id"],
                "title": "Estruturas em 30 segundos",
                "voice_profile_id": voice.json()["id"],
                "narration_asset_id": narration.json()["id"],
                "caption_track_id": captions.json()["id"],
            },
        )
        assert project.status_code == 201, project.text
        scene = client.post(
            f"/v1/video/projects/{project.json()['id']}/scenes",
            headers=headers,
            json={
                "media_asset_id": image.json()["id"],
                "start_ms": 0,
                "end_ms": 30_000,
                "motion": "zoom_in",
            },
        )
        assert scene.status_code == 201, scene.text
        updated = client.patch(
            f"/v1/video/projects/{project.json()['id']}/scenes/{scene.json()['id']}",
            headers=headers,
            json={
                "end_ms": 28_000,
                "transition": "fade",
                "motion": "pan_left",
                "text_overlay": {"text": "CARGAS DISTRIBUÍDAS", "safe_area": True},
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["end_ms"] == 28_000
        assert updated.json()["transition"] == "fade"

        rendered = client.post(
            f"/v1/video/projects/{project.json()['id']}/render",
            headers=headers,
            json={"idempotency_key": f"video-preview-{uuid4().hex}"},
        )
        assert rendered.status_code == 200, rendered.text
        assert rendered.json()["status"] == "mock_ready"
        assert rendered.json()["progress"] == 100

        fetched = client.get(
            f"/v1/video/projects/{project.json()['id']}",
            headers=headers,
        )
        assert fetched.status_code == 200
        assert fetched.json()["status"] == "preview_mock"
        assert fetched.json()["preview_is_mock"] is True


def test_upload_rejects_mismatched_magic_bytes():
    with TestClient(app) as client:
        headers, _ = prepared_script(client)
        response = client.post(
            "/v1/video/assets",
            headers=headers,
            data={"kind": "image", "license_type": "user_owned"},
            files={"file": ("fake.png", b"not-a-png", "image/png")},
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "upload_rejected"
