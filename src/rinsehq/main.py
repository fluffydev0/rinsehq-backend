from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rinsehq.config import get_settings
from rinsehq.infrastructure.db.session import init_db
from rinsehq.infrastructure.seed import seed_demo_data
from rinsehq.presentation.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    init_db()
    if settings.seed_demo_data:
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_v1_router, prefix="/api/v1")
    return app


app = create_app()
