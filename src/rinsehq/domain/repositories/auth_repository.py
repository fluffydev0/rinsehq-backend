from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from rinsehq.domain.entities.user import User, UserCredentials


@dataclass(frozen=True)
class CreateUserInput:
    email: str
    password: str
    name: Optional[str] = None


class AuthRepository(Protocol):
    async def find_by_email(self, email: str) -> Optional[User]: ...

    async def find_by_id(self, user_id: str) -> Optional[User]: ...

    async def create(self, input: CreateUserInput) -> User: ...

    async def validate_credentials(self, credentials: UserCredentials) -> Optional[User]: ...

    async def update_password(self, user_id: str, password_hash: str) -> None: ...

    async def set_email_verified(self, user_id: str) -> None: ...

    async def set_onboarding_completed(self, user_id: str) -> None: ...

    async def update_personal(self, user_id: str, name: str, phone: str) -> User: ...

    async def create_verification_code(self, email: str, code: str, expires_at: object) -> None: ...

    async def get_verification_code(self, email: str) -> Optional[tuple[str, object]]: ...

    async def delete_verification_code(self, email: str) -> None: ...
