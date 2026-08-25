from __future__ import annotations

from ivd.models import State

# Events are internal vocabulary — not exposed outside this module — describing
# *why* a transition happens. Kept as plain strings since they only ever feed
# the table below.
Event = str

FILTERS_PASSED = "filters_passed"
FLAGGED_FOR_REVERIFY = "flagged_for_reverify"
FILTER_FAILED = "filter_failed"
CONFIRMED = "confirmed"
DENIED = "denied"
UNRESOLVED = "unresolved"  # no_answer, voicemail, timeout, no tool call
GRANT_REQUESTED = "grant_requested"

# (from_state, event) -> to_state. The single source of truth for legal moves.
_TRANSITIONS: dict[tuple[State, Event], State] = {
    ("pending", FILTERS_PASSED): "auto_pay",
    ("pending", FLAGGED_FOR_REVERIFY): "calling",
    ("pending", FILTER_FAILED): "needs_human",
    ("calling", CONFIRMED): "verified",
    ("calling", DENIED): "rejected",
    ("calling", UNRESOLVED): "needs_human",
    ("auto_pay", GRANT_REQUESTED): "pay_link_issued",
    ("verified", GRANT_REQUESTED): "pay_link_issued",
}


class IllegalTransitionError(Exception):
    def __init__(self, from_state: State, event: Event):
        self.from_state = from_state
        self.event = event
        super().__init__(f"illegal transition: {from_state!r} + {event!r}")


def next_state(from_state: State, event: Event) -> State:
    """Look up the legal next state for (from_state, event). Raises on illegal moves."""
    key = (from_state, event)
    if key not in _TRANSITIONS:
        raise IllegalTransitionError(from_state, event)
    return _TRANSITIONS[key]


def is_legal(from_state: State, event: Event) -> bool:
    return (from_state, event) in _TRANSITIONS
