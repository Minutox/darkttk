from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from ..content_schemas import ProviderResponse, ProviderUpdateRequest
from ..content_seed import ensure_content_defaults
from ..dependencies import AuthContext, CurrentAuth, DbSession, require_roles
from ..models import AiProvider, Role

router = APIRouter(prefix="/v1/providers", tags=["Providers"])


def provider_response(item: AiProvider) -> ProviderResponse:
    return ProviderResponse(
        id=item.id,
        capability=item.capability,
        provider_key=item.provider_key,
        display_name=item.display_name,
        enabled=item.enabled,
        is_mock=item.is_mock,
        secret_configured=item.secret_ref is not None,
    )


@router.get("", response_model=list[ProviderResponse])
def list_providers(context: CurrentAuth, db: DbSession):
    ensure_content_defaults(db, context.membership.organization_id)
    db.commit()
    providers = list(
        db.scalars(
            select(AiProvider)
            .where(AiProvider.organization_id == context.membership.organization_id)
            .order_by(AiProvider.capability, AiProvider.display_name)
        )
    )
    return [provider_response(item) for item in providers]


@router.patch("/{provider_id}", response_model=ProviderResponse)
def update_provider(
    provider_id: str,
    payload: ProviderUpdateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(Role.ADMIN.value)),
):
    item = db.scalar(
        select(AiProvider).where(
            AiProvider.id == provider_id,
            AiProvider.organization_id == context.membership.organization_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not item.is_mock:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "code": "provider_adapter_unavailable",
                "message": "O adaptador real ainda não está conectado nesta fase.",
            },
        )
    item.enabled = payload.enabled
    item.secret_ref = payload.secret_ref
    db.commit()
    return provider_response(item)
