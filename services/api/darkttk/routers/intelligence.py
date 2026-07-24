from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from ..audit import write_audit
from ..dependencies import AuthContext, CurrentAuth, DbSession, require_roles
from ..intelligence_schemas import (
    ContentSeriesCreate,
    ContentSeriesResponse,
    TrendSignalCreate,
    TrendSignalResponse,
    TrendSourceCreate,
    TrendSourceResponse,
)
from ..models import ContentNiche, ContentSeries, Role, TrendSignal, TrendSource

router = APIRouter(prefix="/v1/intelligence", tags=["Intelligence"])
EDITOR_ROLES = (Role.ADMIN.value, Role.MANAGER.value, Role.EDITOR.value)


@router.get("/trend-sources", response_model=list[TrendSourceResponse])
def list_trend_sources(context: CurrentAuth, db: DbSession):
    return list(
        db.scalars(
            select(TrendSource)
            .where(TrendSource.organization_id == context.membership.organization_id)
            .order_by(TrendSource.name)
        )
    )


@router.post(
    "/trend-sources",
    response_model=TrendSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_trend_source(
    payload: TrendSourceCreate,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*EDITOR_ROLES)),
):
    if not payload.authorization_confirmed:
        raise HTTPException(
            status_code=422,
            detail={"code": "source_authorization_required"},
        )
    source = TrendSource(
        organization_id=context.membership.organization_id,
        name=payload.name.strip(),
        connector_type=payload.connector_type,
        endpoint_url=str(payload.endpoint_url) if payload.endpoint_url else None,
        terms_url=str(payload.terms_url),
        authorized_at=datetime.now(timezone.utc),
    )
    db.add(source)
    db.flush()
    write_audit(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        action="trend_source.created",
        entity_type="trend_source",
        entity_id=source.id,
    )
    db.commit()
    return source


@router.get("/trends", response_model=list[TrendSignalResponse])
def list_trends(context: CurrentAuth, db: DbSession, limit: int = 50):
    return list(
        db.scalars(
            select(TrendSignal)
            .where(TrendSignal.organization_id == context.membership.organization_id)
            .order_by(TrendSignal.captured_at.desc())
            .limit(min(max(limit, 1), 100))
        )
    )


@router.post("/trends", response_model=TrendSignalResponse, status_code=201)
def ingest_trend(
    payload: TrendSignalCreate,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*EDITOR_ROLES)),
):
    source = db.scalar(
        select(TrendSource).where(
            TrendSource.id == payload.source_id,
            TrendSource.organization_id == context.membership.organization_id,
            TrendSource.enabled.is_(True),
        )
    )
    if source is None:
        raise HTTPException(status_code=404, detail={"code": "authorized_source_not_found"})
    if payload.valid_until <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail={"code": "trend_validity_expired"})
    signal = TrendSignal(
        organization_id=context.membership.organization_id,
        **payload.model_dump(),
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


@router.get("/series", response_model=list[ContentSeriesResponse])
def list_series(context: CurrentAuth, db: DbSession):
    return list(
        db.scalars(
            select(ContentSeries)
            .where(ContentSeries.organization_id == context.membership.organization_id)
            .order_by(ContentSeries.created_at.desc())
        )
    )


@router.post("/series", response_model=ContentSeriesResponse, status_code=201)
def create_series(
    payload: ContentSeriesCreate,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*EDITOR_ROLES)),
):
    if payload.niche_id and db.scalar(
        select(ContentNiche).where(
            ContentNiche.id == payload.niche_id,
            ContentNiche.organization_id == context.membership.organization_id,
        )
    ) is None:
        raise HTTPException(status_code=404, detail={"code": "niche_not_found"})
    series = ContentSeries(
        organization_id=context.membership.organization_id,
        created_by=context.user.id,
        **payload.model_dump(),
    )
    db.add(series)
    db.flush()
    write_audit(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        action="content_series.created",
        entity_type="content_series",
        entity_id=series.id,
    )
    db.commit()
    return series
