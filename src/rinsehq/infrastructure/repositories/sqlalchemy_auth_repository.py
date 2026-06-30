from typing import List, Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session

from rinsehq.domain.entities.user import User, UserCredentials
from rinsehq.domain.repositories.auth_repository import AuthRepository, CreateUserInput
from rinsehq.infrastructure.db.models import UserModel
from rinsehq.infrastructure.security.passwords import hash_password, verify_password


class SqlAlchemyAuthRepository(AuthRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    async def find_by_email(self, email: str) -> Optional[User]:
        stmt = select(UserModel).where(UserModel.email == email.lower())
        row = self._session.scalar(stmt)
        return self._to_entity(row) if row else None

    async def find_by_id(self, user_id: str) -> Optional[User]:
        row = self._session.get(UserModel, user_id)
        return self._to_entity(row) if row else None

    async def create(self, input: CreateUserInput) -> User:
        email = input.email.lower()
        name = input.name or email.split("@")[0]
        row = UserModel(
            email=email,
            name=name,
            password_hash=hash_password(input.password),
        )
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    async def validate_credentials(self, credentials: UserCredentials) -> Optional[User]:
        row = self._session.scalar(
            select(UserModel).where(UserModel.email == credentials.email.lower())
        )
        if not row:
            return None
        if not verify_password(credentials.password, row.password_hash):
            return None
        return self._to_entity(row)

    @staticmethod
    def _to_entity(row: UserModel) -> User:
        return User(
            id=row.id,
            email=row.email,
            name=row.name,
            created_at=row.created_at,
        )
