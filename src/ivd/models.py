from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

State = Literal[
    "pending",
    "auto_pay",
    "calling",
    "verified",
    "rejected",
    "needs_human",
    "pay_link_issued",
]

VerificationOutcome = Literal["confirmed", "denied"]


class Invoice(BaseModel):
    """Normalized incoming invoice. Deliberately has no phone field —
    contact details are ERP master data, resolved separately by org number."""

    model_config = ConfigDict(extra="forbid")

    id: str
    issuer_name: str
    issuer_org_no: str
    amount_minor: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    ocr_reference: str
    due_date: date
    issuer_wallet_address: str | None = None


class Decision(BaseModel):
    """Output of policy.decide(): the invoice's next state and why."""

    model_config = ConfigDict(extra="forbid")

    invoice_id: str
    state: State
    reason: str


class CallBinding(BaseModel):
    """Binds a live ElevenLabs conversation to the invoice it was placed for."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    invoice_id: str
    created_at: str


class VerificationResult(BaseModel):
    """Result recorded by the MCP tool after a call resolves."""

    model_config = ConfigDict(extra="forbid")

    invoice_id: str
    outcome: VerificationOutcome
    evidence: str


class ErpContact(BaseModel):
    """A single row of ERP master data: issuer_org_no -> contact + expected amount."""

    model_config = ConfigDict(extra="forbid")

    issuer_name: str
    phone: str
    erp_amount_minor: int = Field(gt=0)
    erp_currency: str = Field(min_length=3, max_length=3)


class PayLink(BaseModel):
    """Result of payments.build_pay_link(): the Open Payments interactive redirect."""

    model_config = ConfigDict(extra="forbid")

    invoice_id: str
    redirect_uri: str
    debit_amount_minor: int
    debit_currency: str


class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: str
    from_state: State | None
    to_state: State
    reason: str
    timestamp: str


__all__ = [
    "State",
    "VerificationOutcome",
    "Invoice",
    "Decision",
    "CallBinding",
    "VerificationResult",
    "ErpContact",
    "PayLink",
    "AuditEntry",
]
