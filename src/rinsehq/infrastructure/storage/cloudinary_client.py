from __future__ import annotations

import asyncio
import logging
from io import BytesIO

import cloudinary
import cloudinary.uploader

from rinsehq.config import get_settings
from rinsehq.domain.services.storage_service import UploadResult

logger = logging.getLogger(__name__)


class CloudinaryStorageService:
    def __init__(self) -> None:
        settings = get_settings()
        if settings.cloudinary_configured:
            cloudinary.config(
                cloud_name=settings.cloudinary_cloud_name,
                api_key=settings.cloudinary_api_key,
                api_secret=settings.cloudinary_api_secret,
                secure=True,
            )

    async def upload_file(
        self, file_bytes: bytes, filename: str, resource_type: str = "image"
    ) -> UploadResult:
        settings = get_settings()
        if not settings.cloudinary_configured:
            raise RuntimeError("Cloudinary is not configured")

        folder = settings.cloudinary_folder
        public_id = filename.rsplit(".", 1)[0]

        def _upload():
            return cloudinary.uploader.upload(
                BytesIO(file_bytes),
                folder=folder,
                public_id=public_id,
                resource_type=resource_type,
                overwrite=True,
            )

        result = await asyncio.to_thread(_upload)
        return UploadResult(public_id=result["public_id"], secure_url=result["secure_url"])


class LocalStorageService:
    """Fallback for dev when Cloudinary is not configured."""

    async def upload_file(
        self, file_bytes: bytes, filename: str, resource_type: str = "image"
    ) -> UploadResult:
        logger.warning("Using local storage placeholder for %s", filename)
        return UploadResult(
            public_id=filename,
            secure_url=f"https://placeholder.local/{filename}",
        )
