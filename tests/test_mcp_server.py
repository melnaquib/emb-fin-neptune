from __future__ import annotations

import pytest

from ivd.mcp_server import RecordVerificationError, record_verification
from ivd.models import CallBinding


def _bind(store, conversation_id: str, invoice_id: str) -> None:
    store.put_binding(
        CallBinding(conversation_id=conversation_id, invoice_id=invoice_id, created_at="2026-08-25T00:00:00+00:00")
    )


def test_record_verification_happy_path(store):
    _bind(store, "conv-1", "INV-001")
    result = record_verification("conv-1", "INV-001", "confirmed", "issuer said yes", store)
    assert result.outcome == "confirmed"
    assert store.get_verification("INV-001") == result


def test_record_verification_rejects_mismatched_invoice_id(store):
    """The bound conversation is for INV-001. A tool call claiming a
    different invoice_id must be rejected and must not mutate the store."""
    _bind(store, "conv-1", "INV-001")

    with pytest.raises(RecordVerificationError):
        record_verification("conv-1", "INV-999", "confirmed", "wrong invoice", store)

    assert store.get_verification("INV-001") is None
    assert store.get_verification("INV-999") is None


def test_record_verification_rejects_unbound_conversation(store):
    with pytest.raises(RecordVerificationError):
        record_verification("conv-unknown", "INV-001", "confirmed", "evidence", store)


def test_record_verification_idempotent_second_call_rejected(store):
    _bind(store, "conv-1", "INV-001")
    record_verification("conv-1", "INV-001", "confirmed", "first call", store)

    with pytest.raises(RecordVerificationError):
        record_verification("conv-1", "INV-001", "denied", "second call, different outcome", store)

    assert store.get_verification("INV-001").outcome == "confirmed"
