from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from darkttk.main import app
from test_tiktok import approved_schedule


def mock_publication(client: TestClient):
    headers, slot = approved_schedule(client)
    connection = client.post("/v1/tiktok/connections/mock", headers=headers).json()
    client.post(
        f"/v1/tiktok/connections/{connection['id']}/creator-info",
        headers=headers,
    )
    published = client.post(
        f"/v1/tiktok/schedule/{slot['id']}/publication-jobs",
        headers=headers,
        json={
            "connection_id": connection["id"],
            "publish_mode": "direct_post",
            "idempotency_key": f"analytics-{uuid4().hex}",
            "caption": "Métrica simulada e identificada.",
            "privacy_level": "SELF_ONLY",
            "allow_comment": False,
            "allow_duet": False,
            "allow_stitch": False,
            "explicit_consent": True,
            "music_usage_confirmed": True,
        },
    )
    assert published.status_code == 201, published.text
    return headers, slot, published.json()


def test_metrics_retention_and_recommendations_are_traceable():
    with TestClient(app) as client:
        headers, _, publication = mock_publication(client)
        synced = client.post(
            f"/v1/analytics/publications/{publication['id']}/sync",
            headers=headers,
        )
        assert synced.status_code == 202, synced.text
        assert synced.json()["is_mock"] is True
        assert synced.json()["view_count"] > 0

        retention = client.post(
            f"/v1/analytics/publications/{publication['id']}/retention",
            headers=headers,
            json={
                "source": "manual_tiktok_analytics_export",
                "average_watch_time_seconds": 19.4,
                "completion_rate": 0.42,
                "watched_full_rate": 0.31,
                "saved_count": 84,
                "retention_curve": [1, 0.78, 0.61, 0.42],
                "collected_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        assert retention.status_code == 201, retention.text
        assert retention.json()["source"] == "manual_tiktok_analytics_export"

        overview = client.get("/v1/analytics/overview", headers=headers)
        assert overview.status_code == 200
        assert overview.json()["is_mock"] is True
        assert overview.json()["average_completion_rate"] == 0.42

        recommendations = client.post(
            "/v1/analytics/recommendations/generate", headers=headers
        )
        assert recommendations.status_code == 200, recommendations.text
        assert recommendations.json()
        assert recommendations.json()[0]["status"] == "open"


def test_experiment_requires_two_distinct_projects_and_tracks_state():
    with TestClient(app) as client:
        headers, slot, _ = mock_publication(client)
        first = client.get(
            f"/v1/video/projects/{slot['video_project_id']}", headers=headers
        )
        assert first.status_code == 200, first.text
        source = first.json()
        second = client.post(
            "/v1/video/projects",
            headers=headers,
            json={
                "script_id": source["script_id"],
                "title": "Variante B — gancho direto",
                "narration_asset_id": source["narration_asset_id"],
                "caption_track_id": source["caption_track_id"],
                "template_key": source["template_key"],
            },
        )
        assert second.status_code == 201, second.text
        experiment = client.post(
            "/v1/analytics/experiments",
            headers=headers,
            json={
                "name": "Gancho explicativo vs. direto",
                "hypothesis": "A abertura direta aumenta a taxa combinada de interação.",
                "variable": "hook",
                "primary_metric": "engagement_rate",
                "variants": [
                    {
                        "label": "A",
                        "video_project_id": source["id"],
                        "variable_value": "Você já percebeu por que isso acontece?",
                    },
                    {
                        "label": "B",
                        "video_project_id": second.json()["id"],
                        "variable_value": "Este erro reduz seu resultado em segundos.",
                    },
                ],
            },
        )
        assert experiment.status_code == 201, experiment.text
        assert len(experiment.json()["variants"]) == 2
        running = client.patch(
            f"/v1/analytics/experiments/{experiment.json()['id']}",
            headers=headers,
            json={"status": "running"},
        )
        assert running.status_code == 200
        assert running.json()["status"] == "running"
