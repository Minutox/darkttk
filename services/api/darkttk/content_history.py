import json

from sqlalchemy.orm import Session

from .models import ContentEvent


def record_content_event(
    db: Session,
    *,
    organization_id: str,
    actor_id: str | None,
    subject_type: str,
    subject_id: str,
    event_type: str,
    payload: dict[str, object] | None = None,
) -> None:
    db.add(
        ContentEvent(
            organization_id=organization_id,
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            event_type=event_type,
            payload_json=json.dumps(payload or {}, ensure_ascii=False, separators=(",", ":")),
        )
    )
