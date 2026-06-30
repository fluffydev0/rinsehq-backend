from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, EmailStr, Field

from rinsehq.application.dtos.auth import SignInInput, SignUpInput
from rinsehq.application.dtos.common import ErrorResult
from rinsehq.application.use_cases.auth_flows import (
    ChangePasswordUseCase,
    ResendVerificationUseCase,
    SelectStoreUseCase,
    SignInUseCase,
    SignUpUseCase,
    VerifyEmailUseCase,
)
from rinsehq.config import get_settings
from rinsehq.infrastructure.di import (
    CurrentSession,
    CurrentUser,
    get_auth_repository,
    get_store_repository,
)
from rinsehq.infrastructure.email.smtp_client import NoOpEmailService, SmtpEmailService
from rinsehq.infrastructure.repositories.sqlalchemy_auth_repository import SqlAlchemyAuthRepository
from rinsehq.infrastructure.repositories.sqlalchemy_store_repository import SqlAlchemyStoreRepository
from rinsehq.infrastructure.security.jwt import create_access_token
from rinsehq.presentation.helpers import unwrap_result
from rinsehq.presentation.schemas.envelope import ApiResponse
from rinsehq.presentation.schemas.mappers import (
    auth_user_to_response,
    store_access_to_response,
    user_to_response,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class SelectStoreRequest(BaseModel):
    storeId: str

    model_config = {"populate_by_name": True}


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendRequest(BaseModel):
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str = Field(min_length=8)


def _email_service():
    settings = get_settings()
    if settings.smtp_user and settings.smtp_password_clean:
        return SmtpEmailService()
    return NoOpEmailService()


def get_sign_up_use_case(
    auth_repo: Annotated[SqlAlchemyAuthRepository, Depends(get_auth_repository)],
    store_repo: Annotated[SqlAlchemyStoreRepository, Depends(get_store_repository)],
) -> SignUpUseCase:
    return SignUpUseCase(auth_repo, store_repo, _email_service())


def get_sign_in_use_case(
    auth_repo: Annotated[SqlAlchemyAuthRepository, Depends(get_auth_repository)],
    store_repo: Annotated[SqlAlchemyStoreRepository, Depends(get_store_repository)],
) -> SignInUseCase:
    return SignInUseCase(auth_repo, store_repo)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def sign_up(
    body: SignUpRequest,
    use_case: Annotated[SignUpUseCase, Depends(get_sign_up_use_case)],
) -> ApiResponse[dict]:
    result = await use_case.execute(SignUpInput(email=body.email, password=body.password))
    user = unwrap_result(result)
    return ApiResponse(data={"user": user_to_response(user)})


@router.post("/login")
async def login(
    body: SignInRequest,
    use_case: Annotated[SignInUseCase, Depends(get_sign_in_use_case)],
) -> ApiResponse[dict]:
    result = await use_case.execute(SignInInput(email=body.email, password=body.password))
    if isinstance(result, ErrorResult):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error": result.error},
        )
    user, stores = result.data
    data: dict[str, Any] = {
        "user": user_to_response(user),
        "accessibleStores": [store_access_to_response(s) for s in stores],
    }
    if len(stores) == 1:
        token = create_access_token(
            user.id, stores[0].store_id, stores[0].permission_level
        )
        data["accessToken"] = token
    return ApiResponse(data=data)


@router.post("/select-store")
async def select_store(
    body: SelectStoreRequest,
    user: CurrentUser,
    store_repo: Annotated[SqlAlchemyStoreRepository, Depends(get_store_repository)],
) -> ApiResponse[dict]:
    use_case = SelectStoreUseCase(store_repo)
    result = await use_case.execute(user.id, body.storeId)
    access = unwrap_result(result)
    token = create_access_token(user.id, access.store_id, access.permission_level)
    from rinsehq.domain.entities.user import AuthUser

    session_user = AuthUser(
        id=user.id,
        email=user.email,
        name=user.name,
        store_id=access.store_id,
        store_name=access.store_name,
        store_role=access.role,
        permission_level=access.permission_level,
    )
    return ApiResponse(
        data={
            "accessToken": token,
            "session": {"user": auth_user_to_response(session_user)},
        }
    )


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    auth_repo: Annotated[SqlAlchemyAuthRepository, Depends(get_auth_repository)],
) -> ApiResponse[dict]:
    use_case = VerifyEmailUseCase(auth_repo)
    result = await use_case.execute(body.email, body.code)
    user = unwrap_result(result)
    return ApiResponse(data={"user": user_to_response(user)})


@router.post("/resend-verification")
async def resend_verification(
    body: ResendRequest,
    auth_repo: Annotated[SqlAlchemyAuthRepository, Depends(get_auth_repository)],
) -> ApiResponse[None]:
    use_case = ResendVerificationUseCase(auth_repo, _email_service())
    unwrap_result(await use_case.execute(body.email))
    return ApiResponse(data=None)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: CurrentUser,
    auth_repo: Annotated[SqlAlchemyAuthRepository, Depends(get_auth_repository)],
) -> ApiResponse[None]:
    use_case = ChangePasswordUseCase(auth_repo)
    unwrap_result(await use_case.execute(user.id, body.currentPassword, body.newPassword))
    return ApiResponse(data=None)


@router.get("/me")
async def me(session: CurrentSession) -> ApiResponse[dict]:
    return ApiResponse(data={"user": auth_user_to_response(session.to_auth_user())})
