"""Dev authentication routes for user switching."""

from uuid import UUID
from fastapi import APIRouter, Cookie, HTTPException, Response
from pydantic import BaseModel
import structlog

from ...config import settings
from ...db.connection import get_db
from ...db.migrations import SALLY_USER_ID, get_dev_users

logger = structlog.get_logger()

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserResponse(BaseModel):
    """User response model."""

    id: str
    name: str
    email: str
    role: str
    title: str | None = None


class UsersListResponse(BaseModel):
    """List of available dev users."""

    users: list[UserResponse]


@router.get("/users", response_model=UsersListResponse)
async def list_users():
    """List available dev users for switching."""
    users = get_dev_users()
    return UsersListResponse(users=[UserResponse(**u) for u in users])


@router.post("/switch/{user_id}", response_model=UserResponse)
async def switch_user(user_id: UUID, response: Response):
    """Switch to a different dev user."""
    # Verify user exists
    with get_db() as db:
        result = db.execute(
            "SELECT id, name, email, role, preferences FROM users WHERE id = ?",
            [str(user_id)],
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        user_id_str, name, email, role, preferences = result

        # Parse title from preferences if available
        title = None
        if preferences:
            import json

            prefs = json.loads(preferences) if isinstance(preferences, str) else preferences
            title = prefs.get("title")

    # Set cookie
    response.set_cookie(
        key=settings.dev_user_cookie,
        value=str(user_id),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )

    logger.info("user_switched", user_id=str(user_id), name=name)

    return UserResponse(
        id=str(user_id_str),  # Convert UUID to string
        name=name,
        email=email,
        role=role,
        title=title,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    response: Response,
    crabgrass_dev_user: str | None = Cookie(default=None),
):
    """Get the current authenticated user."""
    # Default to Sally if no cookie set
    user_id = crabgrass_dev_user or str(SALLY_USER_ID)

    with get_db() as db:
        result = db.execute(
            "SELECT id, name, email, role, preferences FROM users WHERE id = ?",
            [user_id],
        ).fetchone()

        if not result:
            # Fall back to Sally if invalid user ID in cookie
            result = db.execute(
                "SELECT id, name, email, role, preferences FROM users WHERE id = ?",
                [str(SALLY_USER_ID)],
            ).fetchone()

            if not result:
                raise HTTPException(status_code=500, detail="No dev users found")

            # Update cookie to valid user
            response.set_cookie(
                key=settings.dev_user_cookie,
                value=str(SALLY_USER_ID),
                httponly=True,
                samesite="lax",
                max_age=60 * 60 * 24 * 30,
            )

        user_id_str, name, email, role, preferences = result

        # Parse title from preferences if available
        title = None
        if preferences:
            import json

            prefs = json.loads(preferences) if isinstance(preferences, str) else preferences
            title = prefs.get("title")

    return UserResponse(
        id=str(user_id_str),  # Convert UUID to string
        name=name,
        email=email,
        role=role,
        title=title,
    )
