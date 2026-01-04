"""Agent API routes - chat with AI coaching agents."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel
import structlog

from ...concepts.idea import IdeaConcept
from ...concepts.kernel_file import KernelFileConcept
from ...concepts.session import session_concept
from ...concepts.agents import get_agent_for_file_type
from ...db.connection import get_db
from ...db.migrations import SALLY_USER_ID

logger = structlog.get_logger()

router = APIRouter(prefix="/api/ideas", tags=["agent"])

idea_concept = IdeaConcept()
kernel_file_concept = KernelFileConcept()


# --- Helper Functions ---


def get_current_user_info(cookie_value: Optional[str]) -> tuple[UUID, UUID]:
    """
    Get current user ID and org ID from cookie.

    Returns (user_id, org_id) tuple.
    Falls back to Sally if no cookie.
    """
    user_id = UUID(cookie_value) if cookie_value else SALLY_USER_ID

    with get_db() as db:
        result = db.execute(
            "SELECT id, org_id FROM users WHERE id = ?",
            [str(user_id)],
        ).fetchone()

        if not result:
            # Fall back to Sally
            result = db.execute(
                "SELECT id, org_id FROM users WHERE id = ?",
                [str(SALLY_USER_ID)],
            ).fetchone()

            if not result:
                raise HTTPException(status_code=500, detail="No users found")

        user_id_result = result[0]
        org_id_result = result[1]

        if isinstance(user_id_result, str):
            user_id_result = UUID(user_id_result)
        if isinstance(org_id_result, str):
            org_id_result = UUID(org_id_result)

        return user_id_result, org_id_result


# --- Request/Response Models ---


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    message: str
    session_id: Optional[str] = None
    create_new: bool = False  # Force creation of a new session


class ChatResponse(BaseModel):
    """Response from agent chat."""

    response: str
    session_id: str
    is_complete: bool
    agent_type: str


class SessionResponse(BaseModel):
    """Response for a session."""

    id: str
    idea_id: str
    agent_type: str
    file_type: Optional[str]
    title: Optional[str]
    created_at: str
    last_active: str


class SessionMessageResponse(BaseModel):
    """Response for a session message."""

    id: str
    role: str
    content: str
    created_at: str


class SessionWithMessagesResponse(BaseModel):
    """Response for a session with its messages."""

    session: SessionResponse
    messages: list[SessionMessageResponse]


class SessionsListResponse(BaseModel):
    """Response for list of sessions."""

    sessions: list[SessionResponse]


# --- Routes ---


@router.post("/{idea_id}/kernel/{file_type}/chat")
async def chat_with_agent(
    idea_id: UUID,
    file_type: str,
    request: ChatRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Send a message to the agent for a kernel file."""
    import traceback

    try:
        user_id, org_id = get_current_user_info(crabgrass_dev_user)

        # Verify idea exists and user has access
        idea = idea_concept.get(idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")

        if idea.org_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Validate file type
        valid_types = ["summary", "challenge", "approach", "coherent_steps"]
        if file_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Must be one of: {', '.join(valid_types)}",
            )

        # Get the agent for this file type
        try:
            agent = get_agent_for_file_type(file_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"No agent available for file type: {file_type}. Only 'challenge' is implemented in this slice.",
            )

        # Get or create session
        if request.session_id:
            session = session_concept.get(UUID(request.session_id))
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        elif request.create_new:
            # Force creation of a new session
            session = session_concept.create(
                idea_id=idea_id,
                user_id=user_id,
                agent_type=agent.AGENT_TYPE,
                file_type=file_type,
            )
        else:
            session = session_concept.get_or_create(
                idea_id=idea_id,
                user_id=user_id,
                agent_type=agent.AGENT_TYPE,
                file_type=file_type,
            )

        # Get current file content
        kernel_file = kernel_file_concept.get(idea_id, file_type)
        if not kernel_file:
            raise HTTPException(status_code=404, detail="Kernel file not found")

        # Add user message to session
        session_concept.add_message(session.id, "user", request.message)

        # Get agent response
        response_text = await agent.coach(
            idea_id=idea_id,
            content=kernel_file.content,
            user_message=request.message,
            session_id=session.id,
        )

        # Add agent response to session
        session_concept.add_message(session.id, "agent", response_text)

        logger.info(
            "agent_chat",
            idea_id=str(idea_id),
            file_type=file_type,
            session_id=str(session.id),
            user_id=str(user_id),
        )

        return ChatResponse(
            response=response_text,
            session_id=str(session.id),
            is_complete=kernel_file.is_complete,
            agent_type=agent.AGENT_TYPE,
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error("chat_error", error=error_detail, traceback=traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/{idea_id}/kernel/{file_type}/sessions", response_model=SessionsListResponse)
async def list_sessions(
    idea_id: UUID,
    file_type: str,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """List sessions for a kernel file."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    # Verify idea exists and user has access
    idea = idea_concept.get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if idea.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Map file type to agent type
    agent_type = file_type if file_type != "coherent_steps" else "steps"

    sessions = session_concept.list_for_idea(idea_id, agent_type=agent_type, file_type=file_type)

    return SessionsListResponse(
        sessions=[
            SessionResponse(
                id=str(s.id),
                idea_id=str(s.idea_id),
                agent_type=s.agent_type,
                file_type=s.file_type,
                title=s.title,
                created_at=s.created_at.isoformat(),
                last_active=s.last_active.isoformat(),
            )
            for s in sessions
        ]
    )


@router.get("/{idea_id}/sessions/{session_id}", response_model=SessionWithMessagesResponse)
async def get_session_with_messages(
    idea_id: UUID,
    session_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Get a session with its message history."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    # Verify idea exists and user has access
    idea = idea_concept.get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if idea.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get session
    session = session_concept.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.idea_id != idea_id:
        raise HTTPException(status_code=403, detail="Session does not belong to this idea")

    # Get messages
    messages = session_concept.get_history(session_id)

    return SessionWithMessagesResponse(
        session=SessionResponse(
            id=str(session.id),
            idea_id=str(session.idea_id),
            agent_type=session.agent_type,
            file_type=session.file_type,
            title=session.title,
            created_at=session.created_at.isoformat(),
            last_active=session.last_active.isoformat(),
        ),
        messages=[
            SessionMessageResponse(
                id=str(m.id),
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
    )
