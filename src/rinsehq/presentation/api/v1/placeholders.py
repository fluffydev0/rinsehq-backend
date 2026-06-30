from __future__ import annotations

from fastapi import APIRouter

from rinsehq.presentation.schemas.envelope import ApiResponse

router = APIRouter(tags=["placeholders"])


@router.get("/notifications")
async def notifications() -> ApiResponse[list]:
    return ApiResponse(data=[])


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str) -> ApiResponse[None]:
    return ApiResponse(data=None)


@router.get("/tickets")
async def tickets() -> ApiResponse[list]:
    return ApiResponse(data=[])


@router.post("/tickets")
async def create_ticket() -> ApiResponse[None]:
    return ApiResponse(data=None)


@router.get("/help/articles")
async def help_articles() -> ApiResponse[list]:
    return ApiResponse(data=[])
