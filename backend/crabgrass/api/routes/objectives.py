"""Objectives API routes."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel
import structlog

from ...concepts.objective import ObjectiveConcept
from ...concepts.objective_file import ObjectiveFileConcept
from ...concepts.context_file import context_file_concept
from ...concepts.session import session_concept
from ...concepts.agents import objective_agent
from ...sync.synchronizations import on_objective_created
from ...db.connection import get_db
from ...db.migrations import SALLY_USER_ID
from ..sse import (
    emit_agent_edit,
    AgentEdit,
    generate_edit_id,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/objectives", tags=["objectives"])

objective_concept = ObjectiveConcept()
objective_file_concept = ObjectiveFileConcept()


# --- Request/Response Models ---


class CreateObjectiveRequest(BaseModel):
    """Request to create a new objective."""

    title: str
    description: Optional[str] = None
    timeframe: Optional[str] = None
    owner_id: Optional[str] = None  # Defaults to current user


class UpdateObjectiveRequest(BaseModel):
    """Request to update an objective."""

    title: Optional[str] = None
    description: Optional[str] = None
    timeframe: Optional[str] = None
    owner_id: Optional[str] = None
    status: Optional[str] = None


class ObjectiveResponse(BaseModel):
    """Response for a single objective."""

    id: str
    org_id: str
    title: str
    description: Optional[str]
    owner_id: Optional[str]
    owner_name: Optional[str] = None
    timeframe: Optional[str]
    status: str
    created_at: str
    created_by: Optional[str]
    linked_ideas_count: int = 0


class ObjectivesListResponse(BaseModel):
    """Response for list of objectives."""

    objectives: list[ObjectiveResponse]


class ObjectiveFileResponse(BaseModel):
    """Response for objective file."""

    id: str
    objective_id: str
    content: str
    updated_at: str


class UpdateObjectiveFileRequest(BaseModel):
    """Request to update objective file."""

    content: str


class LinkedIdeaResponse(BaseModel):
    """Response for a linked idea."""

    id: str
    title: str
    status: str
    kernel_completion: int
    creator_id: Optional[str]
    created_at: str
    updated_at: str


class LinkedIdeasResponse(BaseModel):
    """Response for list of linked ideas."""

    ideas: list[LinkedIdeaResponse]


class ChatRequest(BaseModel):
    """Request for chat message."""

    message: str
    session_id: Optional[str] = None
    create_new: bool = False  # Force creation of a new session (note: objective chat always creates new if no session_id)


class ChatResponse(BaseModel):
    """Response for chat."""

    response: str
    session_id: str


class AlignmentResponse(BaseModel):
    """Response for alignment summary."""

    summary: str


class SelectionRange(BaseModel):
    """A text selection range in markdown character positions."""

    start: int
    end: int
    text: str


class SelectionRequest(BaseModel):
    """Request to perform an AI action on selected text."""

    selection: SelectionRange
    instruction: str
    session_id: Optional[str] = None


class SelectionResponse(BaseModel):
    """Response from a selection action."""

    edit_id: str
    session_id: str


# --- Helper Functions ---


def get_current_user_info(cookie_value: Optional[str]) -> tuple[UUID, UUID, str]:
    """
    Get current user ID, org ID, and role from cookie.

    Returns (user_id, org_id, role) tuple.
    Falls back to Sally if no cookie.
    """
    user_id = UUID(cookie_value) if cookie_value else SALLY_USER_ID

    with get_db() as db:
        result = db.execute(
            "SELECT id, org_id, role FROM users WHERE id = ?",
            [str(user_id)],
        ).fetchone()

        if not result:
            # Fall back to Sally
            result = db.execute(
                "SELECT id, org_id, role FROM users WHERE id = ?",
                [str(SALLY_USER_ID)],
            ).fetchone()

            if not result:
                raise HTTPException(status_code=500, detail="No users found")

        user_id_result = result[0]
        org_id_result = result[1]
        role_result = result[2]

        if isinstance(user_id_result, str):
            user_id_result = UUID(user_id_result)
        if isinstance(org_id_result, str):
            org_id_result = UUID(org_id_result)

        return user_id_result, org_id_result, role_result


def require_admin(role: str) -> None:
    """Raise 403 if user is not an admin."""
    if role != "org_admin":
        raise HTTPException(
            status_code=403,
            detail="Only organization admins can perform this action",
        )


def get_user_name(user_id: Optional[UUID]) -> Optional[str]:
    """Get user name by ID."""
    if not user_id:
        return None
    with get_db() as db:
        result = db.execute(
            "SELECT name FROM users WHERE id = ?",
            [str(user_id)],
        ).fetchone()
        return result[0] if result else None


# --- Routes ---


@router.get("", response_model=ObjectivesListResponse)
async def list_objectives(
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """List all objectives for the organization."""
    user_id, org_id, role = get_current_user_info(crabgrass_dev_user)

    objectives = objective_concept.list(org_id)

    return ObjectivesListResponse(
        objectives=[
            ObjectiveResponse(
                id=str(obj.id),
                org_id=str(obj.org_id),
                title=obj.title,
                description=obj.description,
                owner_id=str(obj.owner_id) if obj.owner_id else None,
                owner_name=get_user_name(obj.owner_id),
                timeframe=obj.timeframe,
                status=obj.status,
                created_at=obj.created_at.isoformat(),
                created_by=str(obj.created_by) if obj.created_by else None,
                linked_ideas_count=objective_concept.get_ideas_count(obj.id),
            )
            for obj in objectives
        ]
    )


@router.post("", response_model=ObjectiveResponse)
async def create_objective(
    request: CreateObjectiveRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Create a new objective. Admin only."""
    user_id, org_id, role = get_current_user_info(crabgrass_dev_user)
    require_admin(role)

    owner_id = UUID(request.owner_id) if request.owner_id else user_id

    # Create the objective
    objective = objective_concept.create(
        org_id=org_id,
        title=request.title,
        owner_id=owner_id,
        created_by=user_id,
        description=request.description,
        timeframe=request.timeframe,
    )

    # Trigger synchronizations (initializes objective file)
    on_objective_created(objective, user_id)

    logger.info("objective_created", objective_id=str(objective.id), title=objective.title)

    return ObjectiveResponse(
        id=str(objective.id),
        org_id=str(objective.org_id),
        title=objective.title,
        description=objective.description,
        owner_id=str(objective.owner_id) if objective.owner_id else None,
        owner_name=get_user_name(objective.owner_id),
        timeframe=objective.timeframe,
        status=objective.status,
        created_at=objective.created_at.isoformat(),
        created_by=str(objective.created_by) if objective.created_by else None,
        linked_ideas_count=0,
    )


