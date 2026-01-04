"""Coherence API routes - chat with CoherenceAgent and manage coherence evaluation."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Cookie, HTTPException, BackgroundTasks
from pydantic import BaseModel
import structlog

from ...concepts.idea import IdeaConcept
from ...concepts.session import session_concept
from ...concepts.context_file import context_file_concept
from ...concepts.agents.coherence_agent import coherence_agent
from ...db.connection import get_db
from ...db.migrations import SALLY_USER_ID

logger = structlog.get_logger()

router = APIRouter(prefix="/api/ideas", tags=["coherence"])

idea_concept = IdeaConcept()


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


class CoherenceChatRequest(BaseModel):
    """Request to send a chat message to CoherenceAgent."""

    message: str
    session_id: Optional[str] = None
    create_new: bool = False  # Force creation of a new session


class CoherenceChatResponse(BaseModel):
    """Response from CoherenceAgent chat."""

    response: str
    session_id: str


class CoherenceEvaluateResponse(BaseModel):
    """Response from coherence evaluation."""

    feedback_file_id: Optional[str]
    content: str
    kernel_complete_count: int


# --- Routes ---


@router.post("/{idea_id}/coherence/chat")
async def chat_with_coherence_agent(
    idea_id: UUID,
    request: CoherenceChatRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Chat with the CoherenceAgent about the idea."""
    import traceback

    try:
        user_id, org_id = get_current_user_info(crabgrass_dev_user)

        # Verify idea exists and user has access
        idea = idea_concept.get(idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")

        if idea.org_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied")

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
                agent_type="coherence",
                file_type=None,
            )
        else:
            session = session_concept.get_or_create(
                idea_id=idea_id,
                user_id=user_id,
                agent_type="coherence",
                file_type=None,  # CoherenceAgent is idea-level, no file type
            )

        # Add user message to session
        session_concept.add_message(session.id, "user", request.message)

        # Get agent response
        response_text = await coherence_agent.coach(
            idea_id=idea_id,
            user_message=request.message,
            session_id=session.id,
        )

        # Add agent response to session
        session_concept.add_message(session.id, "agent", response_text)

        logger.info(
            "coherence_chat",
            idea_id=str(idea_id),
            session_id=str(session.id),
            user_id=str(user_id),
        )

        return CoherenceChatResponse(
            response=response_text,
            session_id=str(session.id),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error("coherence_chat_error", error=error_detail, traceback=traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/{idea_id}/coherence/evaluate")
async def evaluate_coherence(
    idea_id: UUID,
    background_tasks: BackgroundTasks,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """
    Manually trigger a coherence evaluation.

    This creates or updates the feedback-tasks.md context file.
    """
    import traceback

    try:
        user_id, org_id = get_current_user_info(crabgrass_dev_user)

        # Verify idea exists and user has access
        idea = idea_concept.get(idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")

        if idea.org_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Run the evaluation
        result = await coherence_agent.evaluate(idea_id)

        # Get the feedback file ID
        feedback_file = context_file_concept.get(idea_id, "feedback-tasks.md")
        feedback_file_id = str(feedback_file.id) if feedback_file else None

        logger.info(
            "coherence_evaluated",
            idea_id=str(idea_id),
            user_id=str(user_id),
        )

        return CoherenceEvaluateResponse(
            feedback_file_id=feedback_file_id,
            content=result.feedback_content,
            kernel_complete_count=result.kernel_complete_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error("coherence_evaluate_error", error=error_detail, traceback=traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/{idea_id}/coherence/sessions")
async def list_coherence_sessions(
    idea_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """List coherence sessions for an idea."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    # Verify idea exists and user has access
    idea = idea_concept.get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if idea.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    sessions = session_concept.list_for_idea(idea_id, agent_type="coherence")

    return {
        "sessions": [
            {
                "id": str(s.id),
                "idea_id": str(s.idea_id),
                "agent_type": s.agent_type,
                "title": s.title,
                "created_at": s.created_at.isoformat(),
                "last_active": s.last_active.isoformat(),
            }
            for s in sessions
        ]
    }
