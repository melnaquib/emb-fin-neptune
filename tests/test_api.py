from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from ivd.api import build_app
from ivd.models import CallBinding
from ivd.store import Store


async def test_healthz():
    app = build_app(Store())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_record_verification_webhook_happy_path():
    store = Store()
    store.put_binding(
        CallBinding(conversation_id="conv-1", invoice_id="INV-001", created_at="2026-08-25T00:00:00+00:00")
    )
    app = build_app(store)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/tools/record-verification",
            json={
                "conversation_id": "conv-1",
                "invoice_id": "INV-001",
                "outcome": "confirmed",
                "evidence": "issuer said yes",
            },
        )
    assert response.status_code == 200
    assert store.get_state("INV-001") == "verified"


async def test_record_verification_webhook_rejects_mismatched_invoice_id():
    store = Store()
    store.put_binding(
        CallBinding(conversation_id="conv-1", invoice_id="INV-001", created_at="2026-08-25T00:00:00+00:00")
    )
    app = build_app(store)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/tools/record-verification",
            json={
                "conversation_id": "conv-1",
                "invoice_id": "INV-999",
                "outcome": "confirmed",
                "evidence": "wrong invoice",
            },
        )
    assert response.status_code == 409
    assert store.get_verification("INV-001") is None
