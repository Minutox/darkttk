from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from re import sub
from uuid import uuid4

import jwt
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from ..audit import write_audit
from ..account_security import (
    consume_mfa_code,
    deliver_password_recovery,
    generate_recovery_codes,
    new_totp_secret,
    provisioning_uri,
    random_token,
    recovery_digest,
    set_recovery_codes,
    verify_totp,
)
from ..content_seed import ensure_content_defaults
from ..dependencies import CurrentAuth, DbSession
from ..models import (
    Organization,
    OrganizationMember,
    MfaCredential,
    PasswordRecoveryToken,
    RefreshToken,
    Role,
    User,
    UserStatus,
    utcnow,
)
from ..schemas import (
    LoginRequest,
    MfaCodeRequest,
    MfaConfirmResponse,
    MfaSetupResponse,
    MfaStatusResponse,
    OrganizationSummary,
    RefreshRequest,
    RegisterRequest,
    PasswordRecoveryConfirm,
    PasswordRecoveryRequest,
    PasswordRecoveryResponse,
    TokenResponse,
    UserResponse,
    WorkspaceExchangeRequest,
)
from ..token_crypto import TokenCipher
from ..config import get_settings
from ..security import (
    create_token_bundle,
    decode_token,
    hash_password,
    token_digest,
    verify_password,
)

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


def normalized_email(value: str) -> str:
    return value.strip().lower()


def organization_slug(name: str) -> str:
    base = sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "workspace"
    return f"{base}-{uuid4().hex[:6]}"


def persist_refresh_token(
    db: DbSession,
    *,
    user_id: str,
    organization_id: str,
    raw_token: str,
    jti: str,
    expires_at: datetime,
) -> RefreshToken:
    record = RefreshToken(
        user_id=user_id,
        organization_id=organization_id,
        jti=jti,
        token_hash=token_digest(raw_token),
        expires_at=expires_at,
    )
    db.add(record)
    return record


def token_response(
    db: DbSession, user_id: str, organization_id: str, role: str
) -> TokenResponse:
    bundle = create_token_bundle(user_id, organization_id, role)
    persist_refresh_token(
        db,
        user_id=user_id,
        organization_id=organization_id,
        raw_token=bundle.refresh_token,
        jti=bundle.refresh_jti,
        expires_at=bundle.refresh_expires_at,
    )
    return TokenResponse(
        access_token=bundle.access_token,
        refresh_token=bundle.refresh_token,
        expires_in=bundle.access_expires_in,
    )


@router.post("/workspace-exchange", response_model=TokenResponse)
def workspace_exchange(
    payload: WorkspaceExchangeRequest,
    request: Request,
    db: DbSession,
):
    settings = get_settings()
    if not settings.workspace_identity_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "workspace_exchange_disabled"},
        )
    timestamp = request.headers.get("X-Workspace-Timestamp", "")
    signature = request.headers.get("X-Workspace-Signature", "")
    try:
        request_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    except (ValueError, OSError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_workspace_signature"},
        )
    if abs((datetime.now(timezone.utc) - request_time).total_seconds()) > 60:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "expired_workspace_signature"},
        )

    email = normalized_email(str(payload.email))
    display_name = payload.display_name.strip()
    canonical = f"{timestamp}\n{email}\n{display_name}".encode()
    expected = hmac.new(
        settings.workspace_identity_secret.encode(), canonical, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_workspace_signature"},
        )

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            display_name=display_name,
            password_hash=None,
            status=UserStatus.ACTIVE.value,
        )
        db.add(user)
        db.flush()
    elif user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "account_disabled"},
        )

    membership = db.scalar(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    )
    if membership is None:
        organization = Organization(
            name=f"{display_name} Studio"[:120],
            slug=organization_slug(f"{display_name} Studio"),
        )
        db.add(organization)
        db.flush()
        membership = OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role=Role.ADMIN.value,
        )
        db.add(membership)
        ensure_content_defaults(db, organization.id)
        write_audit(
            db,
            organization_id=organization.id,
            actor_id=user.id,
            action="workspace.identity_provisioned",
            entity_type="user",
            entity_id=user.id,
        )

    response = token_response(
        db, user.id, membership.organization_id, membership.role
    )
    db.commit()
    return response


