from typing import Annotated

from fastapi import APIRouter, Depends

from rinsehq.application.use_cases.dashboard_summary import DashboardSummaryUseCase
from rinsehq.infrastructure.di import CurrentUser, get_dashboard_summary_use_case
from rinsehq.presentation.schemas.order import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    _current_user: CurrentUser,
    use_case: Annotated[DashboardSummaryUseCase, Depends(get_dashboard_summary_use_case)],
) -> DashboardSummaryResponse:
    summary = await use_case.execute()
    return DashboardSummaryResponse(
        active=summary.active,
        pending=summary.pending,
        completed=summary.completed,
    )
