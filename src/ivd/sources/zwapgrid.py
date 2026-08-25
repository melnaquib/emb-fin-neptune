from __future__ import annotations

import httpx

from ivd.models import Invoice


class ZwapgridSource:
    """Fetches the top 10 incoming invoices from Zwapgrid's API. Network calls
    are never exercised in tests — always mocked with respx."""

    def __init__(self, base_url: str, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = client

    async def fetch(self) -> list[Invoice]:
        client = self._client or httpx.AsyncClient()
        owns_client = self._client is None
        try:
            response = await client.get(
                f"{self._base_url}/invoices/incoming",
                params={"limit": 10},
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            response.raise_for_status()
            payload = response.json()
            return [self._normalize(item) for item in payload["invoices"]]
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _normalize(item: dict) -> Invoice:
        return Invoice(
            id=item["id"],
            issuer_name=item["issuerName"],
            issuer_org_no=item["issuerOrgNo"],
            amount_minor=item["amountMinor"],
            currency=item["currency"],
            ocr_reference=item["ocrReference"],
            due_date=item["dueDate"],
            issuer_wallet_address=item.get("issuerWalletAddress"),
        )
