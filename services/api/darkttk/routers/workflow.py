import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from ..audit import write_audit
from ..dependencies import AuthContext, CurrentAuth, DbSession, require_roles
from ..models import (
    ApprovalEvent,
    ApprovalRequest,
    ApprovalStatus,
    Notification,
    OrganizationMember,
    Role,
    ScheduledSlot,
    ScheduleStatus,
    VideoProject,
    utcnow,
)
from ..workflow_schemas import (
    ApprovalDecision,
    ApprovalDecisionRequest,
    ApprovalEventResponse,
    ApprovalResponse,
    ApprovalSubmitRequest,
    NotificationListResponse,
    NotificationResponse,
    ProjectWorkflowEditRequest,
    ScheduleCreateRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
)

router = APIRouter(prefix="/v1/workflow", tags=["Workflow"])
EDITOR_ROLES = (Role.ADMIN.value, Role.MANAGER.value, Role.EDITOR.value)
DECISION_ROLES = (Role.ADMIN.value, Role.MANAGER.value, Role.REVIEWER.value)
SCHEDULE_ROLES = (Role.ADMIN.value, Role.MANAGER.value)
REVIEWABLE_PROJECT_STATUSES = {
    "review",
    "preview_mock",
    "changes_requested",
    "rejected",
}
ACTIVE_SCHEDULE_STATUSES = {
    ScheduleStatus.RESERVED.value,
    ScheduleStatus.READY.value,
}


def owned_project(db: DbSession, organization_id: str, project_id: str) -> VideoProject:
    project = db.scalar(
        select(VideoProject).where(
            VideoProject.id == project_id,
            VideoProject.organization_id == organization_id,
        )
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return project


def owned_approval(
    db: DbSession, organization_id: str, approval_id: str
) -> ApprovalRequest:
    approval = db.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.organization_id == organization_id,
        )
    )
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return approval


def notification(
    db: DbSession,
    *,
    organization_id: str,
    recipient_id: str,
    kind: str,
    title: str,
    message: str,
    entity_type: str,
    entity_id: str,
) -> None:
    db.add(
        Notification(
            organization_id=organization_id,
            recipient_id=recipient_id,
            kind=kind,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    )


def notify_reviewers(
    db: DbSession,
    *,
    organization_id: str,
    approval: ApprovalRequest,
    project: VideoProject,
) -> None:
    reviewer_ids = db.scalars(
        select(OrganizationMember.user_id).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role.in_(DECISION_ROLES),
        )
    )
    for recipient_id in set(reviewer_ids):
        notification(
            db,
            organization_id=organization_id,
            recipient_id=recipient_id,
            kind="approval_requested",
            title="Novo vídeo para aprovação",
            message=f"“{project.title}” está aguardando sua decisão.",
            entity_type="approval_request",
            entity_id=approval.id,
        )


def approval_response(
    db: DbSession, approval: ApprovalRequest, *, include_events: bool = False
) -> ApprovalResponse:
    project = db.get(VideoProject, approval.video_project_id)
    events: list[ApprovalEventResponse] = []
    if include_events:
        rows = db.scalars(
            select(ApprovalEvent)
            .where(ApprovalEvent.approval_request_id == approval.id)
            .order_by(ApprovalEvent.created_at)
        )
        events = [ApprovalEventResponse.model_validate(row) for row in rows]
    return ApprovalResponse(
        id=approval.id,
        video_project_id=approval.video_project_id,
        project_title=project.title if project else "Projeto removido",
        project_status=project.status if project else "removed",
        preview_is_mock=bool(project and project.preview_manifest_json),
        version=approval.version,
        status=approval.status,
        requested_by=approval.requested_by,
        decided_by=approval.decided_by,
        request_note=approval.request_note,
        decision_note=approval.decision_note,
        decided_at=approval.decided_at,
        created_at=approval.created_at,
        updated_at=approval.updated_at,
        events=events,
    )


def schedule_response(db: DbSession, slot: ScheduledSlot) -> ScheduleResponse:
    project = db.get(VideoProject, slot.video_project_id)
    return ScheduleResponse(
        id=slot.id,
        video_project_id=slot.video_project_id,
        project_title=project.title if project else "Projeto removido",
        approval_request_id=slot.approval_request_id,
        scheduled_for=slot.scheduled_for,
        timezone=slot.timezone,
        status=slot.status,
        note=slot.note,
        created_at=slot.created_at,
        updated_at=slot.updated_at,
    )


def normalize_schedule_time(value: datetime, timezone_name: str) -> datetime:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_timezone", "message": "Fuso horário inválido."},
        ) from error
    localized = value.replace(tzinfo=zone) if value.tzinfo is None else value.astimezone(zone)
    normalized = localized.astimezone(timezone.utc)
    if normalized < utcnow() + timedelta(minutes=5):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "schedule_in_past",
                "message": "Escolha um horário com pelo menos cinco minutos de antecedência.",
            },
        )
    return normalized


