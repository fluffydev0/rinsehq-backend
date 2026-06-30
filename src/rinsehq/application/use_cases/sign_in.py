from __future__ import annotations

from rinsehq.application.dtos.auth import SignInInput, validate_sign_in
from rinsehq.application.dtos.common import ErrorResult, Result, SuccessResult
from rinsehq.domain.entities.user import User, UserCredentials
from rinsehq.domain.repositories.auth_repository import AuthRepository


class SignInUseCase:
    def __init__(self, auth_repository: AuthRepository) -> None:
        self._auth_repository = auth_repository

    async def execute(self, input: SignInInput) -> Result[User]:
        validated = validate_sign_in(input)
        if isinstance(validated, ErrorResult):
            return validated

        data = validated.data
        user = await self._auth_repository.validate_credentials(
            UserCredentials(email=data.email, password=data.password)
        )
        if not user:
            return ErrorResult("Invalid email or password")
        return SuccessResult(user)
