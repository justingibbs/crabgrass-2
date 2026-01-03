"""Ideas API routes."""

from uuid import UUID
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel
import structlog

from ...concepts.idea import IdeaConcept
from ...concepts.kernel_file import KernelFileConcept
from ...sync.synchronizations import on_idea_created
from ...db.connection import get_db
from ...db.migrations import SALLY_USER_ID

logger = structlog.get_logger()

router = APIRouter(prefix="/api/ideas", tags=["ideas"])

idea_concept = IdeaConcept()
kernel_file_concept = KernelFileConcept()


# --- Request/Response Models ---


class CreateIdeaRequest(BaseModel):
    """Request to create a new idea."""

    title: str = "Untitled Idea"
    objective_id: Optional[str] = None


class UpdateIdeaRequest(BaseModel):
    """Request to update an idea."""

    title: Optional[str] = None
    objective_id: Optional[str] = None


class KernelFileSummary(BaseModel):
    """Summary of a kernel file (without full content)."""

    file_type: str
    is_complete: bool
    updated_at: str


class IdeaResponse(BaseModel):
    """Response for a single idea."""

    id: str
    org_id: str
    creator_id: str
    title: str
    objective_id: Optional[str]
    status: str
    kernel_completion: int
    created_at: str
    updated_at: str
    kernel_files: Optional[list[KernelFileSummary]] = None


class IdeasListResponse(BaseModel):
    """Response for list of ideas."""

    ideas: list[IdeaResponse]


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

        # DuckDB may return UUIDs as UUID objects or strings depending on version
        user_id_result = result[0]
        org_id_result = result[1]

        if isinstance(user_id_result, str):
            user_id_result = UUID(user_id_result)
        if isinstance(org_id_result, str):
            org_id_result = UUID(org_id_result)

        return user_id_result, org_id_result


# --- Routes ---


@router.get("", response_model=IdeasListResponse)
async def list_ideas(
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """List ideas the current user has access to."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    ideas = idea_concept.list_for_user(org_id, user_id)

    return IdeasListResponse(
        ideas=[
            IdeaResponse(
                id=str(idea.id),
                org_id=str(idea.org_id),
                creator_id=str(idea.creator_id),
                title=idea.title,
                objective_id=str(idea.objective_id) if idea.objective_id else None,
                status=idea.status,
                kernel_completion=idea.kernel_completion,
                created_at=idea.created_at.isoformat(),
                updated_at=idea.updated_at.isoformat(),
            )
            for idea in ideas
        ]
    )


@router.post("", response_model=IdeaResponse)
async def create_idea(
    request: CreateIdeaRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Create a new idea."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    objective_id = UUID(request.objective_id) if request.objective_id else None

    # Create the idea
    idea = idea_concept.create(
        org_id=org_id,
        user_id=user_id,
        title=request.title,
        objective_id=objective_id,
    )

    # Trigger synchronizations (initializes kernel files)
    on_idea_created(idea)

    logger.info("idea_created", idea_id=str(idea.id), title=idea.title)

    return IdeaResponse(
        id=str(idea.id),
        org_id=str(idea.org_id),
        creator_id=str(idea.creator_id),
        title=idea.title,
        objective_id=str(idea.objective_id) if idea.objective_id else None,
        status=idea.status,
        kernel_completion=idea.kernel_completion,
        created_at=idea.created_at.isoformat(),
        updated_at=idea.updated_at.isoformat(),
    )


@router.get("/{idea_id}", response_model=IdeaResponse)
async def get_idea(
    idea_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Get an idea by ID with kernel file metadata."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    idea = idea_concept.get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Check access (for now, just check org)
    if idea.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get kernel file summaries
    kernel_files = kernel_file_concept.get_all(idea_id)
    kernel_summaries = [
        KernelFileSummary(
            file_type=kf.file_type,
            is_complete=kf.is_complete,
            updated_at=kf.updated_at.isoformat(),
        )
        for kf in kernel_files
    ]

    return IdeaResponse(
        id=str(idea.id),
        org_id=str(idea.org_id),
        creator_id=str(idea.creator_id),
        title=idea.title,
        objective_id=str(idea.objective_id) if idea.objective_id else None,
        status=idea.status,
        kernel_completion=idea.kernel_completion,
        created_at=idea.created_at.isoformat(),
        updated_at=idea.updated_at.isoformat(),
        kernel_files=kernel_summaries,
    )


@router.patch("/{idea_id}", response_model=IdeaResponse)
async def update_idea(
    idea_id: UUID,
    request: UpdateIdeaRequest,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Update an idea."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    idea = idea_concept.get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if idea.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Build update fields
    update_fields = {}
    if request.title is not None:
        update_fields["title"] = request.title
    if request.objective_id is not None:
        update_fields["objective_id"] = UUID(request.objective_id)

    if update_fields:
        idea = idea_concept.update(idea_id, **update_fields)

    return IdeaResponse(
        id=str(idea.id),
        org_id=str(idea.org_id),
        creator_id=str(idea.creator_id),
        title=idea.title,
        objective_id=str(idea.objective_id) if idea.objective_id else None,
        status=idea.status,
        kernel_completion=idea.kernel_completion,
        created_at=idea.created_at.isoformat(),
        updated_at=idea.updated_at.isoformat(),
    )


@router.delete("/{idea_id}")
async def archive_idea(
    idea_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Archive (soft delete) an idea."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    idea = idea_concept.get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if idea.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    idea_concept.archive(idea_id)

    logger.info("idea_archived", idea_id=str(idea_id))

    return {"status": "archived", "id": str(idea_id)}


# --- Kernel File Routes ---


class KernelFileResponse(BaseModel):
    """Response for a kernel file with content."""

    id: str
    idea_id: str
    file_type: str
    content: str
    is_complete: bool
    updated_at: str


@router.get("/{idea_id}/kernel/{file_type}", response_model=KernelFileResponse)
async def get_kernel_file(
    idea_id: UUID,
    file_type: str,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """Get a kernel file's content."""
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

    # Get the kernel file
    kernel_file = kernel_file_concept.get(idea_id, file_type)
    if not kernel_file:
        raise HTTPException(status_code=404, detail="Kernel file not found")

    return KernelFileResponse(
        id=str(kernel_file.id),
        idea_id=str(kernel_file.idea_id),
        file_type=kernel_file.file_type,
        content=kernel_file.content,
        is_complete=kernel_file.is_complete,
        updated_at=kernel_file.updated_at.isoformat(),
    )
