from __future__ import annotations

from typing import Protocol

from ivd.models import Invoice


class InvoiceSource(Protocol):
    async def fetch(self) -> list[Invoice]:
        """Return normalized invoices from this source."""
        ...
