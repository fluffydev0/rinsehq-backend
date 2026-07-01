from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

from rinsehq.config import get_settings


@dataclass
class _TokenCache:
    access_token: str = ""
    expires_at: float = 0.0


@dataclass
class CheckoutResult:
    checkout_url: str
    order_reference: str


@dataclass
class VirtualAccountResult:
    account_number: str
    bank_name: str
    account_name: str
    account_ref: str


class NombaError(Exception):
    """Base exception for all Nomba client errors."""


class NombaAuthError(NombaError):
    """Token issue or refresh failed."""


class NombaCheckoutError(NombaError):
    """Checkout order creation failed."""


class NombaVirtualAccountError(NombaError):
    """Virtual account creation failed."""


class NombaClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._cache = _TokenCache()
        self._http = httpx.AsyncClient(
            base_url=self._settings.nomba_base_url,
            timeout=30.0,
        )

    async def _get_token(self) -> str:
        if self._cache.access_token and time.time() < self._cache.expires_at - 300:
            return self._cache.access_token

        resp = await self._http.post(
            "/auth/token/issue",
            headers={
                "Content-Type": "application/json",
                "accountId": self._settings.nomba_account_id,
            },
            json={
                "grant_type": "client_credentials",
                "client_id": self._settings.nomba_client_id,
                "client_secret": self._settings.nomba_client_secret,
            },
        )

        if resp.status_code != 200:
            raise NombaAuthError(
                f"Nomba token issue failed: {resp.status_code} — {resp.text}"
            )

        body = resp.json()
        token_data = body.get("data", {})
        self._cache.access_token = token_data["access_token"]

        expires_at = token_data.get("expiresAt")
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            self._cache.expires_at = expires_dt.timestamp()
        else:
            self._cache.expires_at = time.time() + token_data.get("expires_in", 3600)

        return self._cache.access_token

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "accountId": self._settings.nomba_account_id,
            "Content-Type": "application/json",
        }

    async def create_checkout(
        self,
        *,
        amount_kobo: int,
        customer_email: str,
        callback_url: str,
        order_reference: Optional[str] = None,
    ) -> CheckoutResult:
        token = await self._get_token()
        ref = order_reference or f"rinse_{uuid.uuid4().hex[:20]}"

        resp = await self._http.post(
            "/checkout/order",
            headers=self._headers(token),
            json={
                "order": {
                    "orderReference": ref,
                    "amount": amount_kobo,
                    "currency": "NGN",
                    "callbackUrl": callback_url,
                    "customerEmail": customer_email,
                }
            },
        )

        if resp.status_code not in (200, 201):
            raise NombaCheckoutError(
                f"Nomba checkout failed: {resp.status_code} — {resp.text}"
            )

        data = resp.json().get("data", {})
        checkout_url = data.get("checkoutUrl") or data.get("checkoutLink", "")
        return CheckoutResult(checkout_url=checkout_url, order_reference=ref)

    async def create_virtual_account(
        self,
        *,
        account_ref: str,
        account_name: str,
        expected_amount_kobo: Optional[int] = None,
    ) -> VirtualAccountResult:
        token = await self._get_token()
        payload: dict[str, object] = {
            "accountRef": account_ref,
            "accountName": account_name,
        }
        if expected_amount_kobo is not None:
            payload["amount"] = expected_amount_kobo

        resp = await self._http.post(
            "/accounts/virtual",
            headers=self._headers(token),
            json=payload,
        )

        if resp.status_code not in (200, 201):
            raise NombaVirtualAccountError(
                f"Nomba virtual account creation failed: {resp.status_code} — {resp.text}"
            )

        data = resp.json().get("data", {})
        return VirtualAccountResult(
            account_number=data.get("accountNumber", ""),
            bank_name=data.get("bankName", ""),
            account_name=data.get("accountName", account_name),
            account_ref=account_ref,
        )

    @staticmethod
    def verify_webhook(
        raw_body: bytes,
        signature_header: str,
        webhook_secret: str,
    ) -> bool:
        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header)

    async def close(self) -> None:
        await self._http.aclose()
