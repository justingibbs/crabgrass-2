"""Server-Sent Events (SSE) for real-time updates."""

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Optional, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, HTTPException
from sse_starlette.sse import EventSourceResponse
import structlog

from ..concepts.idea import IdeaConcept
from ..concepts.objective import ObjectiveConcept
from ..db.connection import get_db
from ..db.migrations import SALLY_USER_ID

logger = structlog.get_logger()

router = APIRouter(tags=["events"])

idea_concept = IdeaConcept()
objective_concept = ObjectiveConcept()

# In-memory event queues per idea/objective (simple approach for MVP)
# In production, you'd use Redis pub/sub or similar
_idea_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
_objective_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)


@dataclass
class SSEEvent:
    """An SSE event to send to clients."""

    event_type: str
    data: dict


@dataclass
class AgentEdit:
    """An agent edit operation to apply to canvas content.

    Ranges are in markdown character positions (0-indexed).
    """

    edit_id: str
    file_path: str  # e.g., "kernel/challenge", "context/{id}", "objective"
    operation: Literal["insert", "replace", "delete"]
    range: tuple[int, int] | None  # (start, end) in markdown chars; None for append
    content: str  # New content for insert/replace; empty for delete


# --- Helper Functions ---


def get_current_user_info(cookie_value: Optional[str]) -> tuple[UUID, UUID]:
    """Get current user ID and org ID from cookie."""
    user_id = UUID(cookie_value) if cookie_value else SALLY_USER_ID

    with get_db() as db:
        result = db.execute(
            "SELECT id, org_id FROM users WHERE id = ?",
            [str(user_id)],
        ).fetchone()

        if not result:
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


async def subscribe_to_idea(idea_id: str) -> asyncio.Queue:
    """Subscribe to events for an idea."""
    queue = asyncio.Queue()
    _idea_subscribers[idea_id].append(queue)
    logger.info("sse_subscribed", idea_id=idea_id)
    return queue


async def unsubscribe_from_idea(idea_id: str, queue: asyncio.Queue) -> None:
    """Unsubscribe from events for an idea."""
    if idea_id in _idea_subscribers:
        try:
            _idea_subscribers[idea_id].remove(queue)
            if not _idea_subscribers[idea_id]:
                del _idea_subscribers[idea_id]
        except ValueError:
            pass
    logger.info("sse_unsubscribed", idea_id=idea_id)


async def emit_event(idea_id: str, event: SSEEvent) -> None:
    """Emit an event to all subscribers of an idea."""
    subscribers = _idea_subscribers.get(idea_id, [])
    for queue in subscribers:
        await queue.put(event)
    logger.info(
        "sse_event_emitted",
        idea_id=idea_id,
        event_type=event.event_type,
        subscriber_count=len(subscribers),
    )


# --- Objective Subscription Functions ---


async def subscribe_to_objective(objective_id: str) -> asyncio.Queue:
    """Subscribe to events for an objective."""
    queue = asyncio.Queue()
    _objective_subscribers[objective_id].append(queue)
    logger.info("sse_subscribed_objective", objective_id=objective_id)
    return queue


async def unsubscribe_from_objective(objective_id: str, queue: asyncio.Queue) -> None:
    """Unsubscribe from events for an objective."""
    if objective_id in _objective_subscribers:
        try:
            _objective_subscribers[objective_id].remove(queue)
            if not _objective_subscribers[objective_id]:
                del _objective_subscribers[objective_id]
        except ValueError:
            pass
    logger.info("sse_unsubscribed_objective", objective_id=objective_id)


async def emit_objective_event(objective_id: str, event: SSEEvent) -> None:
    """Emit an event to all subscribers of an objective."""
    subscribers = _objective_subscribers.get(objective_id, [])
    for queue in subscribers:
        await queue.put(event)
    logger.info(
        "sse_objective_event_emitted",
        objective_id=objective_id,
        event_type=event.event_type,
        subscriber_count=len(subscribers),
    )


# --- Public API for emitting events ---


async def emit_completion_changed(
    idea_id: UUID,
    file_type: str,
    is_complete: bool,
    total_complete: int,
) -> None:
    """Emit a completion_changed event."""
    event = SSEEvent(
        event_type="completion_changed",
        data={
            "idea_id": str(idea_id),
            "file_type": file_type,
            "is_complete": is_complete,
            "total_complete": total_complete,
        },
    )
    await emit_event(str(idea_id), event)


