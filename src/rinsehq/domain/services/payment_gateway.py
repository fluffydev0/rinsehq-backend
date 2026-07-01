from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class GatewayCheckoutResult:
    authorization_url: str
    reference: str


class PaymentGateway(Protocol):
    async def create_checkout(
        self,
        *,
        amount_kobo: int,
        customer_email: str,
        callback_url: str,
        order_reference: Optional[str] = None,
    ) -> GatewayCheckoutResult:
        ...

    @staticmethod
    def verify_webhook(
        raw_body: bytes,
        signature_header: str,
        secret: str,
    ) -> bool:
        ...
