from datetime import datetime
from ..models import db, StatusHistory


def add_history(
    entity_type: str,
    entity_id: int,
    old_status: str | None,
    new_status: str,
    operator: str,
    reason: str | None = None
) -> None:
    existing = StatusHistory.query.filter_by(
        entity_type=entity_type,
        entity_id=entity_id,
        old_status=old_status,
        new_status=new_status,
        operator=operator
    ).order_by(StatusHistory.created_at.desc()).first()

    if existing and (datetime.utcnow() - existing.created_at).total_seconds() < 1:
        return

    history = StatusHistory(
        entity_type=entity_type,
        entity_id=entity_id,
        old_status=old_status,
        new_status=new_status,
        operator=operator,
        reason=reason
    )
    db.session.add(history)
