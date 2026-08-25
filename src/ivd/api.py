from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ivd.mcp_server import RecordVerificationError, build_mcp_server, record_verification
from ivd.models import VerificationOutcome
from ivd.policy import decide_from_verification
from ivd.store import Store, get_default_store


class RecordVerificationPayload(BaseModel):
    conversation_id: str
    invoice_id: str
    outcome: VerificationOutcome
    evidence: str


def build_app(store: Store | None = None) -> FastAPI:
    store = store or get_default_store()
    app = FastAPI(title="invoice-voice-demo")
    mcp = build_mcp_server(store)

    app.mount("/mcp", mcp.sse_app())

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"status": "ok"}

    @app.post("/tools/record-verification")
    async def record_verification_webhook(payload: RecordVerificationPayload) -> dict:
        """Webhook counterpart to the MCP record_verification tool, for the
        ElevenLabs agent's webhook-tool integration. conversation_id must be
        the platform-injected {{system__conversation_id}} variable in the
        tool's request config, never a model-suppliable field."""
        try:
            result = record_verification(
                payload.conversation_id, payload.invoice_id, payload.outcome, payload.evidence, store
            )
        except RecordVerificationError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        decision = decide_from_verification(result.invoice_id, result.outcome)
        store.set_state(result.invoice_id, decision.state, decision.reason)
        return result.model_dump()

    return app


app = build_app()
