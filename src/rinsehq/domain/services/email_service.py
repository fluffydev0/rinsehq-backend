from __future__ import annotations

from typing import Protocol


class EmailService(Protocol):
    async def send_verification_otp(self, email: str, code: str) -> None: ...

    async def send_admin_invitation(self, email: str, name: str, invite_link: str) -> None: ...
