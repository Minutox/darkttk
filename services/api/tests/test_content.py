from uuid import uuid4

from fastapi.testclient import TestClient

from darkttk.main import app


def account(client: TestClient) -> tuple[dict[str, str], list[dict[str, object]]]:
    suffix = uuid4().hex[:8]
    response = client.post(
        "/v1/auth/register",
        json={
            "email": f"content-{suffix}@example.com",
            "display_name": "Editora de Conteúdo",
            "password": "Senha#Segura2026",
            "organization_name": f"Conteúdo {suffix}",
        },
    )
    assert response.status_code == 201, response.text
    tokens = response.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    niches = client.get("/v1/content/niches", headers=headers)
    assert niches.status_code == 200
    return headers, niches.json()


def test_default_niches_are_created():
    with TestClient(app) as client:
        _, niches = account(client)
        assert len(niches) == 16
        assert any(item["slug"] == "engenharia" for item in niches)
        assert any(item["slug"] == "analises-filmes" for item in niches)


def test_builtin_policy_blocks_politics_before_generation():
    with TestClient(app) as client:
        headers, niches = account(client)
        niche_id = next(item["id"] for item in niches if item["slug"] == "curiosidades")
        response = client.post(
            "/v1/content/ideas/generate",
            headers=headers,
            json={
                "niche_id": niche_id,
                "topic": "Estratégia de partido político para a próxima eleição",
                "objective": "explicar o cenário",
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "content_blocked"
        assert "politics" in response.json()["detail"]["rules"]


def test_custom_blocklist_is_enforced():
    with TestClient(app) as client:
        headers, niches = account(client)
        blocked = client.post(
            "/v1/content/blocked-topics",
            headers=headers,
            json={"term": "segredo industrial", "kind": "topic"},
        )
        assert blocked.status_code == 201
        niche_id = next(item["id"] for item in niches if item["slug"] == "engenharia")
        response = client.post(
            "/v1/content/ideas/generate",
            headers=headers,
            json={
                "niche_id": niche_id,
                "topic": "O segredo industrial das grandes pontes",
                "objective": "retenção",
            },
        )
        assert response.status_code == 422
        assert any(rule.startswith("custom:topic") for rule in response.json()["detail"]["rules"])


def test_mock_provider_generates_versioned_script_and_fact_check_history():
    with TestClient(app) as client:
        headers, niches = account(client)
        niche_id = next(item["id"] for item in niches if item["slug"] == "engenharia")
        idea = client.post(
            "/v1/content/ideas/generate",
            headers=headers,
            json={
                "niche_id": niche_id,
                "topic": "Por que pontes possuem juntas de dilatação",
                "objective": "educar com clareza",
            },
        )
        assert idea.status_code == 201, idea.text
        assert idea.json()["provider_is_mock"] is True
        assert idea.json()["risk_level"] == "low"

        script = client.post(
            f"/v1/content/ideas/{idea.json()['id']}/scripts/generate",
            headers=headers,
            json={"style": "documentary", "duration_seconds": 45},
        )
        assert script.status_code == 201, script.text
        assert script.json()["version"] == 1
        assert script.json()["provider_is_mock"] is True

        checks = client.post(
            f"/v1/content/scripts/{script.json()['id']}/fact-checks/run",
            headers=headers,
        )
        assert checks.status_code == 200, checks.text
        assert checks.json()
        assert all(item["verdict"] == "needs_review" for item in checks.json())
        assert all(item["provider_is_mock"] is True for item in checks.json())

        history = client.get(
            f"/v1/content/history/script/{script.json()['id']}",
            headers=headers,
        )
        assert history.status_code == 200
        event_types = [item["event_type"] for item in history.json()]
        assert "script.generated" in event_types
        assert "fact_check.completed" in event_types


def test_manual_revision_creates_next_version():
    with TestClient(app) as client:
        headers, niches = account(client)
        niche_id = next(item["id"] for item in niches if item["slug"] == "tecnologia")
        idea = client.post(
            "/v1/content/ideas/generate",
            headers=headers,
            json={
                "niche_id": niche_id,
                "topic": "Como funcionam sensores de proximidade",
                "objective": "educar",
            },
        ).json()
        first = client.post(
            f"/v1/content/ideas/{idea['id']}/scripts/generate",
            headers=headers,
            json={"style": "educational"},
        ).json()
        revision = client.post(
            f"/v1/content/scripts/{first['id']}/versions",
            headers=headers,
            json={
                "style": "educational",
                "reason": "Simplificar o vocabulário",
                "content": (
                    "Seu celular percebe objetos próximos usando um sensor dedicado. "
                    "O roteiro explica o princípio em linguagem simples e recomenda "
                    "confirmar detalhes técnicos na documentação do fabricante."
                ),
            },
        )
        assert revision.status_code == 201, revision.text
        assert revision.json()["version"] == 2
        assert revision.json()["provider_is_mock"] is False
