from __future__ import annotations

import httpx
import pytest
import respx

from ivd.caller import ELEVENLABS_BASE_URL, UnknownIssuerError, trigger_call
from tests.conftest import make_invoice


async def test_trigger_call_never_reads_phone_off_invoice(erp_contacts, store):
    """An invoice never carries a phone field (Invoice.model_fields has none,
    verified in test_models.py). This test proves the dialler path resolves
    the phone number exclusively from ERP contacts by construction: the
    invoice object passed in has no phone attribute at all, and the call
    still succeeds using the ERP-sourced number."""
    invoice = make_invoice(issuer_org_no="5560123456")
    assert not hasattr(invoice, "phone")

    with respx.mock:
        route = respx.post(f"{ELEVENLABS_BASE_URL}/convai/twilio/outbound-call").mock(
            return_value=httpx.Response(200, json={"conversation_id": "conv-123"})
        )
        binding = await trigger_call(
            invoice=invoice,
            erp_contacts=erp_contacts,
            store=store,
            agent_id="agent-1",
            agent_phone_number_id="phone-1",
            api_key="key-1",
            our_company_name="Acme Demo AB",
        )

    assert binding.invoice_id == invoice.id
    assert binding.conversation_id == "conv-123"
    sent_body = route.calls.last.request.content
    assert erp_contacts["5560123456"].phone.encode() in sent_body


async def test_trigger_call_unknown_issuer_raises(erp_contacts, store):
    invoice = make_invoice(issuer_org_no="0000000000")
    with pytest.raises(UnknownIssuerError):
        await trigger_call(
            invoice=invoice,
            erp_contacts=erp_contacts,
            store=store,
            agent_id="agent-1",
            agent_phone_number_id="phone-1",
            api_key="key-1",
            our_company_name="Acme Demo AB",
        )


async def test_trigger_call_stores_binding(erp_contacts, store):
    invoice = make_invoice(issuer_org_no="5560123456")
    with respx.mock:
        respx.post(f"{ELEVENLABS_BASE_URL}/convai/twilio/outbound-call").mock(
            return_value=httpx.Response(200, json={"conversation_id": "conv-456"})
        )
        await trigger_call(
            invoice=invoice,
            erp_contacts=erp_contacts,
            store=store,
            agent_id="agent-1",
            agent_phone_number_id="phone-1",
            api_key="key-1",
            our_company_name="Acme Demo AB",
        )

    binding = store.get_binding_by_conversation("conv-456")
    assert binding is not None
    assert binding.invoice_id == invoice.id