@router.post(
    "/password-recovery/request",
    response_model=PasswordRecoveryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_password_recovery(payload: PasswordRecoveryRequest, db: DbSession):
    email = normalized_email(str(payload.email))
    user = db.scalar(select(User).where(User.email == email))
    mode = get_settings().account_delivery_mode.lower()
    development_token = None
    if (
        user is not None
        and user.status == UserStatus.ACTIVE.value
        and mode in {"mock", "resend"}
    ):
        raw_token = random_token()
        db.add(
            PasswordRecoveryToken(
                user_id=user.id,
                token_hash=recovery_digest(raw_token),
                expires_at=utcnow()
                + timedelta(minutes=get_settings().password_recovery_minutes),
            )
        )
        try:
            result = deliver_password_recovery(email, raw_token)
            development_token = result.development_token
            db.commit()
        except Exception:
            db.rollback()
    return PasswordRecoveryResponse(
        delivery_mode=mode if mode in {"mock", "resend"} else "disabled",
        development_token=development_token,
    )


@router.post("/password-recovery/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_recovery(payload: PasswordRecoveryConfirm, db: DbSession):
    record = db.scalar(
        select(PasswordRecoveryToken).where(
            PasswordRecoveryToken.token_hash == recovery_digest(payload.token)
        )
    )
    now = utcnow()
    if (
        record is None
        or record.used_at is not None
        or record.expires_at.replace(tzinfo=record.expires_at.tzinfo or timezone.utc) <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_or_expired_recovery_token"},
        )
    user = db.get(User, record.user_id)
    if user is None or user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_or_expired_recovery_token"},
        )
    user.password_hash = hash_password(payload.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    record.used_at = now
    for refresh_token in db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
    ):
        refresh_token.revoked_at = now
    membership = db.scalar(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    )
    if membership:
        write_audit(
            db,
            organization_id=membership.organization_id,
            actor_id=user.id,
            action="account.password_recovered",
            entity_type="user",
            entity_id=user.id,
        )
    db.commit()


@router.get("/mfa", response_model=MfaStatusResponse)
def mfa_status(context: CurrentAuth, db: DbSession):
    credential = db.scalar(
        select(MfaCredential).where(MfaCredential.user_id == context.user.id)
    )
    recovery_count = (
        len(json.loads(credential.recovery_codes_json or "[]")) if credential else 0
    )
    return MfaStatusResponse(
        enabled=bool(credential and credential.enabled),
        confirmed_at=credential.confirmed_at if credential else None,
        recovery_codes_remaining=recovery_count,
    )


@router.post("/mfa/setup", response_model=MfaSetupResponse)
def setup_mfa(context: CurrentAuth, db: DbSession):
    secret = new_totp_secret()
    credential = db.scalar(
        select(MfaCredential).where(MfaCredential.user_id == context.user.id)
    )
    if credential is None:
        credential = MfaCredential(
            user_id=context.user.id,
            secret_ciphertext=TokenCipher().encrypt(secret),
            recovery_codes_json="[]",
            enabled=False,
        )
        db.add(credential)
    else:
        credential.secret_ciphertext = TokenCipher().encrypt(secret)
        credential.recovery_codes_json = "[]"
        credential.enabled = False
        credential.confirmed_at = None
        credential.last_used_step = None
    db.commit()
    return MfaSetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri(secret, context.user.email),
    )


@router.post("/mfa/confirm", response_model=MfaConfirmResponse)
def confirm_mfa(payload: MfaCodeRequest, context: CurrentAuth, db: DbSession):
    credential = db.scalar(
        select(MfaCredential).where(MfaCredential.user_id == context.user.id)
    )
    if credential is None:
        raise HTTPException(status_code=409, detail={"code": "mfa_setup_required"})
    secret = TokenCipher().decrypt(credential.secret_ciphertext)
    step = verify_totp(secret, payload.code)
    if step is None:
        raise HTTPException(status_code=400, detail={"code": "invalid_mfa_code"})
    recovery_codes = generate_recovery_codes()
    credential.enabled = True
    credential.confirmed_at = utcnow()
    credential.last_used_step = step
    set_recovery_codes(credential, recovery_codes)
    write_audit(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        action="account.mfa_enabled",
        entity_type="user",
        entity_id=context.user.id,
    )
    db.commit()
    return MfaConfirmResponse(enabled=True, recovery_codes=recovery_codes)


@router.post("/mfa/recovery-codes", response_model=MfaConfirmResponse)
def regenerate_mfa_recovery_codes(
    payload: MfaCodeRequest, context: CurrentAuth, db: DbSession
):
    credential = db.scalar(
        select(MfaCredential).where(
            MfaCredential.user_id == context.user.id,
            MfaCredential.enabled.is_(True),
        )
    )
    if credential is None or not consume_mfa_code(credential, payload.code):
        raise HTTPException(status_code=400, detail={"code": "invalid_mfa_code"})
    recovery_codes = generate_recovery_codes()
    set_recovery_codes(credential, recovery_codes)
    write_audit(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        action="account.mfa_recovery_codes_regenerated",
        entity_type="user",
        entity_id=context.user.id,
    )
    db.commit()
    return MfaConfirmResponse(enabled=True, recovery_codes=recovery_codes)


