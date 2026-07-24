from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from darkttk.main import app
from darkttk.publishing_worker import chunk_plan
from darkttk.token_crypto import TokenCipher
from test_workflow import ready_video_project


def approved_schedule(client: TestClient) -> tuple[dict[str, str], dict[str, object]]:
    headers, project = ready_video_project(client)
    approval = client.post(
        f"/v1/workflow/projects/{project['id']}/approval-requests",
        headers=headers,
        json={"note": "Pronto para a publicação segura."},
    )
    assert approval.status_code == 201, approval.text
    decision = client.post(
        f"/v1/workflow/approvals/{approval.json()['id']}/decision",
        headers=headers,
        json={"decision": "approved", "note": "Conteúdo revisado."},
    )
    assert decision.status_code == 200, decision.text
    slot = client.post(
        f"/v1/workflow/projects/{project['id']}/schedule",
        headers=headers,
        json={
            "scheduled_for": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "timezone": "America/Sao_Paulo",
        },
    )
    assert slot.status_code == 201, slot.text
    return headers, slot.json()


def test_mock_publication_is_explicit_and_never_marks_project_published():
    with TestClient(app) as client:
        headers, slot = approved_schedule(client)
        connection = client.post("/v1/tiktok/connections/mock", headers=headers)
        assert connection.status_code == 201, connection.text
        assert connection.json()["is_mock"] is True
        creator = client.post(
            f"/v1/tiktok/connections/{connection.json()['id']}/creator-info",
            headers=headers,
        )
        assert creator.status_code == 200, creator.text
        assert creator.json()["is_mock"] is True

        payload = {
            "connection_id": connection.json()["id"],
            "publish_mode": "direct_post",
            "idempotency_key": f"publish-{uuid4().hex}",
            "caption": "Conteúdo educativo revisado.",
            "privacy_level": "SELF_ONLY",
            "allow_comment": False,
            "allow_duet": False,
            "allow_stitch": False,
            "is_aigc": True,
            "explicit_consent": True,
            "music_usage_confirmed": True,
        }
        published = client.post(
            f"/v1/tiktok/schedule/{slot['id']}/publication-jobs",
            headers=headers,
            json=payload,
        )
        assert published.status_code == 201, published.text
        body = published.json()
        assert body["status"] == "mock_complete"
        assert body["is_mock"] is True
        assert any(event["event_type"] == "mock.completed" for event in body["events"])

        duplicate = client.post(
            f"/v1/tiktok/schedule/{slot['id']}/publication-jobs",
            headers=headers,
            json=payload,
        )
        assert duplicate.status_code == 201
        assert duplicate.json()["id"] == body["id"]


def test_publication_requires_manual_consent_and_creator_privacy_option():
    with TestClient(app) as client:
        headers, slot = approved_schedule(client)
        connection = client.post("/v1/tiktok/connections/mock", headers=headers).json()
        client.post(
            f"/v1/tiktok/connections/{connection['id']}/creator-info",
            headers=headers,
        )
        base = {
            "connection_id": connection["id"],
            "publish_mode": "direct_post",
            "idempotency_key": f"publish-{uuid4().hex}",
            "caption": "Teste",
            "privacy_level": "SELF_ONLY",
            "allow_comment": False,
            "allow_duet": False,
            "allow_stitch": False,
            "explicit_consent": False,
            "music_usage_confirmed": True,
        }
        no_consent = client.post(
            f"/v1/tiktok/schedule/{slot['id']}/publication-jobs",
            headers=headers,
            json=base,
        )
        assert no_consent.status_code == 422

        invalid_privacy = client.post(
            f"/v1/tiktok/schedule/{slot['id']}/publication-jobs",
            headers=headers,
            json={
                **base,
                "idempotency_key": f"publish-{uuid4().hex}",
                "explicit_consent": True,
                "privacy_level": "NOT_A_PROVIDER_OPTION",
            },
        )
        assert invalid_privacy.status_code == 422
        assert invalid_privacy.json()["detail"]["code"] == "privacy_level_option_mismatch"


def test_token_cipher_and_upload_chunk_plan():
    encrypted = TokenCipher().encrypt("provider-secret")
    assert encrypted != "provider-secret"
    assert TokenCipher().decrypt(encrypted) == "provider-secret"
    assert chunk_plan(4 * 1024 * 1024) == (4 * 1024 * 1024, 1)
    assert chunk_plan(25 * 1024 * 1024) == (10 * 1024 * 1024, 2)
