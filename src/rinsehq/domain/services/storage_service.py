from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class UploadResult:
    public_id: str
    secure_url: str


class StorageService(Protocol):
    async def upload_file(
        self, file_bytes: bytes, filename: str, resource_type: str = "image"
    ) -> UploadResult: ...
