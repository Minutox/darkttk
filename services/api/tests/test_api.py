import os
import hashlib
import hmac
import time

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["APP_SECRET"] = "test-secret-with-at-least-thirty-two-characters"
os.environ["AUTO_CREATE_SCHEMA"] = "true"

from fastapi.testclient import TestClient

from darkttk.main import app
from darkttk.account_security import totp_code


def register(client: TestClient, suffix: str = "owner") -> dict[str, str]:
    response = client.post(
        "/v1/auth/register",
        json={
            "email": f"{suffix}@example.com",
            "display_name": "Conta de Teste",
            "password": "Senha#Segura2026",
            "organization_name": f"Estúdio {suffix}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def authorization(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_health_and_security_headers():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Permissions-Policy"].startswith("camera=()")
        assert response.headers["Content-Security-Policy"].startswith("default-src")
        assert client.get("/health/live").json()["status"] == "alive"
        assert client.get("/health/ready").status_code == 200


def test_rate_limit_and_metrics_are_available_in_development():
    with TestClient(app) as client:
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "darkttk_http_requests_total" in metrics.text


def test_operations_budget_and_audit_checkpoint():
    with TestClient(app) as client:
        tokens = register(client, "operations-flow")
        headers = authorization(tokens)
        status_response = client.get("/v1/operations/status", headers=headers)
        assert status_response.status_code == 200
        assert status_response.json()["is_mock"] is False

        budget = client.put(
            "/v1/operations/costs/budget",
            headers=headers,
            json={
                "monthly_limit_cents": 75000,
                "warning_percent": 75,
                "hard_stop_enabled": False,
                "currency": "BRL",
            },
        )
        assert budget.status_code == 200
        assert budget.json()["monthly_limit_cents"] == 75000

        cost = client.post(
            "/v1/operations/costs/entries",
            headers=headers,
            json={
                "provider": "mock-local-v1",
                "category": "generation",
                "amount_micros": 250000,
                "source_ref": "operations-test-cost-001",
                "is_mock": False,
            },
        )
        assert cost.status_code == 201
        summary = client.get("/v1/operations/costs/summary", headers=headers)
        assert summary.status_code == 200
        assert summary.json()["spent_cents"] == 25

        checkpoint = client.post("/v1/operations/audit/checkpoints", headers=headers)
        assert checkpoint.status_code == 201
        verified = client.get(
            f"/v1/operations/audit/checkpoints/{checkpoint.json()['id']}/verify",
            headers=headers,
        )
        assert verified.status_code == 200
        assert verified.json()["valid"] is True


def test_registration_login_and_current_user():
    with TestClient(app) as client:
        tokens = register(client, "auth-flow")
        me = client.get("/v1/auth/me", headers=authorization(tokens))
        assert me.status_code == 200
        assert me.json()["email"] == "auth-flow@example.com"
        assert me.json()["role"] == "admin"

        login = client.post(
            "/v1/auth/login",
            json={"email": "AUTH-FLOW@example.com", "password": "Senha#Segura2026"},
        )
        assert login.status_code == 200
        assert login.json()["token_type"] == "bearer"


def test_signed_workspace_identity_exchange_provisions_session():
    timestamp = str(int(time.time()))
    email = "workspace-user@example.com"
    display_name = "Pessoa Workspace"
    canonical = f"{timestamp}\n{email}\n{display_name}".encode()
    signature = hmac.new(
        b"test-workspace-identity-secret-at-least-32",
        canonical,
        hashlib.sha256,
    ).hexdigest()
    with TestClient(app) as client:
        exchanged = client.post(
            "/v1/auth/workspace-exchange",
            headers={
                "X-Workspace-Timestamp": timestamp,
                "X-Workspace-Signature": signature,
            },
            json={"email": email, "display_name": display_name},
        )
        assert exchanged.status_code == 200, exchanged.text
        me = client.get(
            "/v1/auth/me",
            headers=authorization(exchanged.json()),
        )
        assert me.status_code == 200
        assert me.json()["email"] == email
        assert me.json()["role"] == "admin"


def test_refresh_token_is_rotated():
    with TestClient(app) as client:
        tokens = register(client, "refresh-flow")
        first = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert first.status_code == 200
        assert first.json()["refresh_token"] != tokens["refresh_token"]

        replay = client.post(
            "/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert replay.status_code == 401


def test_password_recovery_is_single_use_and_revokes_sessions():
    with TestClient(app) as client:
        tokens = register(client, "recovery-flow")
        requested = client.post(
            "/v1/auth/password-recovery/request",
            json={"email": "recovery-flow@example.com"},
        )
        assert requested.status_code == 202
        assert requested.json()["delivery_mode"] == "mock"
        recovery_token = requested.json()["development_token"]
        assert recovery_token

        confirmed = client.post(
            "/v1/auth/password-recovery/confirm",
            json={
                "token": recovery_token,
                "new_password": "Nova#SenhaSegura2026",
            },
        )
        assert confirmed.status_code == 204
        assert client.post(
            "/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        ).status_code == 401
        assert client.post(
            "/v1/auth/password-recovery/confirm",
            json={
                "token": recovery_token,
                "new_password": "Outra#SenhaSegura2026",
            },
        ).status_code == 400
        login = client.post(
            "/v1/auth/login",
            json={
                "email": "recovery-flow@example.com",
                "password": "Nova#SenhaSegura2026",
            },
        )
        assert login.status_code == 200


def test_mfa_requires_second_factor_and_consumes_recovery_code():
    with TestClient(app) as client:
        tokens = register(client, "mfa-flow")
        headers = authorization(tokens)
        setup = client.post("/v1/auth/mfa/setup", headers=headers)
        assert setup.status_code == 200
        code, _ = totp_code(setup.json()["secret"])
        confirmed = client.post(
            "/v1/auth/mfa/confirm",
            headers=headers,
            json={"code": code},
        )
        assert confirmed.status_code == 200
        recovery_code = confirmed.json()["recovery_codes"][0]

        without_code = client.post(
            "/v1/auth/login",
            json={"email": "mfa-flow@example.com", "password": "Senha#Segura2026"},
        )
        assert without_code.status_code == 401
        assert without_code.json()["detail"]["code"] == "mfa_required"

        with_recovery = client.post(
            "/v1/auth/login",
            json={
                "email": "mfa-flow@example.com",
                "password": "Senha#Segura2026",
                "mfa_code": recovery_code,
            },
        )
        assert with_recovery.status_code == 200
        replay = client.post(
            "/v1/auth/login",
            json={
                "email": "mfa-flow@example.com",
                "password": "Senha#Segura2026",
                "mfa_code": recovery_code,
            },
        )
        assert replay.status_code == 401
        assert replay.json()["detail"]["code"] == "invalid_mfa_code"


def test_mfa_recovery_codes_can_be_rotated_once_authenticated():
    with TestClient(app) as client:
        tokens = register(client, "mfa-rotate")
        headers = authorization(tokens)
        setup = client.post("/v1/auth/mfa/setup", headers=headers)
        code, _ = totp_code(setup.json()["secret"])
        confirmed = client.post(
            "/v1/auth/mfa/confirm", headers=headers, json={"code": code}
        )
        old_code = confirmed.json()["recovery_codes"][0]
        rotated = client.post(
            "/v1/auth/mfa/recovery-codes",
            headers=headers,
            json={"code": old_code},
        )
        assert rotated.status_code == 200
        assert len(rotated.json()["recovery_codes"]) == 8
        assert old_code not in rotated.json()["recovery_codes"]
        assert client.post(
            "/v1/auth/mfa/recovery-codes",
            headers=headers,
            json={"code": old_code},
        ).status_code == 400


def test_admin_can_invite_member_and_last_admin_is_protected():
    with TestClient(app) as client:
        tokens = register(client, "rbac-flow")
        headers = authorization(tokens)
        invited = client.post(
            "/v1/organizations/current/members",
            headers=headers,
            json={
                "email": "editor@example.com",
                "display_name": "Pessoa Editora",
                "role": "editor",
            },
        )
        assert invited.status_code == 201
        assert invited.json()["role"] == "editor"

        members = client.get("/v1/organizations/current/members", headers=headers)
        assert members.status_code == 200
        assert len(members.json()) == 2

        owner = next(member for member in members.json() if member["role"] == "admin")
        demotion = client.patch(
            f"/v1/organizations/current/members/{owner['id']}",
            headers=headers,
            json={"role": "viewer"},
        )
        assert demotion.status_code == 409
        assert demotion.json()["detail"]["code"] == "last_admin"


def test_dashboard_requires_authentication():
    with TestClient(app) as client:
        assert client.get("/v1/dashboard").status_code == 401
        tokens = register(client, "dashboard-flow")
        response = client.get("/v1/dashboard", headers=authorization(tokens))
        assert response.status_code == 200
        assert response.json()["daily_limit"] == 5
