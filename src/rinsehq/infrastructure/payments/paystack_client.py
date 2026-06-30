from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from rinsehq.config import get_settings

logger = logging.getLogger(__name__)

PAYSTACK_BASE = "https://api.paystack.co"


@dataclass(frozen=True)
class PaystackInitResult:
    authorization_url: str
    reference: str


class PaystackClient:
    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def configured(self) -> bool:
        return self._settings.paystack_configured

    async def initialize_transaction(
        self,
        email: str,
        amount_kobo: int,
        reference: str,
        callback_url: str,
    ) -> PaystackInitResult:
        if not self.configured:
            return PaystackInitResult(
                authorization_url=f"{callback_url}?reference={reference}&demo=1",
                reference=reference,
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PAYSTACK_BASE}/transaction/initialize",
                headers={"Authorization": f"Bearer {self._settings.paystack_secret_key}"},
                json={
                    "email": email,
                    "amount": amount_kobo,
                    "reference": reference,
                    "callback_url": callback_url,
                },
            )
            response.raise_for_status()
            data = response.json()["data"]
            return PaystackInitResult(
                authorization_url=data["authorization_url"],
                reference=data["reference"],
            )

    def verify_webhook_signature(self, payload: bytes, signature: str | None) -> bool:
        if not self.configured or not signature:
            return not self.configured
        secret = self._settings.paystack_secret_key.encode()
        digest = hmac.new(secret, payload, hashlib.sha512).hexdigest()
        return hmac.compare_digest(digest, signature)

    async def refund_transaction(self, reference: str, reason: str) -> dict[str, Any]:
        if not self.configured:
            return {"status": "demo_refund", "reference": reference}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PAYSTACK_BASE}/refund",
                headers={"Authorization": f"Bearer {self._settings.paystack_secret_key}"},
                json={"transaction": reference, "customer_note": reason},
            )
            response.raise_for_status()
            return response.json()["data"]
