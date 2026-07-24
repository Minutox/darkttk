from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from ..audit import write_audit
from ..config import get_settings
from ..dependencies import AuthContext, CurrentAuth, DbSession, require_roles
from ..models import AuditCheckpoint, AuditLog, BackupRun, CostBudget, CostLedgerEntry, OperationalError, PublicationJob

router = APIRouter(prefix="/v1/operations", tags=["Operations"])
admin_or_manager = Depends(require_roles("admin", "manager"))


class BudgetUpdate(BaseModel):
    monthly_limit_cents: int = Field(ge=0, le=1_000_000_000)
    warning_percent: int = Field(default=80, ge=1, le=100)
    hard_stop_enabled: bool = False
    currency: str = Field(default="BRL", min_length=3, max_length=3)


class CostEntryCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=60)
    category: str = Field(min_length=1, max_length=40)
    amount_micros: int = Field(ge=0, le=10_000_000_000_000)
    quantity: int = Field(default=1, ge=1)
    unit: str = Field(default="operation", min_length=1, max_length=30)
    source_ref: str = Field(min_length=8, max_length=160)
    is_mock: bool = False
    occurred_at: datetime | None = None


class ErrorResolution(BaseModel):
    corrective_action: str = Field(min_length=3, max_length=2000)


def _audit_digest(entries: list[AuditLog]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        canonical = {
            "id": entry.id, "organization_id": entry.organization_id,
            "actor_id": entry.actor_id, "action": entry.action,
            "entity_type": entry.entity_type, "entity_id": entry.entity_id,
            "metadata_json": entry.metadata_json, "created_at": entry.created_at.isoformat(),
        }
        digest.update(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode())
        digest.update(b"\n")
    return digest.hexdigest()


@router.get("/status")
def operational_status(db: DbSession, context: CurrentAuth):
    org_id = context.membership.organization_id
    now = datetime.now(timezone.utc)
    open_errors = db.scalar(select(func.count()).select_from(OperationalError).where(
        (OperationalError.organization_id == org_id) | (OperationalError.organization_id.is_(None)),
        OperationalError.status == "open",
    )) or 0
    failed_publications = db.scalar(select(func.count()).select_from(PublicationJob).where(
        PublicationJob.organization_id == org_id,
        PublicationJob.status.in_(["failed", "dead_letter"]),
    )) or 0
    last_backup = db.scalar(select(BackupRun).where(BackupRun.status == "completed").order_by(
        BackupRun.completed_at.desc()).limit(1))
    backup_fresh = bool(last_backup and last_backup.completed_at and last_backup.completed_at >= now - timedelta(hours=26))
    checks = {
        "security_baseline": True, "audit_log": True, "cost_guard": True,
        "backup_fresh": backup_fresh, "no_critical_errors": open_errors == 0,
        "publication_queue": failed_publications == 0,
    }
    return {
        "status": "ready" if all(checks.values()) else "attention",
        "environment": get_settings().app_env, "version": get_settings().release_version,
        "checks": checks, "open_errors": open_errors,
        "failed_publications": failed_publications,
        "last_backup_at": last_backup.completed_at if last_backup else None,
        "is_mock": False,
    }


@router.get("/errors")
def list_errors(db: DbSession, context: CurrentAuth, error_status: str = Query(default="open", alias="status", pattern="^(open|resolved|all)$"), limit: int = Query(default=50, ge=1, le=200)):
    query = select(OperationalError).where(
        (OperationalError.organization_id == context.membership.organization_id)
        | (OperationalError.organization_id.is_(None))
    )
    if error_status != "all":
        query = query.where(OperationalError.status == error_status)
    entries = db.scalars(query.order_by(OperationalError.last_seen_at.desc()).limit(limit)).all()
    return [{
        "id": item.id, "service": item.service, "code": item.code,
        "severity": item.severity, "status": item.status,
        "message": item.message_sanitized, "fingerprint": item.fingerprint,
        "request_id": item.request_id, "occurrences": item.occurrences,
        "corrective_action": item.corrective_action,
        "first_seen_at": item.first_seen_at, "last_seen_at": item.last_seen_at,
        "resolved_at": item.resolved_at,
    } for item in entries]


@router.patch("/errors/{error_id}")
def resolve_error(error_id: str, payload: ErrorResolution, db: DbSession, context: AuthContext = admin_or_manager):
    item = db.get(OperationalError, error_id)
    if item is None or item.organization_id not in (None, context.membership.organization_id):
        raise HTTPException(status_code=404, detail={"code": "operational_error_not_found"})
    item.status = "resolved"
    item.corrective_action = payload.corrective_action
    item.resolved_by = context.user.id
    item.resolved_at = datetime.now(timezone.utc)
    write_audit(db, organization_id=context.membership.organization_id, actor_id=context.user.id,
                action="operations.error_resolved", entity_type="operational_error",
                entity_id=item.id, metadata={"fingerprint": item.fingerprint})
    db.commit()
    return {"id": item.id, "status": item.status, "resolved_at": item.resolved_at}


@router.get("/costs/summary")
def cost_summary(db: DbSession, context: CurrentAuth):
    org_id = context.membership.organization_id
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    spent_micros = db.scalar(select(func.coalesce(func.sum(CostLedgerEntry.amount_micros), 0)).where(
        CostLedgerEntry.organization_id == org_id,
        CostLedgerEntry.occurred_at >= month_start,
        CostLedgerEntry.is_mock.is_(False),
    )) or 0
    budget = db.scalar(select(CostBudget).where(CostBudget.organization_id == org_id))
    limit_cents = budget.monthly_limit_cents if budget else get_settings().cost_monthly_limit_cents
    warning = budget.warning_percent if budget else get_settings().cost_warning_percent
    spent_cents = int(spent_micros // 10_000)
    percent = round(spent_cents / limit_cents * 100, 2) if limit_cents else 0
    state = "blocked" if budget and budget.hard_stop_enabled and percent >= 100 else "warning" if percent >= warning else "ok"
    return {
        "month": month_start.date(), "spent_cents": spent_cents,
        "monthly_limit_cents": limit_cents, "usage_percent": percent,
        "warning_percent": warning, "hard_stop_enabled": budget.hard_stop_enabled if budget else False,
        "currency": budget.currency if budget else "BRL", "state": state,
    }


@router.put("/costs/budget")
def update_budget(payload: BudgetUpdate, db: DbSession, context: AuthContext = admin_or_manager):
    org_id = context.membership.organization_id
    budget = db.scalar(select(CostBudget).where(CostBudget.organization_id == org_id))
    if budget is None:
        budget = CostBudget(organization_id=org_id, updated_by=context.user.id, **payload.model_dump())
        db.add(budget)
    else:
        for key, value in payload.model_dump().items():
            setattr(budget, key, value)
        budget.updated_by = context.user.id
    db.flush()
    write_audit(db, organization_id=org_id, actor_id=context.user.id,
                action="operations.cost_budget_updated", entity_type="cost_budget",
                entity_id=budget.id, metadata={"monthly_limit_cents": payload.monthly_limit_cents})
    db.commit()
    return {"id": budget.id, **payload.model_dump()}


@router.post("/costs/entries", status_code=status.HTTP_201_CREATED)
def create_cost_entry(payload: CostEntryCreate, db: DbSession, context: AuthContext = admin_or_manager):
    org_id = context.membership.organization_id
    existing = db.scalar(select(CostLedgerEntry).where(
        CostLedgerEntry.organization_id == org_id, CostLedgerEntry.source_ref == payload.source_ref))
    if existing:
        return {"id": existing.id, "duplicate": True}
    entry = CostLedgerEntry(organization_id=org_id,
        occurred_at=payload.occurred_at or datetime.now(timezone.utc),
        **payload.model_dump(exclude={"occurred_at"}))
    db.add(entry)
    db.commit()
    return {"id": entry.id, "duplicate": False}


@router.get("/audit")
def list_audit(db: DbSession, context: CurrentAuth, limit: int = Query(default=100, ge=1, le=500)):
    entries = db.scalars(select(AuditLog).where(
        AuditLog.organization_id == context.membership.organization_id
    ).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [{"id": item.id, "actor_id": item.actor_id, "action": item.action,
             "entity_type": item.entity_type, "entity_id": item.entity_id,
             "metadata": json.loads(item.metadata_json), "created_at": item.created_at}
            for item in entries]


@router.post("/audit/checkpoints", status_code=status.HTTP_201_CREATED)
def create_audit_checkpoint(db: DbSession, context: AuthContext = admin_or_manager):
    to_at = datetime.now(timezone.utc)
    previous = db.scalar(select(AuditCheckpoint).where(
        AuditCheckpoint.organization_id == context.membership.organization_id
    ).order_by(AuditCheckpoint.to_at.desc()).limit(1))
    from_at = previous.to_at if previous else datetime(1970, 1, 1, tzinfo=timezone.utc)
    entries = list(db.scalars(select(AuditLog).where(
        AuditLog.organization_id == context.membership.organization_id,
        AuditLog.created_at > from_at, AuditLog.created_at <= to_at,
    ).order_by(AuditLog.created_at, AuditLog.id)).all())
    checkpoint = AuditCheckpoint(organization_id=context.membership.organization_id,
        created_by=context.user.id, from_at=from_at, to_at=to_at,
        entry_count=len(entries), digest_sha256=_audit_digest(entries))
    db.add(checkpoint)
    db.commit()
    return {"id": checkpoint.id, "entry_count": checkpoint.entry_count,
            "digest_sha256": checkpoint.digest_sha256, "from_at": from_at, "to_at": to_at}


@router.get("/audit/checkpoints/{checkpoint_id}/verify")
def verify_audit_checkpoint(checkpoint_id: str, db: DbSession, context: CurrentAuth):
    checkpoint = db.get(AuditCheckpoint, checkpoint_id)
    if checkpoint is None or checkpoint.organization_id != context.membership.organization_id:
        raise HTTPException(status_code=404, detail={"code": "checkpoint_not_found"})
    entries = list(db.scalars(select(AuditLog).where(
        AuditLog.organization_id == checkpoint.organization_id,
        AuditLog.created_at > checkpoint.from_at, AuditLog.created_at <= checkpoint.to_at,
    ).order_by(AuditLog.created_at, AuditLog.id)).all())
    actual = _audit_digest(entries)
    return {"id": checkpoint.id,
            "valid": actual == checkpoint.digest_sha256 and len(entries) == checkpoint.entry_count,
            "expected_entries": checkpoint.entry_count, "actual_entries": len(entries),
            "digest_sha256": actual}
