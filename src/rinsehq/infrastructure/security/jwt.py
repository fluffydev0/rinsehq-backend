from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from rinsehq.config import get_settings
from rinsehq.infrastructure.auth.permissions import PermissionLevel


def create_access_token(
    user_id: str,
    store_id: str | None = None,
    permission_level: PermissionLevel | None = None,
) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict = {"sub": user_id, "exp": expire}
    if store_id:
        payload["store_id"] = store_id
    if permission_level:
        payload["permission"] = permission_level
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> Optional[dict]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if not isinstance(sub, str):
        return None
    return {
        "user_id": sub,
        "store_id": payload.get("store_id"),
        "permission": payload.get("permission"),
    }
