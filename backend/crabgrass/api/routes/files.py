"""Context file API routes - CRUD operations and ContextAgent chat."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel
import structlog

from ...concepts.idea import IdeaConcept
from ...concepts.context_file import context_file_concept
from ...concepts.session import session_concept
from ...concepts.agents.context_agent import context_agent
from ...db.connection import get_db
from ...db.migrations import SALLY_USER_ID
from ...sync.synchronizations import on_context_file_created_async

logger = structlog.get_logger()

router = APIRouter(prefix="/api/ideas", tags=["files"])

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


class CreateContextFileRequest(BaseModel):
    """Request to create a context file."""

    filename: str
    content: str = ""


class UpdateContextFileRequest(BaseModel):
    """Request to update a context file."""

    content: str


class ContextFileChatRequest(BaseModel):
    """Request to send a chat message to ContextAgent."""

    message: str
    session_id: Optional[str] = None


class ContextFileResponse(BaseModel):
    """Response for a context file."""

    id: str
    filename: str
    size_bytes: int
    created_by_agent: bool
    created_at: str
    updated_at: str


class ContextFileDetailResponse(BaseModel):
    """Response for a single context file with content."""

    id: str
    filename: str
    content: str
    size_bytes: int
    created_by_agent: bool
    created_at: str
    updated_at: str


class ContextFilesListResponse(BaseModel):
    """Response for list of context files."""

    files: list[ContextFileResponse]


class ContextFileChatResponse(BaseModel):
    """Response from ContextAgent chat."""

    response: str
    session_id: str


# --- Routes ---


@router.get("/{idea_id}/context")
async def list_context_files(
    idea_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """List all context files for an idea."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    # Verify idea exists and user has access
    idea = idea_concept.get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if idea.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get context files
    files = context_file_concept.list(idea_id)

    return ContextFilesListResponse(
        files=[
            ContextFileResponse(
                id=str(f.id),
                filename=f.filename,
                size_bytes=f.size_bytes,
                created_by_agent=f.created_by_agent,
                created_at=f.created_at.isoformat(),
                updated_at=f.updated_at.isoformat(),
            )
            for f in files
        ]
    )


