from dataclasses import dataclass
from typing import List, Optional, Union, Protocol

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
