from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import OrganizationMember, User, UserStatus
from .security import decode_token

bearer = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


@dataclass(frozen=True)
class AuthContext:
    user: User
    membership: OrganizationMember


def get_auth_context(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthContext:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required", "message": "Autenticação necessária."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = decode_token(credentials.credentials, "access")
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Sessão inválida ou expirada."},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.get(User, claims["sub"])
    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == claims["sub"],
            OrganizationMember.organization_id == claims["org"],
        )
    )
    if (
        user is None
        or user.status != UserStatus.ACTIVE.value
        or membership is None
        or membership.role != claims["role"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_revoked", "message": "A sessão não é mais válida."},
        )
    return AuthContext(user=user, membership=membership)


CurrentAuth = Annotated[AuthContext, Depends(get_auth_context)]


def require_roles(*roles: str):
    def authorize(context: CurrentAuth) -> AuthContext:
        if context.membership.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "permission_denied", "message": "Permissão insuficiente."},
            )
        return context

    return authorize
