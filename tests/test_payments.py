from __future__ import annotations

import httpx
import pytest
import respx

from ivd.payments import NoWalletAddressError, build_pay_link
from tests.conftest import make_invoice

ISSUER_WALLET_URL = "https://ilp.interledger-test.dev/nordic-supplies"
OUR_WALLET_URL = "https://ilp.interledger-test.dev/our-wallet"
ISSUER_AUTH_SERVER = "https://auth.interledger-test.dev/issuer"
ISSUER_RESOURCE_SERVER = "https://ilp.interledger-test.dev/issuer-rs"
OUR_AUTH_SERVER = "https://auth.interledger-test.dev/ours"
OUR_RESOURCE_SERVER = "https://ilp.interledger-test.dev/our-rs"


def _mock_wallet(url: str, wallet_id: str, auth_server: str, resource_server: str):
    return respx.get(url).mock(
        return_value=httpx.Response(
            200,
            json={"id": wallet_id, "authServer": auth_server, "resourceServer": resource_server, "assetCode": "SEK", "assetScale": 2},
        )
    )


async def test_build_pay_link_returns_redirect_uri():
    invoice = make_invoice(issuer_wallet_address=ISSUER_WALLET_URL, amount_minor=250000, currency="SEK")

    with respx.mock:
        _mock_wallet(ISSUER_WALLET_URL, ISSUER_WALLET_URL, ISSUER_AUTH_SERVER, ISSUER_RESOURCE_SERVER)
        _mock_wallet(OUR_WALLET_URL, OUR_WALLET_URL, OUR_AUTH_SERVER, OUR_RESOURCE_SERVER)

        respx.post(f"{OUR_AUTH_SERVER}/").mock(
            side_effect=[
                httpx.Response(200, json={"access_token": {"value": "incoming-token"}}),
                httpx.Response(200, json={"access_token": {"value": "quote-token"}}),
                httpx.Response(
                    200,
                    json={"interact": {"redirect": "https://auth.interledger-test.dev/interact/xyz"}},
                ),
            ]
        )
        respx.post(f"{ISSUER_RESOURCE_SERVER}/incoming-payments").mock(
            return_value=httpx.Response(201, json={"id": f"{ISSUER_RESOURCE_SERVER}/incoming-payments/abc"})
        )
        respx.post(f"{OUR_RESOURCE_SERVER}/quotes").mock(
            return_value=httpx.Response(
                201,
                json={"debitAmount": {"value": "250000", "assetCode": "SEK", "assetScale": 2}},
            )
        )

        async with httpx.AsyncClient() as client:
            pay_link = await build_pay_link(
                invoice=invoice,
                our_wallet_address=OUR_WALLET_URL,
                client_id="client-1",
                client_secret="secret-1",
                redirect_uri="https://example.com/demo/return",
                client=client,
            )

    assert pay_link.redirect_uri == "https://auth.interledger-test.dev/interact/xyz"
    assert pay_link.debit_amount_minor == 250000
    assert pay_link.debit_currency == "SEK"
    assert pay_link.invoice_id == invoice.id


async def test_build_pay_link_raises_when_no_wallet_address():
    invoice = make_invoice(issuer_wallet_address=None)

    async with httpx.AsyncClient() as client:
        with pytest.raises(NoWalletAddressError):
            await build_pay_link(
                invoice=invoice,
                our_wallet_address=OUR_WALLET_URL,
                client_id="client-1",
                client_secret="secret-1",
                redirect_uri="https://example.com/demo/return",
                client=client,
            )
