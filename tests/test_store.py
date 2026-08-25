from __future__ import annotations

from ivd.store import Store


def test_set_state_appends_audit_entry(store):
    store.set_state("INV-001", "pending", "initial")
    store.set_state("INV-001", "calling", "flagged for reverify")

    log = store.audit_log()
    assert len(log) == 2
    assert log[0].from_state is None
    assert log[0].to_state == "pending"
    assert log[1].from_state == "pending"
    assert log[1].to_state == "calling"


def test_audit_log_is_a_copy_not_a_live_reference(store):
    store.set_state("INV-001", "pending", "initial")
    log = store.audit_log()
    log.clear()
    assert len(store.audit_log()) == 1
