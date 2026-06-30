from __future__ import annotations

from rinsehq.application.dtos.auth import SignUpInput, validate_sign_up
from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.domain.entities.user import User
from rinsehq.domain.repositories.auth_repository import AuthRepository, CreateUserInput


class SignUpUseCase:
    def __init__(self, auth_repository: AuthRepository) -> None:
        self._auth_repository = auth_repository

    async def execute(self, input: SignUpInput) -> Result[User]:
        validated = validate_sign_up(input)
        if isinstance(validated, ErrorResult):
            return validated

        data = validated.data
        existing = await self._auth_repository.find_by_email(data.email)
        if existing:
            return ErrorResult("An account with this email already exists")

        user = await self._auth_repository.create(
            CreateUserInput(email=data.email, password=data.password, name=data.name)
        )
        return SuccessResult(user)
