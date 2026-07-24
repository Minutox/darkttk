from fastapi import APIRouter
from sqlalchemy import func, select

from ..dependencies import CurrentAuth, DbSession
from ..models import ApprovalRequest, ScheduledSlot, VideoProject

router = APIRouter(prefix="/v1/dashboard", tags=["Dashboard"])


@router.get("")
def dashboard(context: CurrentAuth, db: DbSession):
    organization_id = context.membership.organization_id
    awaiting_approval = db.scalar(
        select(func.count(ApprovalRequest.id)).where(
            ApprovalRequest.organization_id == organization_id,
            ApprovalRequest.status == "pending",
        )
    )
    scheduled = db.scalar(
        select(func.count(ScheduledSlot.id)).where(
            ScheduledSlot.organization_id == organization_id,
            ScheduledSlot.status.in_(("reserved", "ready")),
        )
    )
    in_production = db.scalar(
        select(func.count(VideoProject.id)).where(
            VideoProject.organization_id == organization_id,
            VideoProject.status.in_(("assembling", "queued", "rendering")),
        )
    )
    published = db.scalar(
        select(func.count(VideoProject.id)).where(
            VideoProject.organization_id == organization_id,
            VideoProject.status == "published",
        )
    )
    return {
        "organization_id": organization_id,
        "published_today": published or 0,
        "daily_limit": 5,
        "awaiting_approval": awaiting_approval or 0,
        "in_production": in_production or 0,
        "scheduled": scheduled or 0,
        "health": "operational",
    }
