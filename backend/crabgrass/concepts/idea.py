"""Idea concept - the core project container in Crabgrass."""

from dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional
import hashlib

from ..db.connection import get_db


@dataclass
class Idea:
    """State representation of an Idea."""

    id: UUID
    org_id: UUID
    creator_id: UUID
    title: str
    objective_id: Optional[UUID]
    status: str  # 'draft' | 'active' | 'archived'
    kernel_completion: int  # 0-4
    created_at: datetime
    updated_at: datetime


class IdeaConcept:
    """Actions for the Idea concept."""

    def create(
        self,
        org_id: UUID,
        user_id: UUID,
        title: str,
        objective_id: Optional[UUID] = None,
    ) -> Idea:
        """
        Create a new idea.

        Note: Does NOT trigger synchronizations - caller must do that.
        """
        idea_id = uuid4()
        now = datetime.now(timezone.utc)

        with get_db() as db:
            db.execute(
                """
                INSERT INTO ideas (id, org_id, creator_id, title, objective_id, status, kernel_completion, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'draft', 0, ?, ?)
                """,
                [
                    str(idea_id),
                    str(org_id),
                    str(user_id),
                    title,
                    str(objective_id) if objective_id else None,
                    now.isoformat(),
                    now.isoformat(),
                ],
            )

            # Also add creator as owner in collaborators
            db.execute(
                """
                INSERT INTO idea_collaborators (idea_id, user_id, role, added_at)
                VALUES (?, ?, 'owner', ?)
                """,
                [str(idea_id), str(user_id), now.isoformat()],
            )

        return Idea(
            id=idea_id,
            org_id=org_id,
            creator_id=user_id,
            title=title,
            objective_id=objective_id,
            status="draft",
            kernel_completion=0,
            created_at=now,
            updated_at=now,
        )

    def get(self, idea_id: UUID) -> Optional[Idea]:
        """Get idea by ID."""
        with get_db() as db:
            result = db.execute(
                """
                SELECT id, org_id, creator_id, title, objective_id, status,
                       kernel_completion, created_at, updated_at
                FROM ideas
                WHERE id = ?
                """,
                [str(idea_id)],
            ).fetchone()

            if not result:
                return None

            return self._row_to_idea(result)

    def list_for_user(self, org_id: UUID, user_id: UUID) -> list[Idea]:
        """
        List ideas the user has access to.

        Returns ideas where user is creator or collaborator.
        """
        with get_db() as db:
            result = db.execute(
                """
                SELECT DISTINCT i.id, i.org_id, i.creator_id, i.title, i.objective_id,
                       i.status, i.kernel_completion, i.created_at, i.updated_at
                FROM ideas i
                LEFT JOIN idea_collaborators c ON i.id = c.idea_id
                WHERE i.org_id = ?
                  AND i.status != 'archived'
                  AND (i.creator_id = ? OR c.user_id = ?)
                ORDER BY i.updated_at DESC
                """,
                [str(org_id), str(user_id), str(user_id)],
            ).fetchall()

            return [self._row_to_idea(row) for row in result]

    def update(self, idea_id: UUID, **fields) -> Optional[Idea]:
        """Update idea fields."""
        if not fields:
            return self.get(idea_id)

        # Build update query dynamically
        allowed_fields = {"title", "objective_id", "status", "kernel_completion"}
        update_fields = {k: v for k, v in fields.items() if k in allowed_fields}

        if not update_fields:
            return self.get(idea_id)

        # Always update updated_at
        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        values = [
            str(v) if isinstance(v, UUID) else v for v in update_fields.values()
        ]
        values.append(str(idea_id))

        with get_db() as db:
            db.execute(
                f"UPDATE ideas SET {set_clause} WHERE id = ?",
                values,
            )

        return self.get(idea_id)

    def archive(self, idea_id: UUID) -> None:
        """Soft delete by setting status to 'archived'."""
        self.update(idea_id, status="archived")

    def update_kernel_completion(self, idea_id: UUID) -> int:
        """
        Recalculate and update kernel_completion count.

        Returns the new completion count.
        """
        with get_db() as db:
            result = db.execute(
                """
                SELECT COUNT(*) FROM kernel_files
                WHERE idea_id = ? AND is_complete = TRUE
                """,
                [str(idea_id)],
            ).fetchone()

            count = result[0] if result else 0

            db.execute(
                "UPDATE ideas SET kernel_completion = ?, updated_at = ? WHERE id = ?",
                [count, datetime.now(timezone.utc).isoformat(), str(idea_id)],
            )

            return count

    def _row_to_idea(self, row) -> Idea:
        """Convert a database row to an Idea object."""
        (
            id_,
            org_id,
            creator_id,
            title,
            objective_id,
            status,
            kernel_completion,
            created_at,
            updated_at,
        ) = row

        return Idea(
            id=UUID(id_) if isinstance(id_, str) else id_,
            org_id=UUID(org_id) if isinstance(org_id, str) else org_id,
            creator_id=UUID(creator_id) if isinstance(creator_id, str) else creator_id,
            title=title,
            objective_id=(
                UUID(objective_id)
                if objective_id and isinstance(objective_id, str)
                else objective_id
            ),
            status=status,
            kernel_completion=kernel_completion,
            created_at=(
                datetime.fromisoformat(created_at)
                if isinstance(created_at, str)
                else created_at
            ),
            updated_at=(
                datetime.fromisoformat(updated_at)
                if isinstance(updated_at, str)
                else updated_at
            ),
        )
