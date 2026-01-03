"""Server-Sent Events (SSE) for real-time updates."""

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Cookie, HTTPException
from sse_starlette.sse import EventSourceResponse
import structlog

from ..concepts.idea import IdeaConcept
from ..db.connection import get_db
from ..db.migrations import SALLY_USER_ID

logger = structlog.get_logger()

router = APIRouter(tags=["events"])

idea_concept = IdeaConcept()

# In-memory event queues per idea (simple approach for MVP)
# In production, you'd use Redis pub/sub or similar
_idea_subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)


@dataclass
class SSEEvent:
    """An SSE event to send to clients."""

    event_type: str
    data: dict


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
