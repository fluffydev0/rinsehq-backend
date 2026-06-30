from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from rinsehq.application.dtos.auth import SignInInput, SignUpInput
from rinsehq.application.dtos.common import ErrorResult
from rinsehq.application.use_cases.sign_in import SignInUseCase
from rinsehq.application.use_cases.sign_up import SignUpUseCase
from rinsehq.infrastructure.di import CurrentUser, get_sign_in_use_case, get_sign_up_use_case
from rinsehq.infrastructure.security.jwt import create_access_token
from rinsehq.presentation.schemas.auth import SignInRequest, SignUpRequest, TokenResponse, UserResponse
from rinsehq.presentation.schemas.mappers import user_to_response

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(
    body: SignUpRequest,
    use_case: Annotated[SignUpUseCase, Depends(get_sign_up_use_case)],
) -> UserResponse:
    result = await use_case.execute(
        SignUpInput(email=body.email, password=body.password, name=body.name)
    )
    if isinstance(result, ErrorResult):
        status_code = (
            status.HTTP_409_CONFLICT
            if "already exists" in result.error
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=result.error)
    return user_to_response(result.data)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: SignInRequest,
    use_case: Annotated[SignInUseCase, Depends(get_sign_in_use_case)],
) -> TokenResponse:
    result = await use_case.execute(SignInInput(email=body.email, password=body.password))
    if isinstance(result, ErrorResult):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error,
        )
    token = create_access_token(result.data.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return user_to_response(current_user)
