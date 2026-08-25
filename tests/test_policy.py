from __future__ import annotations

from ivd.policy import decide, decide_from_verification, decide_grant_requested, decide_unresolved_call
from tests.conftest import make_invoice

THRESHOLD = 1_000_000


def test_pending_invoice_from_unknown_issuer_never_seen_before_flagged_for_reverify(erp_contacts, inv_001):
    decision = decide(inv_001, erp_contacts, THRESHOLD, known_issuer_ids=set())
    assert decision.state == "calling"


def test_pending_invoice_from_previously_known_issuer_auto_pays(erp_contacts, inv_001):
    decision = decide(inv_001, erp_contacts, THRESHOLD, known_issuer_ids={inv_001.issuer_org_no})
    assert decision.state == "auto_pay"


def test_pending_invoice_invalid_ocr_goes_needs_human(erp_contacts, inv_001):
    bad = inv_001.model_copy(update={"ocr_reference": "0000000000000"})
    decision = decide(bad, erp_contacts, THRESHOLD, known_issuer_ids={bad.issuer_org_no})
    assert decision.state == "needs_human"
    assert "OCR" in decision.reason


def test_pending_invoice_unknown_issuer_goes_needs_human(erp_contacts):
    invoice = make_invoice(issuer_org_no="0000000000")
    decision = decide(invoice, erp_contacts, THRESHOLD, known_issuer_ids={invoice.issuer_org_no})
    assert decision.state == "needs_human"
    assert "issuer" in decision.reason


def test_pending_invoice_over_threshold_goes_needs_human(erp_contacts, inv_001):
    over = inv_001.model_copy(update={"amount_minor": THRESHOLD + 1})
    decision = decide(over, erp_contacts, THRESHOLD, known_issuer_ids={over.issuer_org_no})
    assert decision.state == "needs_human"
    assert "threshold" in decision.reason


def test_inv_001_fixture_path_pending_to_calling(erp_contacts, inv_001):
    """INV-001: clean, flagged for reverify -> calling."""
    decision = decide(inv_001, erp_contacts, THRESHOLD, known_issuer_ids=set())
    assert decision.state == "calling"


def test_inv_001_fixture_path_calling_to_verified():
    decision = decide_from_verification("INV-001", "confirmed")
    assert decision.state == "verified"


def test_inv_001_fixture_path_verified_to_pay_link_issued():
    decision = decide_grant_requested("INV-001", "verified")
    assert decision.state == "pay_link_issued"


def test_inv_002_fixture_path_pending_to_calling(erp_contacts, inv_002):
    """INV-002: amount mismatches ERP -> still passes triage filters (amount
    mismatch is discovered on the call, not at triage) -> flagged -> calling."""
    decision = decide(inv_002, erp_contacts, THRESHOLD, known_issuer_ids=set())
    assert decision.state == "calling"


def test_inv_002_fixture_path_calling_to_rejected():
    decision = decide_from_verification("INV-002", "denied")
    assert decision.state == "rejected"


def test_unresolved_call_goes_needs_human():
    decision = decide_unresolved_call("INV-003", "no_answer")
    assert decision.state == "needs_human"
    assert decision.reason == "no_answer"
