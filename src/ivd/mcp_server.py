from __future__ import annotations

from mcp.server.fastmcp import Context, FastMCP

from ivd.models import VerificationOutcome, VerificationResult
from ivd.store import Store

# Header ElevenLabs' MCP client sets to identify the calling conversation.
# Never trust a conversation_id supplied as a tool argument — that would let
# the agent (or a malicious prompt) claim to be any conversation it likes.
CONVERSATION_ID_HEADER = "x-elevenlabs-conversation-id"


class RecordVerificationError(Exception):
    """Raised for a rejected record_verification call: mismatched invoice_id
    or a second call attempting to change an already-recorded outcome."""


def record_verification(
    conversation_id: str,
    invoice_id: str,
    outcome: VerificationOutcome,
    evidence: str,
    store: Store,
) -> VerificationResult:
    """Core logic behind the MCP tool, factored out for direct testing.

    The conversation is resolved from its own binding (created at call time,
    not supplied by the caller) and the supplied invoice_id is validated
    against it. A mismatch is rejected and nothing is mutated. A second call
    for an invoice that already has a recorded verification is rejected too,
    even if the outcome would be identical — recording is one-shot.
    """
    binding = store.get_binding_by_conversation(conversation_id)
    if binding is None:
        print(f"[record_verification] REJECTED: no call binding for conversation_id={conversation_id}")
        raise RecordVerificationError(f"no call binding for conversation_id={conversation_id}")

    if binding.invoice_id != invoice_id:
        print(
            f"[record_verification] REJECTED: invoice_id mismatch — tool call claimed "
            f"{invoice_id!r}, but conversation {conversation_id!r} is bound to {binding.invoice_id!r}"
        )
        raise RecordVerificationError(
            f"invoice_id mismatch: tool call claimed {invoice_id!r}, "
            f"but conversation {conversation_id!r} is bound to {binding.invoice_id!r}"
        )

    existing = store.get_verification(invoice_id)
    if existing is not None:
        print(f"[record_verification] REJECTED: verification already recorded for invoice_id={invoice_id}")
        raise RecordVerificationError(f"verification already recorded for invoice_id={invoice_id}")

    result = VerificationResult(invoice_id=invoice_id, outcome=outcome, evidence=evidence)
    store.put_verification(result)
    print(f"[record_verification] invoice_id={invoice_id} outcome={outcome} evidence={evidence!r}")
    return result


def _conversation_id_from_context(ctx: Context) -> str:
    """Resolve the calling conversation from transport-level request headers,
    never from an LLM-suppliable tool argument."""
    request = ctx.request_context.request
    conversation_id = request.headers.get(CONVERSATION_ID_HEADER) if request else None
    if not conversation_id:
        raise RecordVerificationError(f"missing {CONVERSATION_ID_HEADER} header on MCP request")
    return conversation_id


def build_mcp_server(store: Store) -> FastMCP:
    mcp = FastMCP("invoice-voice-demo")

    @mcp.tool()
    def record_verification_tool(
        invoice_id: str,
        outcome: VerificationOutcome,
        evidence: str,
        ctx: Context,
    ) -> dict:
        """Record the outcome of a verification call for invoice_id. The
        calling conversation is resolved server-side from the request, not
        supplied by the model — do not ask for or accept a conversation id."""
        conversation_id = _conversation_id_from_context(ctx)
        result = record_verification(conversation_id, invoice_id, outcome, evidence, store)
        return result.model_dump()

    return mcp
