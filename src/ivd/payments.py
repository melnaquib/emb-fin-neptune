from __future__ import annotations

import httpx

from ivd.models import Invoice, PayLink


class NoWalletAddressError(Exception):
    """Raised when the issuer has no wallet address on file. Callers must
    route this to `needs_human`, not let it crash the pipeline."""


async def build_pay_link(
    invoice: Invoice,
    our_wallet_address: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    client: httpx.AsyncClient,
) -> PayLink:
    """Open Payments testnet flow, stopping at the interactive grant redirect:

    1. GET issuer wallet address (resource server metadata)
    2. create incoming payment (on the issuer's resource server)
    3. get a quote (on our resource server)
    4. request an outgoing payment grant with interact.redirect and
       limits.debitAmount from the quote
    5. return the redirect URI

    Does not implement `continue` / `interact_ref` — the demo stops once the
    redirect is printed. If the issuer has no wallet address, raises
    NoWalletAddressError; the caller is responsible for mapping that to
    `needs_human` rather than crashing.
    """
    if not invoice.issuer_wallet_address:
        raise NoWalletAddressError(f"invoice {invoice.id} has no issuer_wallet_address")

    issuer_wallet = await _get_wallet_address(invoice.issuer_wallet_address, client)
    our_wallet = await _get_wallet_address(our_wallet_address, client)

    grant = await _request_grant(
        auth_server=our_wallet["authServer"],
        client_id=client_id,
        client_secret=client_secret,
        access_type="incoming-payment",
        client=client,
    )
    incoming_payment = await _create_incoming_payment(
        resource_server=issuer_wallet["resourceServer"],
        wallet_address=issuer_wallet["id"],
        access_token=grant["access_token"]["value"],
        client=client,
    )

    quote_grant = await _request_grant(
        auth_server=our_wallet["authServer"],
        client_id=client_id,
        client_secret=client_secret,
        access_type="quote",
        client=client,
    )
    quote = await _create_quote(
        resource_server=our_wallet["resourceServer"],
        wallet_address=our_wallet["id"],
        receiver=incoming_payment["id"],
        access_token=quote_grant["access_token"]["value"],
        client=client,
    )

    outgoing_grant = await _request_outgoing_payment_grant(
        auth_server=our_wallet["authServer"],
        client_id=client_id,
        client_secret=client_secret,
        wallet_address=our_wallet["id"],
        debit_amount=quote["debitAmount"],
        redirect_uri=redirect_uri,
        client=client,
    )

    return PayLink(
        invoice_id=invoice.id,
        redirect_uri=outgoing_grant["interact"]["redirect"],
        debit_amount_minor=int(quote["debitAmount"]["value"]),
        debit_currency=quote["debitAmount"]["assetCode"],
    )


async def _get_wallet_address(wallet_address_url: str, client: httpx.AsyncClient) -> dict:
    response = await client.get(wallet_address_url)
    response.raise_for_status()
    return response.json()


async def _request_grant(
    auth_server: str,
    client_id: str,
    client_secret: str,
    access_type: str,
    client: httpx.AsyncClient,
) -> dict:
    response = await client.post(
        f"{auth_server}/",
        json={
            "access_token": {
                "access": [{"type": access_type, "actions": ["create", "read"]}],
            },
            "client": client_id,
        },
        headers={"Content-Type": "application/json"},
        auth=(client_id, client_secret),
    )
    response.raise_for_status()
    return response.json()


async def _create_incoming_payment(
    resource_server: str,
    wallet_address: str,
    access_token: str,
    client: httpx.AsyncClient,
) -> dict:
    response = await client.post(
        f"{resource_server}/incoming-payments",
        json={"walletAddress": wallet_address},
        headers={"Authorization": f"GNAP {access_token}"},
    )
    response.raise_for_status()
    return response.json()


async def _create_quote(
    resource_server: str,
    wallet_address: str,
    receiver: str,
    access_token: str,
    client: httpx.AsyncClient,
) -> dict:
    response = await client.post(
        f"{resource_server}/quotes",
        json={"walletAddress": wallet_address, "receiver": receiver, "method": "ilp"},
        headers={"Authorization": f"GNAP {access_token}"},
    )
    response.raise_for_status()
    return response.json()


async def _request_outgoing_payment_grant(
    auth_server: str,
    client_id: str,
    client_secret: str,
    wallet_address: str,
    debit_amount: dict,
    redirect_uri: str,
    client: httpx.AsyncClient,
) -> dict:
    response = await client.post(
        f"{auth_server}/",
        json={
            "access_token": {
                "access": [
                    {
                        "type": "outgoing-payment",
                        "actions": ["create", "read"],
                        "identifier": wallet_address,
                        "limits": {"debitAmount": debit_amount},
                    }
                ],
            },
            "client": client_id,
            "interact": {"start": ["redirect"]},
        },
        headers={"Content-Type": "application/json"},
        auth=(client_id, client_secret),
    )
    response.raise_for_status()
    return response.json()
