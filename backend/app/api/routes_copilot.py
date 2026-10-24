"""FastAPI router for ORACLE Conversational Investigation Copilot."""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..schemas.copilot import (
    CopilotChatRequest,
    CopilotCreateSessionRequest,
    CopilotMessage,
    CopilotSession,
)

logger = logging.getLogger("oracle.api.copilot")
router = APIRouter(tags=["Investigation Copilot"])


def get_copilot_service(request: Request):
    """Retrieve CopilotService singleton from application state."""
    service = getattr(request.app.state, "copilot_service", None)
    if not service:
        raise HTTPException(status_code=500, detail="CopilotService is not initialized.")
    return service


@router.get("/sessions", response_model=List[CopilotSession])
def list_sessions(request: Request) -> List[CopilotSession]:
    """List all active and archived investigation sessions."""
    service = get_copilot_service(request)
    return service.list_sessions()


@router.post("/sessions", response_model=CopilotSession)
def create_session(payload: CopilotCreateSessionRequest, request: Request) -> CopilotSession:
    """Create a new conversational investigation session."""
    service = get_copilot_service(request)
    return service.create_session(
        title=payload.title,
        primary_technology=payload.primary_technology,
        severity=payload.severity or "high",
    )


@router.get("/sessions/{session_id}", response_model=CopilotSession)
def get_session(session_id: str, request: Request) -> CopilotSession:
    """Fetch details and full message history of an investigation session."""
    service = get_copilot_service(request)
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return session


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, request: Request):
    """Delete an investigation session."""
    service = get_copilot_service(request)
    deleted = service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {"status": "deleted", "session_id": session_id}


@router.post("/sessions/{session_id}/chat", response_model=CopilotMessage)
async def chat(
    session_id: str,
    payload: CopilotChatRequest,
    request: Request,
) -> CopilotMessage:
    """Post a question and receive a complete, grounded assistant response."""
    service = get_copilot_service(request)
    try:
        return await service.chat(session_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Copilot chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/chat/stream")
async def chat_stream(
    session_id: str,
    payload: CopilotChatRequest,
    request: Request,
):
    """Post a question and stream tokens and metadata via Server-Sent Events (SSE)."""
    service = get_copilot_service(request)
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    return StreamingResponse(
        service.stream_chat(session_id, payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/stream")
async def direct_chat_stream(
    payload: CopilotChatRequest,
    request: Request,
    session_id: Optional[str] = None,
):
    """Direct stream chat endpoint supporting optional session creation or ephemeral session."""
    service = get_copilot_service(request)
    sid = session_id or getattr(payload, "session_id", None)
    if not sid or not service.get_session(sid):
        sess = service.create_session(title="Investigation Chat", primary_technology="general", severity="medium")
        sid = sess.id

    return StreamingResponse(
        service.stream_chat(sid, payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
