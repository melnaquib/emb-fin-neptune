from __future__ import annotations

from ivd.filters import is_known_issuer, is_over_threshold, is_valid_ocr
from ivd.models import Decision, ErpContact, Invoice
from ivd.states import (
    CONFIRMED,
    DENIED,
    FILTER_FAILED,
    FILTERS_PASSED,
    FLAGGED_FOR_REVERIFY,
    GRANT_REQUESTED,
    UNRESOLVED,
    next_state,
)


def decide(
    invoice: Invoice,
    erp_contacts: dict[str, ErpContact],
    threshold_minor: int,
    known_issuer_ids: set[str],
) -> Decision:
    """Pure triage decision for an invoice sitting in `pending`.

    `known_issuer_ids` is the set of issuer org numbers this payer has
    successfully auto-paid before. An issuer outside that set is treated as
    unproven and flagged for reverify even if every filter passes — this is
    what routes first-time issuers through a verification call instead of
    straight to auto-pay.
    """
    if not is_valid_ocr(invoice.ocr_reference):
        return Decision(invoice_id=invoice.id, state=next_state("pending", FILTER_FAILED), reason="invalid OCR reference")

    if not is_known_issuer(invoice, erp_contacts):
        return Decision(invoice_id=invoice.id, state=next_state("pending", FILTER_FAILED), reason="unknown issuer")

    if is_over_threshold(invoice, threshold_minor):
        return Decision(invoice_id=invoice.id, state=next_state("pending", FILTER_FAILED), reason="amount over auto-pay threshold")

    if invoice.issuer_org_no not in known_issuer_ids:
        return Decision(
            invoice_id=invoice.id,
            state=next_state("pending", FLAGGED_FOR_REVERIFY),
            reason="first invoice from this issuer, flagged for reverify",
        )

    return Decision(invoice_id=invoice.id, state=next_state("pending", FILTERS_PASSED), reason="all filters passed")


def decide_from_verification(invoice_id: str, outcome: str) -> Decision:
    """Pure transition from `calling` given a recorded verification outcome."""
    event = CONFIRMED if outcome == "confirmed" else DENIED
    state = next_state("calling", event)
    reason = "issuer confirmed invoice by phone" if event == CONFIRMED else "issuer denied invoice by phone"
    return Decision(invoice_id=invoice_id, state=state, reason=reason)


def decide_unresolved_call(invoice_id: str, reason: str) -> Decision:
    """Pure transition from `calling` when no confirmation was obtained
    (no_answer, voicemail, timeout, or no tool call)."""
    return Decision(invoice_id=invoice_id, state=next_state("calling", UNRESOLVED), reason=reason)


def decide_grant_requested(invoice_id: str, from_state: str) -> Decision:
    state = next_state(from_state, GRANT_REQUESTED)  # type: ignore[arg-type]
    return Decision(invoice_id=invoice_id, state=state, reason="Open Payments grant requested")
