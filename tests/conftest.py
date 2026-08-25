from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from ivd.models import ErpContact, Invoice
from ivd.store import Store

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def erp_contacts() -> dict[str, ErpContact]:
    raw = json.loads((FIXTURES_DIR / "erp_contacts.json").read_text())
    return {org_no: ErpContact.model_validate(row) for org_no, row in raw.items()}


@pytest.fixture
def sample_invoices() -> list[Invoice]:
    raw = json.loads((FIXTURES_DIR / "invoices.sample.json").read_text())
    return [Invoice.model_validate(item) for item in raw]


@pytest.fixture
def inv_001(sample_invoices: list[Invoice]) -> Invoice:
    return next(inv for inv in sample_invoices if inv.id == "INV-001")


@pytest.fixture
def inv_002(sample_invoices: list[Invoice]) -> Invoice:
    return next(inv for inv in sample_invoices if inv.id == "INV-002")


@pytest.fixture
def store() -> Store:
    return Store()


def make_invoice(**overrides) -> Invoice:
    defaults = dict(
        id="INV-TEST",
        issuer_name="Test Issuer AB",
        issuer_org_no="5560123456",
        amount_minor=10000,
        currency="SEK",
        ocr_reference="1234567890136",
        due_date=date(2026, 9, 15),
        issuer_wallet_address="https://ilp.interledger-test.dev/test-issuer",
    )
    defaults.update(overrides)
    return Invoice(**defaults)
