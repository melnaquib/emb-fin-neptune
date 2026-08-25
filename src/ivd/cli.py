from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import httpx
import typer
from dotenv import load_dotenv

from ivd import snapshot
from ivd.caller import UnknownIssuerError, trigger_call
from ivd.mcp_server import RecordVerificationError, record_verification
from ivd.models import ErpContact, Invoice
from ivd.payments import NoWalletAddressError, build_pay_link
from ivd.policy import decide, decide_from_verification, decide_grant_requested
from ivd.sources.jsonfile import JsonFileSource
from ivd.sources.zwapgrid import ZwapgridSource
from ivd.store import Store

load_dotenv()

app = typer.Typer(add_completion=False)

ERP_CONTACTS_PATH = Path(__file__).resolve().parents[2] / "data" / "erp_contacts.json"


def _load_erp_contacts() -> dict[str, ErpContact]:
    raw = json.loads(ERP_CONTACTS_PATH.read_text())
    return {org_no: ErpContact.model_validate(row) for org_no, row in raw.items()}


def _load_invoices_into_store(store: Store, invoices: list[Invoice]) -> None:
    for invoice in invoices:
        store.put_invoice(invoice)


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        typer.echo(f"missing required environment variable: {name} (see .env.example)", err=True)
        raise typer.Exit(code=1)
    return value


@app.command()
def fetch(source: str = typer.Option("json", "--source", help="json or zwapgrid")) -> None:
    """Fetch normalized invoices and print them as JSON."""
    invoices = asyncio.run(_fetch(source))
    typer.echo(json.dumps([inv.model_dump(mode="json") for inv in invoices], indent=2))


async def _fetch(source: str) -> list[Invoice]:
    if source == "json":
        return await JsonFileSource().fetch()
    if source == "zwapgrid":
        base_url = _require_env("ZWAPGRID_API_BASE")
        api_key = _require_env("ZWAPGRID_API_KEY")
        return await ZwapgridSource(base_url, api_key).fetch()
    raise typer.BadParameter(f"unknown source: {source}")


@app.command()
def triage(source: str = typer.Option("json", "--source", help="json or zwapgrid")) -> None:
    """Fetch invoices, run filters + policy, print each invoice's resulting state."""
    store = snapshot.load()
    erp_contacts = _load_erp_contacts()
    invoices = asyncio.run(_fetch(source))
    _load_invoices_into_store(store, invoices)

    threshold = int(os.environ.get("AUTO_PAY_THRESHOLD_MINOR", "1000000"))
    results = []
    for invoice in invoices:
        decision = decide(invoice, erp_contacts, threshold, store.known_issuer_ids())
        store.set_state(invoice.id, decision.state, decision.reason)
        results.append(decision.model_dump())

    snapshot.save(store)
    typer.echo(json.dumps(results, indent=2))


@app.command()
def call(invoice_id: str) -> None:
    """Create a call binding and trigger the outbound ElevenLabs call for invoice_id."""
    store = snapshot.load()
    erp_contacts = _load_erp_contacts()
    invoice = store.get_invoice(invoice_id)
    if invoice is None:
        typer.echo(f"unknown invoice_id: {invoice_id}", err=True)
        raise typer.Exit(code=1)

    current_state = store.get_state(invoice_id)
    if current_state != "calling":
        typer.echo(f"invoice {invoice_id} is not in 'calling' state (currently {current_state!r}); run 'ivd triage' first", err=True)
        raise typer.Exit(code=1)

    try:
        binding = asyncio.run(
            trigger_call(
                invoice=invoice,
                erp_contacts=erp_contacts,
                store=store,
                agent_id=_require_env("ELEVENLABS_AGENT_ID"),
                agent_phone_number_id=_require_env("ELEVENLABS_AGENT_PHONE_NUMBER_ID"),
                api_key=_require_env("ELEVENLABS_API_KEY"),
                our_company_name=os.environ.get("OUR_COMPANY_NAME", "our company"),
            )
        )
    except UnknownIssuerError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    snapshot.save(store)
    typer.echo(json.dumps(binding.model_dump(), indent=2))


@app.command()
def verify(invoice_id: str, outcome: str = typer.Argument(..., help="confirmed or denied")) -> None:
    """Simulate the MCP record_verification tool call for a demo run without a
    live phone call. In the real flow this is invoked by the ElevenLabs agent
    mid-conversation; this command exists so the CLI script is runnable end
    to end without dialling out."""
    if outcome not in ("confirmed", "denied"):
        typer.echo("outcome must be 'confirmed' or 'denied'", err=True)
        raise typer.Exit(code=1)

    store = snapshot.load()
    binding = store.get_binding_by_invoice(invoice_id)
    if binding is None:
        typer.echo(f"no call binding for invoice_id={invoice_id}; run 'ivd call {invoice_id}' first", err=True)
        raise typer.Exit(code=1)

    try:
        record_verification(binding.conversation_id, invoice_id, outcome, "recorded via ivd verify", store)
    except RecordVerificationError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    decision = decide_from_verification(invoice_id, outcome)
    store.set_state(invoice_id, decision.state, decision.reason)
    snapshot.save(store)
    typer.echo(json.dumps(decision.model_dump(), indent=2))


@app.command()
def pay(invoice_id: str) -> None:
    """Build and print the Open Payments redirect URL for invoice_id."""
    store = snapshot.load()
    invoice = store.get_invoice(invoice_id)
    if invoice is None:
        typer.echo(f"unknown invoice_id: {invoice_id}", err=True)
        raise typer.Exit(code=1)

    current_state = store.get_state(invoice_id)
    if current_state not in ("auto_pay", "verified"):
        typer.echo(f"invoice {invoice_id} is not payable (currently {current_state!r})", err=True)
        raise typer.Exit(code=1)

    try:
        pay_link = asyncio.run(_build_pay_link(invoice))
    except NoWalletAddressError:
        store.set_state(invoice_id, "needs_human", "no wallet address on file for issuer")
        snapshot.save(store)
        typer.echo(f"invoice {invoice_id} has no wallet address; routed to needs_human", err=True)
        raise typer.Exit(code=1)

    decision = decide_grant_requested(invoice_id, current_state)
    store.set_state(invoice_id, decision.state, decision.reason)
    snapshot.save(store)
    typer.echo(pay_link.redirect_uri)


async def _build_pay_link(invoice: Invoice):
    async with httpx.AsyncClient() as client:
        return await build_pay_link(
            invoice=invoice,
            our_wallet_address=_require_env("OPEN_PAYMENTS_WALLET_ADDRESS"),
            client_id=_require_env("OPEN_PAYMENTS_CLIENT_ID"),
            client_secret=_require_env("OPEN_PAYMENTS_CLIENT_SECRET"),
            redirect_uri="https://example.com/demo/return",
            client=client,
        )


if __name__ == "__main__":
    app()
