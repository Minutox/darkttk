import json

from sqlalchemy.orm import Session

from .models import AuditLog


def write_audit(
    db: Session,
    *,
    organization_id: str,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: dict[str, object] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    db.add(
        AuditLog(
            organization_id=organization_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False, separators=(",", ":")),
            ip_address=ip_address,
            user_agent=(user_agent or "")[:255] or None,
        )
    )