@router.delete("/mfa", status_code=status.HTTP_204_NO_CONTENT)
def disable_mfa(payload: MfaCodeRequest, context: CurrentAuth, db: DbSession):
    credential = db.scalar(
        select(MfaCredential).where(
            MfaCredential.user_id == context.user.id,
            MfaCredential.enabled.is_(True),
        )
    )
    if credential is None or not consume_mfa_code(credential, payload.code):
        raise HTTPException(status_code=400, detail={"code": "invalid_mfa_code"})
    db.delete(credential)
    write_audit(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        action="account.mfa_disabled",
        entity_type="user",
        entity_id=context.user.id,
    )
    db.commit()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: DbSession):
    email = normalized_email(str(payload.email))
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "email_in_use", "message": "Este e-mail já está cadastrado."},
        )

    user = User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        status=UserStatus.ACTIVE.value,
    )
    organization = Organization(
        name=payload.organization_name.strip(),
        slug=organization_slug(payload.organization_name),
    )
    db.add_all([user, organization])
    db.flush()
    membership = OrganizationMember(
        organization_id=organization.id,
        user_id=user.id,
        role=Role.ADMIN.value,
    )
    db.add(membership)
    ensure_content_defaults(db, organization.id)
    write_audit(
        db,
        organization_id=organization.id,
        actor_id=user.id,
        action="organization.created",
        entity_type="organization",
        entity_id=organization.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    response = token_response(db, user.id, organization.id, membership.role)
    db.commit()
    return response


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: DbSession):
    user = db.scalar(select(User).where(User.email == normalized_email(str(payload.email))))
    now = utcnow()
    if user is None or user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "E-mail ou senha inválidos."},
        )
    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "account_disabled", "message": "Esta conta não está ativa."},
        )
    locked_until = user.locked_until
    if locked_until is not None:
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "account_locked", "message": "Muitas tentativas. Tente novamente mais tarde."},
            )
    if not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
            user.failed_login_attempts = 0
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "E-mail ou senha inválidos."},
        )

    mfa = db.scalar(
        select(MfaCredential).where(
            MfaCredential.user_id == user.id,
            MfaCredential.enabled.is_(True),
        )
    )
    if mfa is not None:
        if payload.mfa_code is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "mfa_required", "message": "Informe o código de autenticação."},
            )
        if not consume_mfa_code(mfa, payload.mfa_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "invalid_mfa_code", "message": "Código de autenticação inválido."},
            )

    memberships = list(
        db.scalars(
            select(OrganizationMember).where(OrganizationMember.user_id == user.id)
        )
    )
    membership = next(
        (
            item
            for item in memberships
            if payload.organization_id is None or item.organization_id == payload.organization_id
        ),
        None,
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "organization_access_denied", "message": "Organização indisponível."},
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    write_audit(
        db,
        organization_id=membership.organization_id,
        actor_id=user.id,
        action="session.created",
        entity_type="user",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    response = token_response(db, user.id, membership.organization_id, membership.role)
    db.commit()
    return response


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DbSession):
    try:
        claims = decode_token(payload.refresh_token, "refresh")
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_refresh_token", "message": "Sessão expirada."},
        ) from exc

    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.jti == claims["jti"],
            RefreshToken.token_hash == token_digest(payload.refresh_token),
        )
    )
    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == claims["sub"],
            OrganizationMember.organization_id == claims["org"],
        )
    )
    if record is None or record.revoked_at is not None or membership is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "refresh_token_rejected", "message": "Sessão revogada."},
        )

    bundle = create_token_bundle(claims["sub"], claims["org"], membership.role)
    record.revoked_at = utcnow()
    record.replaced_by_jti = bundle.refresh_jti
    persist_refresh_token(
        db,
        user_id=claims["sub"],
        organization_id=claims["org"],
        raw_token=bundle.refresh_token,
        jti=bundle.refresh_jti,
        expires_at=bundle.refresh_expires_at,
    )
    db.commit()
    return TokenResponse(
        access_token=bundle.access_token,
        refresh_token=bundle.refresh_token,
        expires_in=bundle.access_expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, context: CurrentAuth, db: DbSession):
    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.user_id == context.user.id,
            RefreshToken.token_hash == token_digest(payload.refresh_token),
        )
    )
    if record is not None and record.revoked_at is None:
        record.revoked_at = utcnow()
        db.commit()


@router.get("/me", response_model=UserResponse)
def me(context: CurrentAuth, db: DbSession):
    organization = db.get(Organization, context.membership.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return UserResponse(
        id=context.user.id,
        email=context.user.email,
        display_name=context.user.display_name,
        role=context.membership.role,
        organization=OrganizationSummary(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            role=context.membership.role,
        ),
    )
