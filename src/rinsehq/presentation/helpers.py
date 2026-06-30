from __future__ import annotations

from fastapi import HTTPException, status

from rinsehq.application.dtos.common import ErrorResult, Result


def unwrap_result(result: Result, not_found: bool = False) -> object:
    if isinstance(result, ErrorResult):
        code = status.HTTP_404_NOT_FOUND if not_found else status.HTTP_400_BAD_REQUEST
        if "already exists" in result.error or "already verified" in result.error:
            code = status.HTTP_409_CONFLICT
        elif "Invalid email or password" in result.error or "not authenticated" in result.error.lower():
            code = status.HTTP_401_UNAUTHORIZED
        elif "not found" in result.error.lower() or "access" in result.error.lower():
            code = status.HTTP_404_NOT_FOUND if "not found" in result.error.lower() else status.HTTP_403_FORBIDDEN
        raise HTTPException(
            status_code=code,
            detail={"success": False, "error": result.error},
        )
    return result.data
