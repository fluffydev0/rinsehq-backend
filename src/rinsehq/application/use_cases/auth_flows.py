from __future__ import annotations

from datetime import datetime, timedelta, timezone

from rinsehq.application.dtos.auth import SignInInput, SignUpInput, validate_sign_up
from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.domain.entities.user import StoreAccess, User
from rinsehq.domain.repositories.auth_repository import AuthRepository, CreateUserInput
from rinsehq.domain.repositories.store_repository import CreateStoreInput, StoreRepository
from rinsehq.domain.services.email_service import EmailService
from rinsehq.infrastructure.repositories.sqlalchemy_auth_repository import SqlAlchemyAuthRepository


class SignUpUseCase:
    def __init__(
        self,
        auth_repository: AuthRepository,
        store_repository: StoreRepository,
        email_service: EmailService,
    ) -> None:
        self._auth = auth_repository
        self._stores = store_repository
        self._email = email_service

    async def execute(self, input: SignUpInput) -> Result[User]:
        validated = validate_sign_up(input)
        if isinstance(validated, ErrorResult):
            return validated
        data = validated.data
        existing = await self._auth.find_by_email(data.email)
        if existing:
            return ErrorResult("An account with this email already exists")

        user = await self._auth.create(
            CreateUserInput(email=data.email, password=data.password, name=data.name)
        )
        await self._stores.create_store(
            CreateStoreInput(
                name=f"{user.name}'s Laundry",
                address="",
                city="",
                phone="",
                status="active",
                owner_user_id=user.id,
                is_main_store=True,
            )
        )
        code = SqlAlchemyAuthRepository.generate_otp()
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        await self._auth.create_verification_code(data.email, code, expires)
        await self._email.send_verification_otp(data.email, code)
        return SuccessResult(user)


class SignInUseCase:
    def __init__(
        self,
        auth_repository: AuthRepository,
        store_repository: StoreRepository,
    ) -> None:
        self._auth = auth_repository
        self._stores = store_repository

    async def execute(self, input: SignInInput) -> Result[tuple[User, list[StoreAccess]]]:
        from rinsehq.domain.entities.user import UserCredentials

        user = await self._auth.validate_credentials(
            UserCredentials(email=input.email, password=input.password)
        )
        if not user:
            return ErrorResult("Invalid email or password")
        stores = await self._stores.list_accessible_stores(user.id)
        if not stores:
            return ErrorResult("No stores are assigned to this account.")
        return SuccessResult((user, stores))


class VerifyEmailUseCase:
    def __init__(self, auth_repository: AuthRepository) -> None:
        self._auth = auth_repository

    async def execute(self, email: str, code: str) -> Result[User]:
        user = await self._auth.find_by_email(email)
        if not user:
            return ErrorResult("Account not found")
        if user.email_verified:
            return ErrorResult("Email is already verified")
        stored = await self._auth.get_verification_code(email)
        if not stored:
            return ErrorResult("No verification code found. Please resend.")
        stored_code, expires_at = stored
        now = datetime.now(timezone.utc)
        exp = expires_at
        if getattr(exp, "tzinfo", None) is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            return ErrorResult("Verification code has expired. Please resend.")
        if stored_code != code:
            return ErrorResult("Invalid verification code")
        await self._auth.set_email_verified(user.id)
        await self._auth.delete_verification_code(email)
        updated = await self._auth.find_by_id(user.id)
        return SuccessResult(updated)  # type: ignore[arg-type]


class ResendVerificationUseCase:
    def __init__(
        self, auth_repository: AuthRepository, email_service: EmailService
    ) -> None:
        self._auth = auth_repository
        self._email = email_service

    async def execute(self, email: str) -> Result[None]:
        user = await self._auth.find_by_email(email)
        if not user:
            return ErrorResult("Account not found")
        if user.email_verified:
            return ErrorResult("Email is already verified")
        code = SqlAlchemyAuthRepository.generate_otp()
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        await self._auth.create_verification_code(email, code, expires)
        await self._email.send_verification_otp(email, code)
        return SuccessResult(None)


class SelectStoreUseCase:
    def __init__(self, store_repository: StoreRepository) -> None:
        self._stores = store_repository

    async def execute(self, user_id: str, store_id: str) -> Result[StoreAccess]:
        assignment = await self._stores.get_assignment(user_id, store_id)
        if not assignment:
            return ErrorResult("You do not have access to this store.")
        stores = await self._stores.list_accessible_stores(user_id)
        match = next((s for s in stores if s.store_id == store_id), None)
        if not match:
            return ErrorResult("You do not have access to this store.")
        return SuccessResult(match)


class ChangePasswordUseCase:
    def __init__(self, auth_repository: AuthRepository) -> None:
        self._auth = auth_repository

    async def execute(self, user_id: str, current: str, new_password: str) -> Result[None]:
        from rinsehq.domain.entities.user import UserCredentials
        from rinsehq.infrastructure.security.passwords import hash_password, verify_password

        user = await self._auth.find_by_id(user_id)
        if not user:
            return ErrorResult("User not found")
        row_user = await self._auth.validate_credentials(
            UserCredentials(email=user.email, password=current)
        )
        if not row_user:
            return ErrorResult("Current password is incorrect.")
        await self._auth.update_password(user_id, hash_password(new_password))
        return SuccessResult(None)