def validate_schedule_capacity(
    db: DbSession,
    *,
    organization_id: str,
    scheduled_for: datetime,
    timezone_name: str,
    exclude_slot_id: str | None = None,
) -> None:
    conflict_query = select(ScheduledSlot.id).where(
        ScheduledSlot.organization_id == organization_id,
        ScheduledSlot.status.in_(ACTIVE_SCHEDULE_STATUSES),
        ScheduledSlot.scheduled_for >= scheduled_for - timedelta(minutes=15),
        ScheduledSlot.scheduled_for <= scheduled_for + timedelta(minutes=15),
    )
    if exclude_slot_id:
        conflict_query = conflict_query.where(ScheduledSlot.id != exclude_slot_id)
    if db.scalar(conflict_query.limit(1)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "schedule_conflict",
                "message": "Já existe uma publicação em uma janela de 15 minutos.",
            },
        )
    zone = ZoneInfo(timezone_name)
    local_date = scheduled_for.astimezone(zone).date()
    start_utc = datetime.combine(local_date, datetime.min.time(), zone).astimezone(
        timezone.utc
    )
    end_utc = start_utc + timedelta(days=1)
    daily_query = select(func.count(ScheduledSlot.id)).where(
        ScheduledSlot.organization_id == organization_id,
        ScheduledSlot.status.in_(ACTIVE_SCHEDULE_STATUSES),
        ScheduledSlot.scheduled_for >= start_utc,
        ScheduledSlot.scheduled_for < end_utc,
    )
    if exclude_slot_id:
        daily_query = daily_query.where(ScheduledSlot.id != exclude_slot_id)
    if (db.scalar(daily_query) or 0) >= 5:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "daily_schedule_limit",
                "message": "O limite operacional é de cinco publicações por dia.",
            },
        )


@router.get("/approvals", response_model=list[ApprovalResponse])
def list_approvals(
    context: CurrentAuth,
    db: DbSession,
    approval_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
):
    query = select(ApprovalRequest).where(
        ApprovalRequest.organization_id == context.membership.organization_id
    )
    if approval_status:
        if approval_status not in {item.value for item in ApprovalStatus}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
        query = query.where(ApprovalRequest.status == approval_status)
    approvals = db.scalars(
        query.order_by(ApprovalRequest.created_at.desc()).limit(limit)
    )
    return [approval_response(db, item) for item in approvals]


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
def get_approval(approval_id: str, context: CurrentAuth, db: DbSession):
    approval = owned_approval(
        db, context.membership.organization_id, approval_id
    )
    return approval_response(db, approval, include_events=True)


@router.post(
    "/projects/{project_id}/approval-requests",
    response_model=ApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_for_approval(
    project_id: str,
    payload: ApprovalSubmitRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*EDITOR_ROLES)),
):
    organization_id = context.membership.organization_id
    project = owned_project(db, organization_id, project_id)
    if project.status not in REVIEWABLE_PROJECT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "project_not_reviewable",
                "message": "O projeto precisa ter uma prévia ou render concluído.",
            },
        )
    latest = db.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.video_project_id == project.id)
        .order_by(ApprovalRequest.version.desc())
        .limit(1)
    )
    if latest and latest.status == ApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "approval_already_pending", "message": "Já existe uma revisão pendente."},
        )
    approval = ApprovalRequest(
        organization_id=organization_id,
        video_project_id=project.id,
        requested_by=context.user.id,
        version=(latest.version + 1) if latest else 1,
        status=ApprovalStatus.PENDING.value,
        request_note=(payload.note or "").strip() or None,
    )
    db.add(approval)
    db.flush()
    db.add(
        ApprovalEvent(
            organization_id=organization_id,
            approval_request_id=approval.id,
            actor_id=context.user.id,
            event_type="submitted" if latest is None else "resubmitted",
            note=approval.request_note,
        )
    )
    project.status = "review"
    notify_reviewers(db, organization_id=organization_id, approval=approval, project=project)
    write_audit(
        db,
        organization_id=organization_id,
        actor_id=context.user.id,
        action="approval.submitted",
        entity_type="approval_request",
        entity_id=approval.id,
        metadata={"project_id": project.id, "version": approval.version},
    )
    db.commit()
    return approval_response(db, approval, include_events=True)


