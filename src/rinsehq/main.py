from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from rinsehq.config import get_settings
from rinsehq.infrastructure.db.session import init_db
from rinsehq.presentation.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    init_db()
    if settings.seed_demo_data:
        from rinsehq.infrastructure.seed import seed_demo_data

        await seed_demo_data()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="RinseHQ API",
        description="Laundry service management backend",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException):
        if isinstance(exc.detail, dict) and "success" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": str(exc.detail)},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_v1_router, prefix="/v1")
    return app


app = create_app()
