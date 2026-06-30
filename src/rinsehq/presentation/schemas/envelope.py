from __future__ import annotations

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total: int
    page: int
    limit: int


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: Optional[PaginationMeta] = None
