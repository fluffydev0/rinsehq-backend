from __future__ import annotations

import random
import string
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from rinsehq.domain.entities.user import User, UserCredentials
from rinsehq.domain.repositories.auth_repository import AuthRepository, CreateUserInput
from rinsehq.infrastructure.db.models import UserModel, VerificationCodeModel
from rinsehq.infrastructure.security.passwords import hash_password, verify_password


class SqlAlchemyAuthRepository(AuthRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    async def find_by_email(self, email: str) -> Optional[User]:
        row = self._session.scalar(select(UserModel).where(UserModel.email == email.lower()))
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
        if not row or not verify_password(credentials.password, row.password_hash):
            return None
        return self._to_entity(row)

    async def update_password(self, user_id: str, password_hash: str) -> None:
        row = self._session.get(UserModel, user_id)
        if row:
            row.password_hash = password_hash
            self._session.flush()

    async def set_email_verified(self, user_id: str) -> None:
        row = self._session.get(UserModel, user_id)
        if row:
            row.email_verified = True
            self._session.flush()

    async def set_onboarding_completed(self, user_id: str) -> None:
        row = self._session.get(UserModel, user_id)
        if row:
            row.onboarding_completed = True
            self._session.flush()

    async def update_personal(self, user_id: str, name: str, phone: str) -> User:
        row = self._session.get(UserModel, user_id)
        if not row:
            raise ValueError("User not found")
        row.name = name
        row.phone = phone
        self._session.flush()
        return self._to_entity(row)

    async def create_verification_code(self, email: str, code: str, expires_at: object) -> None:
        await self.delete_verification_code(email)
        self._session.add(
            VerificationCodeModel(email=email.lower(), code=code, expires_at=expires_at)  # type: ignore[arg-type]
        )
        self._session.flush()

    async def get_verification_code(self, email: str) -> Optional[tuple[str, object]]:
        row = self._session.scalar(
            select(VerificationCodeModel)
            .where(VerificationCodeModel.email == email.lower())
            .order_by(VerificationCodeModel.created_at.desc())
        )
        if not row:
            return None
        return row.code, row.expires_at

    async def delete_verification_code(self, email: str) -> None:
        self._session.execute(
            delete(VerificationCodeModel).where(VerificationCodeModel.email == email.lower())
        )
        self._session.flush()

    @staticmethod
    def generate_otp() -> str:
        return "".join(random.choices(string.digits, k=6))

    @staticmethod
    def _to_entity(row: UserModel) -> User:
        return User(
            id=row.id,
            email=row.email,
            name=row.name,
            created_at=row.created_at,
            email_verified=row.email_verified,
            phone=row.phone,
            onboarding_completed=row.onboarding_completed,
        )