@router.get("/{objective_id}", response_model=ObjectiveResponse)
async def get_objective(
    objective_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Get an objective by ID."""
    user_id, org_id, role = get_current_user_info(crabgrass_dev_user)

    objective = objective_concept.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    if objective.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return ObjectiveResponse(
        id=str(objective.id),
        org_id=str(objective.org_id),
        title=objective.title,
        description=objective.description,
        owner_id=str(objective.owner_id) if objective.owner_id else None,
        owner_name=get_user_name(objective.owner_id),
        timeframe=objective.timeframe,
        status=objective.status,
        created_at=objective.created_at.isoformat(),
        created_by=str(objective.created_by) if objective.created_by else None,
        linked_ideas_count=objective_concept.get_ideas_count(objective_id),
    )


@router.patch("/{objective_id}", response_model=ObjectiveResponse)
async def update_objective(
    objective_id: UUID,
    request: UpdateObjectiveRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Update an objective. Admin only."""
    user_id, org_id, role = get_current_user_info(crabgrass_dev_user)
    require_admin(role)

    objective = objective_concept.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    if objective.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Build update fields
    update_fields = {}
    if request.title is not None:
        update_fields["title"] = request.title
    if request.description is not None:
        update_fields["description"] = request.description
    if request.timeframe is not None:
        update_fields["timeframe"] = request.timeframe
    if request.owner_id is not None:
        update_fields["owner_id"] = UUID(request.owner_id)
    if request.status is not None:
        update_fields["status"] = request.status

    if update_fields:
        objective = objective_concept.update(objective_id, **update_fields)

    return ObjectiveResponse(
        id=str(objective.id),
        org_id=str(objective.org_id),
        title=objective.title,
        description=objective.description,
        owner_id=str(objective.owner_id) if objective.owner_id else None,
        owner_name=get_user_name(objective.owner_id),
        timeframe=objective.timeframe,
        status=objective.status,
        created_at=objective.created_at.isoformat(),
        created_by=str(objective.created_by) if objective.created_by else None,
        linked_ideas_count=objective_concept.get_ideas_count(objective_id),
    )


@router.delete("/{objective_id}")
async def archive_objective(
    objective_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Archive (soft delete) an objective. Admin only."""
    user_id, org_id, role = get_current_user_info(crabgrass_dev_user)
    require_admin(role)

    objective = objective_concept.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    if objective.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    objective_concept.archive(objective_id)

    logger.info("objective_archived", objective_id=str(objective_id))

    return {"status": "archived", "id": str(objective_id)}


# --- Linked Ideas ---


@router.get("/{objective_id}/ideas", response_model=LinkedIdeasResponse)
async def get_linked_ideas(
    objective_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Get ideas linked to this objective."""
    user_id, org_id, role = get_current_user_info(crabgrass_dev_user)

    objective = objective_concept.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    if objective.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    ideas = objective_concept.get_ideas(objective_id)

    return LinkedIdeasResponse(
        ideas=[
            LinkedIdeaResponse(
                id=idea["id"],
                title=idea["title"],
                status=idea["status"],
                kernel_completion=idea["kernel_completion"],
                creator_id=idea.get("creator_id"),
                created_at=idea["created_at"],
                updated_at=idea["updated_at"],
            )
            for idea in ideas
        ]
    )


# --- Objective File ---


@router.get("/{objective_id}/file", response_model=ObjectiveFileResponse)
async def get_objective_file(
    objective_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Get the objective file content."""
    user_id, org_id, role = get_current_user_info(crabgrass_dev_user)

    objective = objective_concept.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    if objective.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    obj_file = objective_file_concept.get(objective_id)
    if not obj_file:
        raise HTTPException(status_code=404, detail="Objective file not found")

    return ObjectiveFileResponse(
        id=str(obj_file.id),
        objective_id=str(obj_file.objective_id),
        content=obj_file.content,
        updated_at=obj_file.updated_at.isoformat(),
    )


@router.put("/{objective_id}/file", response_model=ObjectiveFileResponse)
async def update_objective_file(
    objective_id: UUID,
    request: UpdateObjectiveFileRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Update the objective file content. Admin only."""
    user_id, org_id, role = get_current_user_info(crabgrass_dev_user)
    require_admin(role)

    objective = objective_concept.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    if objective.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    obj_file = objective_file_concept.update(objective_id, request.content, user_id)
    if not obj_file:
        raise HTTPException(status_code=404, detail="Objective file not found")

    logger.info("objective_file_updated", objective_id=str(objective_id))

    return ObjectiveFileResponse(
        id=str(obj_file.id),
        objective_id=str(obj_file.objective_id),
        content=obj_file.content,
        updated_at=obj_file.updated_at.isoformat(),
    )


# --- Agent Chat ---


@router.post("/{objective_id}/chat", response_model=ChatResponse)
async def chat_with_agent(
    objective_id: UUID,
    request: ChatRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Chat with the ObjectiveAgent."""
    user_id, org_id, role = get_current_user_info(crabgrass_dev_user)

    objective = objective_concept.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    if objective.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get or create session
    if request.session_id:
        session_id = UUID(request.session_id)
        session = session_concept.get(session_id)
        if not session or session.objective_id != objective_id:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = session_concept.create_for_objective(
            objective_id=objective_id,
            user_id=user_id,
            agent_type="objective",
        )
        session_id = session.id

    # Save user message
    session_concept.add_message(session_id, "user", request.message)

    # Get agent response
    response = await objective_agent.coach(
        objective_id=objective_id,
        user_message=request.message,
        session_id=session_id,
    )

    # Save agent response
    session_concept.add_message(session_id, "agent", response)

    return ChatResponse(
        response=response,
        session_id=str(session_id),
    )


@router.get("/{objective_id}/alignment", response_model=AlignmentResponse)
async def get_alignment_summary(
    objective_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Get a summary of how linked ideas align with this objective."""
    user_id, org_id, role = get_current_user_info(crabgrass_dev_user)

    objective = objective_concept.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    if objective.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    summary = await objective_agent.summarize_alignment(objective_id)

    return AlignmentResponse(summary=summary)


# --- Sessions ---


class SessionSummary(BaseModel):
    """Summary of a session."""

    id: str
    title: Optional[str]
    created_at: str
    last_active: str


class SessionsListResponse(BaseModel):
    """Response for list of sessions."""

    sessions: list[SessionSummary]


@router.get("/{objective_id}/sessions", response_model=SessionsListResponse)
async def list_sessions(
    objective_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """List chat sessions for this objective."""
    user_id, org_id, role = get_current_user_info(crabgrass_dev_user)

    objective = objective_concept.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    if objective.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    sessions = session_concept.list_for_objective(objective_id)

    return SessionsListResponse(
        sessions=[
            SessionSummary(
                id=str(s.id),
                title=s.title,
                created_at=s.created_at.isoformat(),
                last_active=s.last_active.isoformat(),
            )
            for s in sessions
        ]
    )


# --- Selection Actions ---


@router.post("/{objective_id}/selection-action", response_model=SelectionResponse)
async def objective_file_selection_action(
    objective_id: UUID,
    request: SelectionRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Perform an AI action on selected text in an objective file.

    The ObjectiveAgent will process the selection with the given instruction and emit
    an agent_edit SSE event with the result. Admin only.
    """
    import traceback

    try:
        user_id, org_id, role = get_current_user_info(crabgrass_dev_user)
        require_admin(role)

        # Verify objective exists and user has access
        objective = objective_concept.get(objective_id)
        if not objective:
            raise HTTPException(status_code=404, detail="Objective not found")

        if objective.org_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Get objective file content
        obj_file = objective_file_concept.get(objective_id)
        if not obj_file:
            raise HTTPException(status_code=404, detail="Objective file not found")

        # Find the actual position of the selected text in the stored content
        stored_content = obj_file.content
        selection_text = request.selection.text

        actual_start = stored_content.find(selection_text)
        if actual_start == -1:
            normalized_selection = ' '.join(selection_text.split())
            normalized_content = ' '.join(stored_content.split())
            normalized_start = normalized_content.find(normalized_selection)

            if normalized_start == -1:
                raise HTTPException(
                    status_code=400,
                    detail="Could not locate selected text in the file. The file may have been modified."
                )

            actual_start = 0
            norm_pos = 0
            while norm_pos < normalized_start and actual_start < len(stored_content):
                if stored_content[actual_start].isspace():
                    while actual_start < len(stored_content) and stored_content[actual_start].isspace():
                        actual_start += 1
                    norm_pos += 1
                else:
                    actual_start += 1
                    norm_pos += 1

        actual_end = actual_start + len(selection_text)

        # Expand selection to include list markers at the beginning of the line
        # This handles cases where user selects "Why now" but the markdown has "1.  Why now"
        import re
        line_start = stored_content.rfind('\n', 0, actual_start)
        line_start = 0 if line_start == -1 else line_start + 1
        prefix = stored_content[line_start:actual_start]
        # Check if prefix is a list marker (numbered or bullet)
        if re.match(r'^(\d+\.\s+|\*\s+|-\s+|\+\s+)$', prefix):
            actual_start = line_start

        found_text = stored_content[actual_start:actual_end]
        if found_text != selection_text:
            remaining = stored_content[actual_start:]
            for end_offset in range(len(selection_text), len(remaining) + 1):
                candidate = remaining[:end_offset]
                if ' '.join(candidate.split()) == ' '.join(selection_text.split()):
                    actual_end = actual_start + end_offset
                    break

        # Get or create session
        if request.session_id:
            session_id = UUID(request.session_id)
            session = session_concept.get(session_id)
            if not session or session.objective_id != objective_id:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            session = session_concept.create_for_objective(
                objective_id=objective_id,
                user_id=user_id,
                agent_type="objective",
            )
            session_id = session.id

        # Generate edit ID
        edit_id = generate_edit_id()

        # Build the prompt for the agent to process the selection
        selection_prompt = f"""The user has selected the following text and wants you to modify it:

SELECTED TEXT:
\"\"\"{selection_text}\"\"\"

USER INSTRUCTION: {request.instruction}

FULL DOCUMENT CONTEXT:
```markdown
{stored_content}
```

Please provide ONLY the replacement text for the selection. Do not include any explanation or markdown code blocks - just the raw replacement text that should replace the selected text."""

        # Add to session history
        session_concept.add_message(
            session_id,
            "user",
            f"[Selection Action] {request.instruction}\n\nSelected: \"{request.selection.text}\""
        )

        # Get agent response (the replacement text)
        replacement_text = await objective_agent.coach(
            objective_id=objective_id,
            user_message=selection_prompt,
            session_id=session_id,
        )

        # Clean up the response - remove any markdown code blocks if present
        replacement_text = replacement_text.strip()
        if replacement_text.startswith("```") and replacement_text.endswith("```"):
            lines = replacement_text.split("\n")
            replacement_text = "\n".join(lines[1:-1])

        # Add agent response to session
        session_concept.add_message(
            session_id,
            "agent",
            f"[Selection Edit] Replaced with: \"{replacement_text}\""
        )

        # Create and emit the edit event using recalculated positions
        edit = AgentEdit(
            edit_id=edit_id,
            file_path="objective",
            operation="replace",
            range=(actual_start, actual_end),
            content=replacement_text,
        )

        await emit_agent_edit(objective_id, "objective", edit)

        logger.info(
            "objective_file_selection_action_completed",
            objective_id=str(objective_id),
            edit_id=edit_id,
            session_id=str(session_id),
        )

        return SelectionResponse(
            edit_id=edit_id,
            session_id=str(session_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error("objective_file_selection_action_error", error=error_detail, traceback=traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_detail)
