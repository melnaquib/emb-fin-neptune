from __future__ import annotations

import pytest

from ivd.states import (
    CONFIRMED,
    DENIED,
    FILTER_FAILED,
    FILTERS_PASSED,
    FLAGGED_FOR_REVERIFY,
    GRANT_REQUESTED,
    UNRESOLVED,
    IllegalTransitionError,
    is_legal,
    next_state,
)

LEGAL_TRANSITIONS = [
    ("pending", FILTERS_PASSED, "auto_pay"),
    ("pending", FLAGGED_FOR_REVERIFY, "calling"),
    ("pending", FILTER_FAILED, "needs_human"),
    ("calling", CONFIRMED, "verified"),
    ("calling", DENIED, "rejected"),
    ("calling", UNRESOLVED, "needs_human"),
    ("auto_pay", GRANT_REQUESTED, "pay_link_issued"),
    ("verified", GRANT_REQUESTED, "pay_link_issued"),
]


@pytest.mark.parametrize("from_state,event,to_state", LEGAL_TRANSITIONS)
def test_legal_transition(from_state, event, to_state):
    assert next_state(from_state, event) == to_state
    assert is_legal(from_state, event) is True


ALL_STATES = [
    "pending",
    "auto_pay",
    "calling",
    "verified",
    "rejected",
    "needs_human",
    "pay_link_issued",
]
ALL_EVENTS = [
    FILTERS_PASSED,
    FLAGGED_FOR_REVERIFY,
    FILTER_FAILED,
    CONFIRMED,
    DENIED,
    UNRESOLVED,
    GRANT_REQUESTED,
]


def _illegal_pairs():
    legal = {(f, e) for f, e, _ in LEGAL_TRANSITIONS}
    for from_state in ALL_STATES:
        for event in ALL_EVENTS:
            if (from_state, event) not in legal:
                yield from_state, event


@pytest.mark.parametrize("from_state,event", list(_illegal_pairs()))
def test_illegal_transition_raises(from_state, event):
    assert is_legal(from_state, event) is False
    with pytest.raises(IllegalTransitionError):
        next_state(from_state, event)


def test_rejected_only_reachable_via_explicit_denial():
    """rejected must only be reachable from calling+DENIED — no other
    (state, event) pair in the legal table may lead there."""
    from ivd.states import _TRANSITIONS

    rejected_sources = [(f, e) for (f, e), to in _TRANSITIONS.items() if to == "rejected"]
    assert rejected_sources == [("calling", DENIED)]
