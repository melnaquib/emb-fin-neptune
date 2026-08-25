from __future__ import annotations

from datetime import datetime, timezone

from ivd.models import AuditEntry, CallBinding, Invoice, State, VerificationResult


class Store:
    """In-memory demo store — plain dicts, no database. The CLI persists a
    JSON snapshot at the process boundary (see snapshot.py) purely so the
    multi-step demo script works across separate `ivd` invocations; the
    Store class itself has no file I/O and no real durability guarantees."""

    def __init__(self) -> None:
        self._invoices: dict[str, Invoice] = {}
        self._states: dict[str, State] = {}
        self._bindings_by_conversation: dict[str, CallBinding] = {}
        self._bindings_by_invoice: dict[str, CallBinding] = {}
        self._verifications: dict[str, VerificationResult] = {}
        self._audit: list[AuditEntry] = []
        self._known_issuer_ids: set[str] = set()

    def put_invoice(self, invoice: Invoice) -> None:
        self._invoices[invoice.id] = invoice

    def get_invoice(self, invoice_id: str) -> Invoice | None:
        return self._invoices.get(invoice_id)

    def all_invoices(self) -> list[Invoice]:
        return list(self._invoices.values())

    def get_state(self, invoice_id: str) -> State | None:
        return self._states.get(invoice_id)

    def set_state(self, invoice_id: str, state: State, reason: str) -> None:
        from_state = self._states.get(invoice_id)
        self._states[invoice_id] = state
        self._audit.append(
            AuditEntry(
                invoice_id=invoice_id,
                from_state=from_state,
                to_state=state,
                reason=reason,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    def audit_log(self) -> list[AuditEntry]:
        return list(self._audit)

    def known_issuer_ids(self) -> set[str]:
        return set(self._known_issuer_ids)

    def mark_issuer_known(self, issuer_org_no: str) -> None:
        self._known_issuer_ids.add(issuer_org_no)

    def put_binding(self, binding: CallBinding) -> None:
        self._bindings_by_conversation[binding.conversation_id] = binding
        self._bindings_by_invoice[binding.invoice_id] = binding

    def get_binding_by_conversation(self, conversation_id: str) -> CallBinding | None:
        return self._bindings_by_conversation.get(conversation_id)

    def get_binding_by_invoice(self, invoice_id: str) -> CallBinding | None:
        return self._bindings_by_invoice.get(invoice_id)

    def put_verification(self, result: VerificationResult) -> None:
        self._verifications[result.invoice_id] = result

    def get_verification(self, invoice_id: str) -> VerificationResult | None:
        return self._verifications.get(invoice_id)

    def to_dict(self) -> dict:
        """Plain-dict snapshot of all state, for CLI-boundary persistence
        between separate process invocations. The Store itself stays
        in-memory-only; nothing here touches a file."""
        return {
            "invoices": {k: v.model_dump(mode="json") for k, v in self._invoices.items()},
            "states": dict(self._states),
            "bindings_by_conversation": {k: v.model_dump(mode="json") for k, v in self._bindings_by_conversation.items()},
            "verifications": {k: v.model_dump(mode="json") for k, v in self._verifications.items()},
            "audit": [entry.model_dump(mode="json") for entry in self._audit],
            "known_issuer_ids": sorted(self._known_issuer_ids),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Store":
        store = cls()
        for row in data.get("invoices", {}).values():
            store.put_invoice(Invoice.model_validate(row))
        store._states = dict(data.get("states", {}))
        for row in data.get("bindings_by_conversation", {}).values():
            store.put_binding(CallBinding.model_validate(row))
        for row in data.get("verifications", {}).values():
            store.put_verification(VerificationResult.model_validate(row))
        store._audit = [AuditEntry.model_validate(row) for row in data.get("audit", [])]
        store._known_issuer_ids = set(data.get("known_issuer_ids", []))
        return store


_default_store = Store()


def get_default_store() -> Store:
    return _default_store