async def emit_file_saved(
    idea_id: UUID,
    file_type: str,
    version: Optional[str] = None,
) -> None:
    """Emit a file_saved event."""
    from datetime import datetime, timezone

    event = SSEEvent(
        event_type="file_saved",
        data={
            "idea_id": str(idea_id),
            "file_type": file_type,
            "version": version,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await emit_event(str(idea_id), event)


# --- Agent Edit Events ---


def generate_edit_id() -> str:
    """Generate a unique edit ID."""
    return str(uuid4())


async def emit_agent_edit(
    entity_id: UUID,
    entity_type: Literal["idea", "objective"],
    edit: AgentEdit,
) -> None:
    """Emit a complete agent edit event.

    Args:
        entity_id: The idea or objective ID
        entity_type: Whether this is for an idea or objective
        edit: The edit operation to apply
    """
    event = SSEEvent(
        event_type="agent_edit",
        data={
            "edit_id": edit.edit_id,
            "file_path": edit.file_path,
            "operation": edit.operation,
            "range": list(edit.range) if edit.range else None,
            "content": edit.content,
        },
    )

    if entity_type == "idea":
        await emit_event(str(entity_id), event)
    else:
        await emit_objective_event(str(entity_id), event)

    logger.info(
        "agent_edit_emitted",
        entity_id=str(entity_id),
        entity_type=entity_type,
        edit_id=edit.edit_id,
        operation=edit.operation,
    )


async def emit_agent_edit_stream_start(
    entity_id: UUID,
    entity_type: Literal["idea", "objective"],
    edit_id: str,
    file_path: str,
    operation: Literal["insert", "replace", "delete"],
    range: tuple[int, int] | None,
) -> None:
    """Emit the start of a streaming agent edit.

    Args:
        entity_id: The idea or objective ID
        entity_type: Whether this is for an idea or objective
        edit_id: Unique ID for this edit operation
        file_path: The file being edited
        operation: The type of edit operation
        range: The character range being edited (markdown positions)
    """
    event = SSEEvent(
        event_type="agent_edit_stream_start",
        data={
            "edit_id": edit_id,
            "file_path": file_path,
            "operation": operation,
            "range": list(range) if range else None,
        },
    )

    if entity_type == "idea":
        await emit_event(str(entity_id), event)
    else:
        await emit_objective_event(str(entity_id), event)

    logger.info(
        "agent_edit_stream_started",
        entity_id=str(entity_id),
        edit_id=edit_id,
    )


async def emit_agent_edit_stream_chunk(
    entity_id: UUID,
    entity_type: Literal["idea", "objective"],
    edit_id: str,
    content: str,
) -> None:
    """Emit a chunk of streaming content for an agent edit.

    Args:
        entity_id: The idea or objective ID
        entity_type: Whether this is for an idea or objective
        edit_id: The edit ID this chunk belongs to
        content: The content chunk
    """
    event = SSEEvent(
        event_type="agent_edit_stream_chunk",
        data={
            "edit_id": edit_id,
            "content": content,
        },
    )

    if entity_type == "idea":
        await emit_event(str(entity_id), event)
    else:
        await emit_objective_event(str(entity_id), event)


async def emit_agent_edit_stream_end(
    entity_id: UUID,
    entity_type: Literal["idea", "objective"],
    edit_id: str,
    final_content: str,
) -> None:
    """Emit the end of a streaming agent edit.

    Args:
        entity_id: The idea or objective ID
        entity_type: Whether this is for an idea or objective
        edit_id: The edit ID being completed
        final_content: The complete final content
    """
    event = SSEEvent(
        event_type="agent_edit_stream_end",
        data={
            "edit_id": edit_id,
            "final_content": final_content,
        },
    )

    if entity_type == "idea":
        await emit_event(str(entity_id), event)
    else:
        await emit_objective_event(str(entity_id), event)

    logger.info(
        "agent_edit_stream_ended",
        entity_id=str(entity_id),
        edit_id=edit_id,
    )


# --- Routes ---


@router.get("/api/ideas/{idea_id}/events")
async def idea_events(
    idea_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """SSE stream for idea updates."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    # Verify idea exists and user has access
    idea = idea_concept.get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    if idea.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    async def event_generator():
        queue = await subscribe_to_idea(str(idea_id))
        try:
            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps({"idea_id": str(idea_id)}),
            }

            while True:
                try:
                    # Wait for events with a timeout for keepalive
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": event.event_type,
                        "data": json.dumps(event.data),
                    }
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield {"comment": "keepalive"}
        except asyncio.CancelledError:
            await unsubscribe_from_idea(str(idea_id), queue)
            raise

    return EventSourceResponse(event_generator())


@router.get("/api/objectives/{objective_id}/events")
async def objective_events(
    objective_id: UUID,
    crabgrass_dev_user: Optional[str] = Cookie(default=None),
):
    """SSE stream for objective updates."""
    user_id, org_id = get_current_user_info(crabgrass_dev_user)

    # Verify objective exists and user has access
    objective = objective_concept.get(objective_id)
    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    if objective.org_id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    async def event_generator():
        queue = await subscribe_to_objective(str(objective_id))
        try:
            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps({"objective_id": str(objective_id)}),
            }

            while True:
                try:
                    # Wait for events with a timeout for keepalive
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": event.event_type,
                        "data": json.dumps(event.data),
                    }
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield {"comment": "keepalive"}
        except asyncio.CancelledError:
            await unsubscribe_from_objective(str(objective_id), queue)
            raise

    return EventSourceResponse(event_generator())
