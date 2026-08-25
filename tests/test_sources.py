from __future__ import annotations

import httpx
import respx

from ivd.sources.jsonfile import JsonFileSource
from ivd.sources.zwapgrid import ZwapgridSource


async def test_jsonfile_source_returns_two_fixture_invoices():
    invoices = await JsonFileSource().fetch()
    assert {inv.id for inv in invoices} == {"INV-001", "INV-002"}


async def test_zwapgrid_source_normalizes_response():
    with respx.mock:
        respx.get("https://zwapgrid.example/invoices/incoming").mock(
            return_value=httpx.Response(
                200,
                json={
                    "invoices": [
                        {
                            "id": "ZW-1",
                            "issuerName": "Zwap Issuer",
                            "issuerOrgNo": "5560123456",
                            "amountMinor": 5000,
                            "currency": "SEK",
                            "ocrReference": "1234567890136",
                            "dueDate": "2026-09-15",
                            "issuerWalletAddress": None,
                        }
                    ]
                },
            )
        )
        source = ZwapgridSource(base_url="https://zwapgrid.example", api_key="key-1")
        invoices = await source.fetch()

    assert len(invoices) == 1
    assert invoices[0].id == "ZW-1"
    assert invoices[0].issuer_org_no == "5560123456"
