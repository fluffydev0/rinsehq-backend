from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from rinsehq.infrastructure.db.models import IdSequenceModel


def next_prefixed_id(session: Session, prefix: str, width: int = 3) -> str:
    row = session.scalar(
        select(IdSequenceModel).where(IdSequenceModel.prefix == prefix).with_for_update()
    )
    if not row:
        row = IdSequenceModel(prefix=prefix, last_value=0)
        session.add(row)
        session.flush()
    row.last_value += 1
    session.flush()
    return f"{prefix}{row.last_value:0{width}d}"