@router.post(
    "/approvals/{approval_id}/decision",
    response_model=ApprovalResponse,
)
def decide_approval(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*DECISION_ROLES)),
):
    organization_id = context.membership.organization_id
    approval = owned_approval(db, organization_id, approval_id)
    if approval.status != ApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "approval_already_decided", "message": "Esta revisão já foi decidida."},
        )
    project = owned_project(db, organization_id, approval.video_project_id)
    approval.status = payload.decision.value
    approval.decided_by = context.user.id
    approval.decision_note = (payload.note or "").strip() or None
    approval.decided_at = utcnow()
    if payload.decision == ApprovalDecision.APPROVED:
        project.status = "approved"
        title = "Vídeo aprovado"
        message = f"“{project.title}” foi aprovado e pode ser agendado."
    elif payload.decision == ApprovalDecision.CHANGES_REQUESTED:
        project.status = "changes_requested"
        title = "Alterações solicitadas"
        message = f"“{project.title}” precisa de ajustes antes de uma nova revisão."
    else:
        project.status = "rejected"
        title = "Vídeo reprovado"
        message = f"“{project.title}” foi reprovado."
    db.add(
        ApprovalEvent(
            organization_id=organization_id,
            approval_request_id=approval.id,
            actor_id=context.user.id,
            event_type=payload.decision.value,
            note=approval.decision_note,
        )
    )
    notification(
        db,
        organization_id=organization_id,
        recipient_id=approval.requested_by,
        kind=f"approval_{payload.decision.value}",
        title=title,
        message=message,
        entity_type="approval_request",
        entity_id=approval.id,
    )
    write_audit(
        db,
        organization_id=organization_id,
        actor_id=context.user.id,
        action=f"approval.{payload.decision.value}",
        entity_type="approval_request",
        entity_id=approval.id,
        metadata={"project_id": project.id, "note": approval.decision_note},
    )
    db.commit()
    return approval_response(db, approval, include_events=True)


@router.patch("/projects/{project_id}", response_model=ApprovalResponse)
def edit_project_for_review(
    project_id: str,
    payload: ProjectWorkflowEditRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*EDITOR_ROLES)),
):
    organization_id = context.membership.organization_id
    project = owned_project(db, organization_id, project_id)
    latest = db.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.video_project_id == project.id)
        .order_by(ApprovalRequest.version.desc())
        .limit(1)
    )
    if latest is None or latest.status not in {
        ApprovalStatus.CHANGES_REQUESTED.value,
        ApprovalStatus.REJECTED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "project_edit_locked",
                "message": "Edições são liberadas após pedido de alteração ou reprovação.",
            },
        )
    changes = payload.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(project, field, value)
    project.status = "changes_requested"
    db.add(
        ApprovalEvent(
            organization_id=organization_id,
            approval_request_id=latest.id,
            actor_id=context.user.id,
            event_type="project_edited",
            payload_json=json.dumps(changes, ensure_ascii=False, separators=(",", ":")),
        )
    )
    write_audit(
        db,
        organization_id=organization_id,
        actor_id=context.user.id,
        action="project.review_edit",
        entity_type="video_project",
        entity_id=project.id,
        metadata={"fields": sorted(changes)},
    )
    db.commit()
    return approval_response(db, latest, include_events=True)


def create_or_update_schedule(
    *,
    db: DbSession,
    context: AuthContext,
    project: VideoProject,
    payload: ScheduleCreateRequest | ScheduleUpdateRequest,
    existing: ScheduledSlot | None = None,
) -> ScheduledSlot:
    organization_id = context.membership.organization_id
    approval = db.scalar(
        select(ApprovalRequest)
        .where(
            ApprovalRequest.video_project_id == project.id,
            ApprovalRequest.status == ApprovalStatus.APPROVED.value,
        )
        .order_by(ApprovalRequest.version.desc())
        .limit(1)
    )
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "approval_required", "message": "O vídeo precisa ser aprovado antes do agendamento."},
        )
    scheduled_for = normalize_schedule_time(payload.scheduled_for, payload.timezone)
    validate_schedule_capacity(
        db,
        organization_id=organization_id,
        scheduled_for=scheduled_for,
        timezone_name=payload.timezone,
        exclude_slot_id=existing.id if existing else None,
    )
    if existing:
        slot = existing
        slot.scheduled_for = scheduled_for
        slot.timezone = payload.timezone
        slot.note = (payload.note or "").strip() or None
        action = "schedule.rescheduled"
    else:
        active = db.scalar(
            select(ScheduledSlot.id).where(
                ScheduledSlot.video_project_id == project.id,
                ScheduledSlot.status.in_(ACTIVE_SCHEDULE_STATUSES),
            )
        )
        if active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "project_already_scheduled", "message": "O projeto já possui um horário ativo."},
            )
        slot = ScheduledSlot(
            organization_id=organization_id,
            video_project_id=project.id,
            approval_request_id=approval.id,
            created_by=context.user.id,
            scheduled_for=scheduled_for,
            timezone=payload.timezone,
            status=ScheduleStatus.RESERVED.value,
            note=(payload.note or "").strip() or None,
        )
        db.add(slot)
        db.flush()
        action = "schedule.created"
    project.status = "scheduled"
    notification(
        db,
        organization_id=organization_id,
        recipient_id=project.created_by,
        kind="schedule_updated",
        title="Publicação agendada",
        message=f"“{project.title}” foi reservado para {scheduled_for.isoformat()}.",
        entity_type="scheduled_slot",
        entity_id=slot.id,
    )
    write_audit(
        db,
        organization_id=organization_id,
        actor_id=context.user.id,
        action=action,
        entity_type="scheduled_slot",
        entity_id=slot.id,
        metadata={"project_id": project.id, "scheduled_for": scheduled_for.isoformat()},
    )
    db.commit()
    return slot


