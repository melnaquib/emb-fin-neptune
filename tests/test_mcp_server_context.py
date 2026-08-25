from __future__ import annotations

from types import SimpleNamespace

import pytest

from ivd.mcp_server import CONVERSATION_ID_HEADER, RecordVerificationError, _conversation_id_from_context


def _fake_context(headers: dict) -> SimpleNamespace:
    request = SimpleNamespace(headers=headers)
    request_context = SimpleNamespace(request=request)
    return SimpleNamespace(request_context=request_context)


def test_conversation_id_resolved_from_header():
    ctx = _fake_context({CONVERSATION_ID_HEADER: "conv-abc"})
    assert _conversation_id_from_context(ctx) == "conv-abc"


def test_missing_header_rejected():
    ctx = _fake_context({})
    with pytest.raises(RecordVerificationError):
        _conversation_id_from_context(ctx)


def test_missing_request_rejected():
    request_context = SimpleNamespace(request=None)
    ctx = SimpleNamespace(request_context=request_context)
    with pytest.raises(RecordVerificationError):
        _conversation_id_from_context(ctx)
