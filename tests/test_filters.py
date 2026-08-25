from __future__ import annotations

from ivd.filters import (
    amount_matches_erp,
    is_known_issuer,
    is_over_threshold,
    is_valid_ocr,
)
from tests.conftest import make_invoice


def test_valid_ocr_reference_accepted():
    assert is_valid_ocr("1234567890136") is True


def test_ocr_reference_with_mutated_check_digit_rejected():
    assert is_valid_ocr("1234567890137") is False


def test_ocr_reference_with_mutated_length_digit_rejected():
    assert is_valid_ocr("1234567890146") is False


def test_ocr_reference_non_digit_rejected():
    assert is_valid_ocr("12345abc890136") is False


def test_ocr_reference_too_short_rejected():
    assert is_valid_ocr("5") is False


def test_known_issuer(erp_contacts):
    invoice = make_invoice(issuer_org_no="5560123456")
    assert is_known_issuer(invoice, erp_contacts) is True


def test_unknown_issuer(erp_contacts):
    invoice = make_invoice(issuer_org_no="0000000000")
    assert is_known_issuer(invoice, erp_contacts) is False


def test_over_threshold():
    invoice = make_invoice(amount_minor=1000001)
    assert is_over_threshold(invoice, threshold_minor=1000000) is True


def test_not_over_threshold():
    invoice = make_invoice(amount_minor=1000000)
    assert is_over_threshold(invoice, threshold_minor=1000000) is False


def test_amount_matches_erp_true(erp_contacts, inv_001):
    assert amount_matches_erp(inv_001, erp_contacts) is True


def test_amount_matches_erp_false_on_mismatch(erp_contacts, inv_002):
    assert amount_matches_erp(inv_002, erp_contacts) is False


def test_amount_matches_erp_false_for_unknown_issuer(erp_contacts):
    invoice = make_invoice(issuer_org_no="0000000000")
    assert amount_matches_erp(invoice, erp_contacts) is False