@router.post(
    "/projects/{project_id}/schedule",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def schedule_project(
    project_id: str,
    payload: ScheduleCreateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*SCHEDULE_ROLES)),
):
    project = owned_project(db, context.membership.organization_id, project_id)
    slot = create_or_update_schedule(
        db=db, context=context, project=project, payload=payload
    )
    return schedule_response(db, slot)


@router.patch("/schedule/{slot_id}", response_model=ScheduleResponse)
def reschedule_project(
    slot_id: str,
    payload: ScheduleUpdateRequest,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*SCHEDULE_ROLES)),
):
    slot = db.scalar(
        select(ScheduledSlot).where(
            ScheduledSlot.id == slot_id,
            ScheduledSlot.organization_id == context.membership.organization_id,
            ScheduledSlot.status.in_(ACTIVE_SCHEDULE_STATUSES),
        )
    )
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    project = owned_project(
        db, context.membership.organization_id, slot.video_project_id
    )
    updated = create_or_update_schedule(
        db=db, context=context, project=project, payload=payload, existing=slot
    )
    return schedule_response(db, updated)


@router.delete("/schedule/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_schedule(
    slot_id: str,
    db: DbSession,
    context: AuthContext = Depends(require_roles(*SCHEDULE_ROLES)),
):
    slot = db.scalar(
        select(ScheduledSlot).where(
            ScheduledSlot.id == slot_id,
            ScheduledSlot.organization_id == context.membership.organization_id,
            ScheduledSlot.status.in_(ACTIVE_SCHEDULE_STATUSES),
        )
    )
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    slot.status = ScheduleStatus.CANCELLED.value
    project = db.get(VideoProject, slot.video_project_id)
    if project:
        project.status = "approved"
    write_audit(
        db,
        organization_id=context.membership.organization_id,
        actor_id=context.user.id,
        action="schedule.cancelled",
        entity_type="scheduled_slot",
        entity_id=slot.id,
        metadata={"project_id": slot.video_project_id},
    )
    db.commit()


@router.get("/calendar", response_model=list[ScheduleResponse])
def list_calendar(
    context: CurrentAuth,
    db: DbSession,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
):
    start = from_ or (utcnow() - timedelta(days=7))
    end = to or (utcnow() + timedelta(days=30))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if end <= start or end - start > timedelta(days=180):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    slots = db.scalars(
        select(ScheduledSlot)
        .where(
            ScheduledSlot.organization_id == context.membership.organization_id,
            ScheduledSlot.scheduled_for >= start,
            ScheduledSlot.scheduled_for <= end,
        )
        .order_by(ScheduledSlot.scheduled_for)
    )
    return [schedule_response(db, slot) for slot in slots]


@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    context: CurrentAuth,
    db: DbSession,
    unread_only: bool = False,
    limit: int = Query(default=30, ge=1, le=100),
):
    query = select(Notification).where(
        Notification.organization_id == context.membership.organization_id,
        Notification.recipient_id == context.user.id,
    )
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    items = list(db.scalars(query.order_by(Notification.created_at.desc()).limit(limit)))
    unread_count = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.organization_id == context.membership.organization_id,
            Notification.recipient_id == context.user.id,
            Notification.read_at.is_(None),
        )
    )
    return NotificationListResponse(unread_count=unread_count or 0, items=items)


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_read(
    notification_id: str, context: CurrentAuth, db: DbSession
):
    item = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == context.membership.organization_id,
            Notification.recipient_id == context.user.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    item.read_at = item.read_at or utcnow()
    db.commit()
    return item


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(context: CurrentAuth, db: DbSession):
    items = db.scalars(
        select(Notification).where(
            Notification.organization_id == context.membership.organization_id,
            Notification.recipient_id == context.user.id,
            Notification.read_at.is_(None),
        )
    )
    now = utcnow()
    for item in items:
        item.read_at = now
    db.commit()
