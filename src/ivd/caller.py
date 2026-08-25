from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx

from ivd.models import CallBinding, ErpContact, Invoice
from ivd.store import Store

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"


class UnknownIssuerError(Exception):
    """Raised when an invoice's issuer has no ERP contact record — the dialler
    has no phone number to call and must not guess or fall back to invoice data."""


def _reject_if_invoice_carries_phone(invoice: Invoice) -> None:
    """Invoice never carries a phone field by construction (extra='forbid' in
    the model), but this guard makes the contract explicit and fails loudly if
    that model constraint is ever loosened."""
    if hasattr(invoice, "phone"):
        raise TypeError("Invoice must never carry a phone field; phone comes from ERP contacts only")


async def trigger_call(
    invoice: Invoice,
    erp_contacts: dict[str, ErpContact],
    store: Store,
    agent_id: str,
    agent_phone_number_id: str,
    api_key: str,
    our_company_name: str,
    client: httpx.AsyncClient | None = None,
) -> CallBinding:
    """Places an outbound ElevenLabs call to verify `invoice` with its issuer,
    and records the conversation_id -> invoice_id binding in `store`."""
    _reject_if_invoice_carries_phone(invoice)

    contact = erp_contacts.get(invoice.issuer_org_no)
    if contact is None:
        raise UnknownIssuerError(f"no ERP contact for issuer_org_no={invoice.issuer_org_no}")

    dynamic_variables = {
        "issuer_name": invoice.issuer_name,
        "invoice_amount": _format_amount(invoice.amount_minor),
        "currency": invoice.currency,
        "ocr_reference": invoice.ocr_reference,
        "due_date": invoice.due_date.isoformat(),
        "our_company_name": our_company_name,
        "contact_number": contact.phone,
        # Not part of the spoken conversation; only so the agent can supply
        # invoice_id to record_verification. The server independently
        # validates it against the conversation_id binding, so a wrong or
        # hallucinated value here is caught server-side, not trusted blindly.
        "invoice_id": invoice.id,
    }

    owns_client = client is None
    http = client or httpx.AsyncClient()
    try:
        response = await http.post(
            f"{ELEVENLABS_BASE_URL}/convai/twilio/outbound-call",
            headers={"xi-api-key": api_key},
            json={
                "agent_id": agent_id,
                "agent_phone_number_id": agent_phone_number_id,
                "to_number": contact.phone,
                "conversation_initiation_client_data": {
                    "dynamic_variables": dynamic_variables,
                },
            },
        )
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns_client:
            await http.aclose()

    conversation_id = payload.get("conversation_id") or str(uuid.uuid4())
    binding = CallBinding(
        conversation_id=conversation_id,
        invoice_id=invoice.id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    store.put_binding(binding)
    return binding


def _format_amount(amount_minor: int) -> str:
    return f"{amount_minor / 100:.2f}"
