from __future__ import annotations

from ivd.models import ErpContact, Invoice


def _luhn_check_digit(digits: str) -> int:
    """Standard Luhn check digit over `digits`, computed from the rightmost position."""
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return (10 - (total % 10)) % 10


def is_valid_ocr(ocr_reference: str) -> bool:
    """Validate a Bankgirot-style OCR reference: last digit is a Luhn check digit
    over everything before it; second-to-last digit encodes the total length mod 10."""
    if len(ocr_reference) < 2 or not ocr_reference.isdigit():
        return False
    body, check = ocr_reference[:-1], ocr_reference[-1]
    if _luhn_check_digit(body) != int(check):
        return False
    length_digit = ocr_reference[-2]
    return length_digit == str(len(ocr_reference) % 10)


def is_known_issuer(invoice: Invoice, erp_contacts: dict[str, ErpContact]) -> bool:
    return invoice.issuer_org_no in erp_contacts


def is_over_threshold(invoice: Invoice, threshold_minor: int) -> bool:
    return invoice.amount_minor > threshold_minor


def amount_matches_erp(invoice: Invoice, erp_contacts: dict[str, ErpContact]) -> bool:
    """True if the invoice amount agrees with the ERP master record. Only
    meaningful when the issuer is known; callers must check is_known_issuer first."""
    contact = erp_contacts.get(invoice.issuer_org_no)
    if contact is None:
        return False
    return (
        invoice.amount_minor == contact.erp_amount_minor
        and invoice.currency == contact.erp_currency
    )
