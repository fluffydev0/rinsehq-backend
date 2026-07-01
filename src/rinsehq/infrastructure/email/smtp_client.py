from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from rinsehq.config import get_settings

logger = logging.getLogger(__name__)


class SmtpEmailService:
    async def send_verification_otp(self, email: str, code: str) -> None:
        subject = "Verify your RinseHQ email"
        body = (
            f"Your RinseHQ verification code is: {code}\n\n"
            "This code expires in 15 minutes."
        )
        await self._send(email, subject, body)

    async def send_admin_invitation(self, email: str, name: str, invite_link: str) -> None:
        subject = "You've been invited to RinseHQ"
        body = (
            f"Hi {name},\n\n"
            f"You have been invited to join a RinseHQ store. "
            f"Sign in or create an account at: {invite_link}"
        )
        await self._send(email, subject, body)

    async def send_password_reset_otp(self, email: str, code: str) -> None:
        subject = "Reset your RinseHQ password"
        body = (
            f"Your RinseHQ password reset code is: {code}\n\n"
            "This code expires in 15 minutes."
        )
        await self._send(email, subject, body)

    async def _send(self, to: str, subject: str, body: str) -> None:
        settings = get_settings()
        if not settings.smtp_user or not settings.smtp_password_clean:
            logger.warning("SMTP not configured; skipping email to %s", to)
            return

        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from_address
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password_clean)
                server.sendmail(settings.smtp_from_address, to, msg.as_string())
        except Exception:
            logger.exception("Failed to send email to %s", to)


class NoOpEmailService:
    async def send_verification_otp(self, email: str, code: str) -> None:
        logger.info("NoOp email OTP to %s: %s", email, code)

    async def send_admin_invitation(self, email: str, name: str, invite_link: str) -> None:
        logger.info("NoOp admin invite to %s", email)

    async def send_password_reset_otp(self, email: str, code: str) -> None:
        logger.info("NoOp password reset OTP to %s: %s", email, code)
