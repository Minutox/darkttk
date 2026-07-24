from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from darkttk.main import app


def ready_video_project(client: TestClient) -> tuple[dict[str, str], dict[str, object]]:
    suffix = uuid4().hex[:8]
    registered = client.post(
        "/v1/auth/register",
        json={
            "email": f"workflow-{suffix}@example.com",
            "display_name": "Responsável Editorial",
            "password": "Senha#Segura2026",
            "organization_name": f"Operação {suffix}",
        },
    )
    assert registered.status_code == 201, registered.text
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    niches = client.get("/v1/content/niches", headers=headers).json()
    niche_id = next(item["id"] for item in niches if item["slug"] == "engenharia")
    idea = client.post(
        "/v1/content/ideas/generate",
        headers=headers,
        json={
            "niche_id": niche_id,
            "topic": "Como pontes distribuem cargas",
            "objective": "educar",
        },
    ).json()
    script_response = client.post(
        f"/v1/content/ideas/{idea['id']}/scripts/generate",
        headers=headers,
        json={"style": "documentary", "duration_seconds": 30},
    )
    assert script_response.status_code == 201, script_response.text
    script = script_response.json()
    voice = client.post(
        "/v1/video/voices", headers=headers, json={"name": "Voz editorial"}
    ).json()
    narration = client.post(
        f"/v1/video/scripts/{script['id']}/narration",
        headers=headers,
        json={"voice_profile_id": voice["id"]},
    ).json()
    captions = client.post(
        f"/v1/video/scripts/{script['id']}/captions",
        headers=headers,
        json={"duration_ms": 30_000},
    ).json()
    image_response = client.post(
        "/v1/video/assets",
        headers=headers,
        data={"kind": "image", "license_type": "user_owned"},
        files={"file": ("workflow.png", b"\x89PNG\r\n\x1a\nworkflow", "image/png")},
    )
    assert image_response.status_code == 201, image_response.text
    image = image_response.json()
    project = client.post(
        "/v1/video/projects",
        headers=headers,
        json={
            "script_id": script["id"],
            "title": "Pontes e distribuição de cargas",
            "voice_profile_id": voice["id"],
            "narration_asset_id": narration["id"],
            "caption_track_id": captions["id"],
        },
    ).json()
    scene = client.post(
        f"/v1/video/projects/{project['id']}/scenes",
        headers=headers,
        json={
            "media_asset_id": image["id"],
            "start_ms": 0,
            "end_ms": 30_000,
        },
    )
    assert scene.status_code == 201, scene.text
    rendered = client.post(
        f"/v1/video/projects/{project['id']}/render",
        headers=headers,
        json={"idempotency_key": f"workflow-render-{uuid4().hex}"},
    )
    assert rendered.status_code == 200, rendered.text
    assert rendered.json()["status"] == "mock_ready"
    return headers, project


def test_approval_revision_schedule_and_notifications():
    with TestClient(app) as client:
        headers, project = ready_video_project(client)
        submitted = client.post(
            f"/v1/workflow/projects/{project['id']}/approval-requests",
            headers=headers,
            json={"note": "Prévia pronta para revisão humana."},
        )
        assert submitted.status_code == 201, submitted.text
        assert submitted.json()["status"] == "pending"
        assert submitted.json()["preview_is_mock"] is True
        approval_id = submitted.json()["id"]

        duplicate = client.post(
            f"/v1/workflow/projects/{project['id']}/approval-requests",
            headers=headers,
            json={},
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"]["code"] == "approval_already_pending"

        missing_reason = client.post(
            f"/v1/workflow/approvals/{approval_id}/decision",
            headers=headers,
            json={"decision": "changes_requested"},
        )
        assert missing_reason.status_code == 422

        changes = client.post(
            f"/v1/workflow/approvals/{approval_id}/decision",
            headers=headers,
            json={
                "decision": "changes_requested",
                "note": "Deixar o título mais específico.",
            },
        )
        assert changes.status_code == 200, changes.text
        assert changes.json()["status"] == "changes_requested"

        edited = client.patch(
            f"/v1/workflow/projects/{project['id']}",
            headers=headers,
            json={"title": "Como pontes distribuem cargas com segurança"},
        )
        assert edited.status_code == 200, edited.text
        assert any(event["event_type"] == "project_edited" for event in edited.json()["events"])

        resubmitted = client.post(
            f"/v1/workflow/projects/{project['id']}/approval-requests",
            headers=headers,
            json={"note": "Título corrigido conforme solicitado."},
        )
        assert resubmitted.status_code == 201, resubmitted.text
        assert resubmitted.json()["version"] == 2

        approved = client.post(
            f"/v1/workflow/approvals/{resubmitted.json()['id']}/decision",
            headers=headers,
            json={"decision": "approved", "note": "Aprovado para calendário."},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["project_status"] == "approved"

        future = datetime.now(timezone.utc) + timedelta(days=2)
        scheduled = client.post(
            f"/v1/workflow/projects/{project['id']}/schedule",
            headers=headers,
            json={
                "scheduled_for": future.isoformat(),
                "timezone": "America/Sao_Paulo",
                "note": "Faixa editorial da noite.",
            },
        )
        assert scheduled.status_code == 201, scheduled.text
        assert scheduled.json()["status"] == "reserved"

        calendar = client.get("/v1/workflow/calendar", headers=headers)
        assert calendar.status_code == 200
        assert any(item["id"] == scheduled.json()["id"] for item in calendar.json())

        notifications = client.get("/v1/workflow/notifications", headers=headers)
        assert notifications.status_code == 200
        assert notifications.json()["unread_count"] >= 1
        marked = client.post("/v1/workflow/notifications/read-all", headers=headers)
        assert marked.status_code == 204
        assert client.get(
            "/v1/workflow/notifications", headers=headers
        ).json()["unread_count"] == 0

        cancelled = client.delete(
            f"/v1/workflow/schedule/{scheduled.json()['id']}", headers=headers
        )
        assert cancelled.status_code == 204
