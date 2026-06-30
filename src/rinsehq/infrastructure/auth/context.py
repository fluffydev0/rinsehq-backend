from __future__ import annotations

from dataclasses import dataclass

from rinsehq.domain.entities.user import AuthUser, User
from rinsehq.infrastructure.auth.permissions import PermissionLevel


@dataclass(frozen=True)
class SessionContext:
    user: User
    store_id: str
    store_name: str
    store_role: str
    permission_level: PermissionLevel
    custom_permissions: dict[str, bool] | None = None

    def to_auth_user(self) -> AuthUser:
        return AuthUser(
            id=self.user.id,
            email=self.user.email,
            name=self.user.name,
            store_id=self.store_id,
            store_name=self.store_name,
            store_role=self.store_role,  # type: ignore[arg-type]
            permission_level=self.permission_level,
        )
