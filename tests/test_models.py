from __future__ import annotations

import pytest
from pydantic import ValidationError

from ivd.models import Invoice
from tests.conftest import make_invoice


def test_invoice_rejects_unknown_field_named_phone():
    with pytest.raises(ValidationError):
        Invoice.model_validate(
            {
                "id": "INV-X",
                "issuer_name": "X",
                "issuer_org_no": "123",
                "amount_minor": 100,
                "currency": "SEK",
                "ocr_reference": "1234567890136",
                "due_date": "2026-09-15",
                "phone": "+46701234567",
            }
        )


def test_invoice_model_has_no_phone_attribute():
    invoice = make_invoice()
    assert not hasattr(invoice, "phone")
    assert "phone" not in Invoice.model_fields


def test_invoice_amount_must_be_positive():
    with pytest.raises(ValidationError):
        make_invoice(amount_minor=0)
