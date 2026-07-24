from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from darkttk.main import app


def account(client: TestClient):
    suffix = uuid4().hex[:8]
    response = client.post(
        "/v1/auth/register",
        json={
            "email": f"intel-{suffix}@example.com",
            "display_name": "Estratégia Editorial",
            "password": "Senha#Segura2026",
            "organization_name": f"Inteligência {suffix}",
        },
    )
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    return headers, client.get("/v1/content/niches", headers=headers).json()


def test_authorized_trend_source_signal_and_series_are_persisted():
    with TestClient(app) as client:
        headers, niches = account(client)
        rejected = client.post(
            "/v1/intelligence/trend-sources",
            headers=headers,
            json={
                "name": "Fonte sem confirmação",
                "connector_type": "api",
                "endpoint_url": "https://example.com/api",
                "terms_url": "https://example.com/terms",
                "authorization_confirmed": False,
            },
        )
        assert rejected.status_code == 422
        source = client.post(
            "/v1/intelligence/trend-sources",
            headers=headers,
            json={
                "name": "API pública autorizada",
                "connector_type": "api",
                "endpoint_url": "https://example.com/api",
                "terms_url": "https://example.com/terms",
                "authorization_confirmed": True,
            },
        )
        assert source.status_code == 201, source.text
        trend = client.post(
            "/v1/intelligence/trends",
            headers=headers,
            json={
                "source_id": source.json()["id"],
                "topic": "Materiais que se autorreparam",
                "category": "Engenharia",
                "relevance_reason": "Sinal crescente confirmado pela fonte.",
                "growth_percent": 84.5,
                "interest_volume": 12000,
                "competition": "low",
                "retention_score": 91,
                "share_score": 87,
                "sensitivity_risk": "low",
                "saturation_risk": "low",
                "suggested_approach": "Explicação transformativa e original.",
                "likely_audience": "Curiosos por ciência",
                "valid_until": (datetime.now(timezone.utc) + timedelta(days=4)).isoformat(),
            },
        )
        assert trend.status_code == 201, trend.text
        niche_id = next(item["id"] for item in niches if item["slug"] == "engenharia")
        series = client.post(
            "/v1/intelligence/series",
            headers=headers,
            json={
                "name": "Engenharia invisível",
                "description": "Mecanismos cotidianos explicados com fontes.",
                "niche_id": niche_id,
                "cadence": "weekly",
                "target_episode_count": 12,
            },
        )
        assert series.status_code == 201, series.text
        assert len(client.get("/v1/intelligence/trends", headers=headers).json()) == 1
        assert len(client.get("/v1/intelligence/series", headers=headers).json()) == 1