@router.post("/{idea_id}/context")
async def create_context_file(
    idea_id: UUID,
    request: CreateContextFileRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Create a new context file."""
    import traceback

    try:
        user_id, org_id = get_current_user_info(crabgrass_dev_user)

        # Verify idea exists and user has access
        idea = idea_concept.get(idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")

        if idea.org_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if file already exists
        existing = context_file_concept.get(idea_id, request.filename)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"File '{request.filename}' already exists"
            )

        # Create the context file
        try:
            context_file = context_file_concept.create(
                idea_id=idea_id,
                filename=request.filename,
                content=request.content,
                user_id=user_id,
                created_by_agent=False,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Trigger synchronization (extract insights)
        await on_context_file_created_async(idea_id, context_file.id, user_id)

        logger.info(
            "context_file_created_via_api",
            idea_id=str(idea_id),
            file_id=str(context_file.id),
            filename=request.filename,
            user_id=str(user_id),
        )

        return ContextFileDetailResponse(
            id=str(context_file.id),
            filename=context_file.filename,
            content=context_file.content,
            size_bytes=context_file.size_bytes,
            created_by_agent=context_file.created_by_agent,
            created_at=context_file.created_at.isoformat(),
            updated_at=context_file.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error("create_context_file_error", error=error_detail, traceback=traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/{idea_id}/context/{file_id}")
async def get_context_file(
    idea_id: UUID,
    file_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Get a single context file with content."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    # Verify idea exists and user has access
    idea = idea_concept.get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if idea.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get context file by ID
    file = context_file_concept.get_by_id(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="Context file not found")

    # Verify file belongs to the idea
    if file.idea_id != idea_id:
        raise HTTPException(status_code=404, detail="Context file not found")

    return ContextFileDetailResponse(
        id=str(file.id),
        filename=file.filename,
        content=file.content,
        size_bytes=file.size_bytes,
        created_by_agent=file.created_by_agent,
        created_at=file.created_at.isoformat(),
        updated_at=file.updated_at.isoformat(),
    )


@router.put("/{idea_id}/context/{file_id}")
async def update_context_file(
    idea_id: UUID,
    file_id: UUID,
    request: UpdateContextFileRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Update a context file's content."""
    import traceback

    try:
        user_id, org_id = get_current_user_info(crabgrass_dev_user)

        # Verify idea exists and user has access
        idea = idea_concept.get(idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")

        if idea.org_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get context file by ID to get filename
        file = context_file_concept.get_by_id(file_id)
        if not file:
            raise HTTPException(status_code=404, detail="Context file not found")

        # Verify file belongs to the idea
        if file.idea_id != idea_id:
            raise HTTPException(status_code=404, detail="Context file not found")

        # Update the file
        try:
            updated_file = context_file_concept.update(
                idea_id=idea_id,
                filename=file.filename,
                content=request.content,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not updated_file:
            raise HTTPException(status_code=404, detail="Context file not found")

        logger.info(
            "context_file_updated_via_api",
            idea_id=str(idea_id),
            file_id=str(file_id),
            filename=file.filename,
            user_id=str(user_id),
        )

        return ContextFileDetailResponse(
            id=str(updated_file.id),
            filename=updated_file.filename,
            content=updated_file.content,
            size_bytes=updated_file.size_bytes,
            created_by_agent=updated_file.created_by_agent,
            created_at=updated_file.created_at.isoformat(),
            updated_at=updated_file.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error("update_context_file_error", error=error_detail, traceback=traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@router.delete("/{idea_id}/context/{file_id}")
async def delete_context_file(
    idea_id: UUID,
    file_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Delete a context file."""
    import traceback

    try:
        user_id, org_id = get_current_user_info(crabgrass_dev_user)

        # Verify idea exists and user has access
        idea = idea_concept.get(idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")

        if idea.org_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete the file
        deleted = context_file_concept.delete(idea_id, file_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Context file not found")

        logger.info(
            "context_file_deleted_via_api",
            idea_id=str(idea_id),
            file_id=str(file_id),
            user_id=str(user_id),
        )

        return {"success": True, "message": "Context file deleted"}

    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error("delete_context_file_error", error=error_detail, traceback=traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/{idea_id}/context/{file_id}/chat")
async def chat_with_context_agent(
    idea_id: UUID,
    file_id: UUID,
    request: ContextFileChatRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Chat with the ContextAgent about a specific context file."""
    import traceback

    try:
        user_id, org_id = get_current_user_info(crabgrass_dev_user)

        # Verify idea exists and user has access
        idea = idea_concept.get(idea_id)
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")

        if idea.org_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Verify context file exists and belongs to idea
        file = context_file_concept.get_by_id(file_id)
        if not file or file.idea_id != idea_id:
            raise HTTPException(status_code=404, detail="Context file not found")

        # Get or create session
        if request.session_id:
            session = session_concept.get(UUID(request.session_id))
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            # Create session with context file ID in title for reference
            session = session_concept.get_or_create(
                idea_id=idea_id,
                user_id=user_id,
                agent_type="context",
                file_type=None,  # Context files don't have a file_type
            )
            # Update session title to include filename
            session_concept.update_title(session.id, f"Context: {file.filename}")

        # Add user message to session
        session_concept.add_message(session.id, "user", request.message)

        # Get agent response
        response_text = await context_agent.coach(
            idea_id=idea_id,
            context_file_id=file_id,
            user_message=request.message,
            session_id=session.id,
        )

        # Add agent response to session
        session_concept.add_message(session.id, "agent", response_text)

        logger.info(
            "context_agent_chat",
            idea_id=str(idea_id),
            file_id=str(file_id),
            session_id=str(session.id),
            user_id=str(user_id),
        )

        return ContextFileChatResponse(
            response=response_text,
            session_id=str(session.id),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error("context_agent_chat_error", error=error_detail, traceback=traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)
