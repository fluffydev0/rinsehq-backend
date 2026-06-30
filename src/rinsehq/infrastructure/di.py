from typing import List, Optional, Union, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from rinsehq.application.use_cases.create_order import CreateOrderUseCase
from rinsehq.application.use_cases.dashboard_summary import DashboardSummaryUseCase
from rinsehq.application.use_cases.get_order import GetOrderUseCase
from rinsehq.application.use_cases.list_orders import ListOrdersUseCase
from rinsehq.application.use_cases.sign_in import SignInUseCase
from rinsehq.application.use_cases.sign_up import SignUpUseCase
from rinsehq.application.use_cases.update_order import UpdateOrderUseCase
from rinsehq.domain.entities.user import User
from rinsehq.infrastructure.db.session import get_db_session
from rinsehq.infrastructure.repositories.sqlalchemy_auth_repository import SqlAlchemyAuthRepository
from rinsehq.infrastructure.repositories.sqlalchemy_order_repository import (
    SqlAlchemyOrderRepository,
)
from rinsehq.infrastructure.security.jwt import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db_session)]


def get_auth_repository(session: DbSession) -> SqlAlchemyAuthRepository:
    return SqlAlchemyAuthRepository(session)


def get_order_repository(session: DbSession) -> SqlAlchemyOrderRepository:
    return SqlAlchemyOrderRepository(session)


def get_sign_up_use_case(
    auth_repo: Annotated[SqlAlchemyAuthRepository, Depends(get_auth_repository)],
) -> SignUpUseCase:
    return SignUpUseCase(auth_repo)


def get_sign_in_use_case(
    auth_repo: Annotated[SqlAlchemyAuthRepository, Depends(get_auth_repository)],
) -> SignInUseCase:
    return SignInUseCase(auth_repo)


def get_list_orders_use_case(
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
) -> ListOrdersUseCase:
    return ListOrdersUseCase(order_repo)


def get_create_order_use_case(
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
) -> CreateOrderUseCase:
    return CreateOrderUseCase(order_repo)


def get_get_order_use_case(
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
) -> GetOrderUseCase:
    return GetOrderUseCase(order_repo)


def get_update_order_use_case(
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
) -> UpdateOrderUseCase:
    return UpdateOrderUseCase(order_repo)


def get_dashboard_summary_use_case(
    order_repo: Annotated[SqlAlchemyOrderRepository, Depends(get_order_repository)],
) -> DashboardSummaryUseCase:
    return DashboardSummaryUseCase(order_repo)


async def get_current_user(
    session: DbSession,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    auth_repo = SqlAlchemyAuthRepository(session)
    user = await auth_repo.find_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
