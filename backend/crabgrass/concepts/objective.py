"""Objective concept - org-wide strategic goals that ideas connect to."""

from dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional, List, Dict
import structlog

from ..db.connection import get_db

logger = structlog.get_logger()


@dataclass
class Objective:
    """State representation of an Objective."""

    id: UUID
    org_id: UUID
    title: str
    description: Optional[str]
    owner_id: Optional[UUID]
    timeframe: Optional[str]  # e.g., 'Q1 2025', 'FY25', 'H1 2025'
    status: str  # 'active' | 'achieved' | 'deprecated'
    created_at: datetime
    created_by: Optional[UUID]


class ObjectiveConcept:
    """Actions for the Objective concept."""

    def create(
        self,
        org_id: UUID,
        title: str,
        owner_id: UUID,
        created_by: UUID,
        description: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> Objective:
        """
        Create a new objective.

        Only org_admins should call this (enforced at API layer).
        Note: Does NOT trigger synchronizations - caller must do that.
        """
        objective_id = uuid4()
        now = datetime.now(timezone.utc)

        with get_db() as db:
            db.execute(
                """
                INSERT INTO objectives (id, org_id, title, description, owner_id, timeframe, status, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                [
                    str(objective_id),
                    str(org_id),
                    title,
                    description,
                    str(owner_id) if owner_id else None,
                    timeframe,
                    now.isoformat(),
                    str(created_by),
                ],
            )

        logger.info("objective_created", objective_id=str(objective_id), title=title)

        return Objective(
            id=objective_id,
            org_id=org_id,
            title=title,
            description=description,
            owner_id=owner_id,
            timeframe=timeframe,
            status="active",
            created_at=now,
            created_by=created_by,
        )

    def get(self, objective_id: UUID) -> Optional[Objective]:
        """Get objective by ID."""
        with get_db() as db:
            result = db.execute(
                """
                SELECT id, org_id, title, description, owner_id, timeframe,
                       status, created_at, created_by
                FROM objectives
                WHERE id = ?
                """,
                [str(objective_id)],
            ).fetchone()

            if not result:
                return None

            return self._row_to_objective(result)

    def list(self, org_id: UUID) -> List[Objective]:
        """
        List all objectives for an organization.

        All org members can view objectives.
        """
        with get_db() as db:
            result = db.execute(
                """
                SELECT id, org_id, title, description, owner_id, timeframe,
                       status, created_at, created_by
                FROM objectives
                WHERE org_id = ?
                  AND status != 'deprecated'
                ORDER BY created_at DESC
                """,
                [str(org_id)],
            ).fetchall()

            return [self._row_to_objective(row) for row in result]

    def update(self, objective_id: UUID, **fields) -> Optional[Objective]:
        """
        Update objective fields.

        Only org_admins should call this (enforced at API layer).
        """
        if not fields:
            return self.get(objective_id)

        # Build update query dynamically
        allowed_fields = {"title", "description", "owner_id", "timeframe", "status"}
        update_fields = {k: v for k, v in fields.items() if k in allowed_fields}

        if not update_fields:
            return self.get(objective_id)

        set_clause = ", ".join(f"{k} = ?" for k in update_fields)
        values = [
            str(v) if isinstance(v, UUID) else v for v in update_fields.values()
        ]
        values.append(str(objective_id))

        with get_db() as db:
            db.execute(
                f"UPDATE objectives SET {set_clause} WHERE id = ?",
                values,
            )

        logger.info("objective_updated", objective_id=str(objective_id), fields=list(update_fields.keys()))

        return self.get(objective_id)

    def archive(self, objective_id: UUID) -> None:
        """
        Archive (soft delete) by setting status to 'deprecated'.

        Only org_admins should call this (enforced at API layer).
        """
        self.update(objective_id, status="deprecated")
        logger.info("objective_archived", objective_id=str(objective_id))

    def get_ideas(self, objective_id: UUID) -> List[Dict]:
        """
        Get ideas linked to this objective.

        Returns list of idea dicts with basic info.
        Uses idea_objective_links table for graph-based query.
        """
        with get_db() as db:
            # First try to get from graph links table
            result = db.execute(
                """
                SELECT i.id, i.title, i.status, i.kernel_completion,
                       i.creator_id, i.created_at, i.updated_at
                FROM ideas i
                INNER JOIN idea_objective_links l ON i.id = l.idea_id
                WHERE l.objective_id = ?
                  AND i.status != 'archived'
                ORDER BY i.updated_at DESC
                """,
                [str(objective_id)],
            ).fetchall()

            return [
                {
                    "id": str(row[0]) if not isinstance(row[0], str) else row[0],
                    "title": row[1],
                    "status": row[2],
                    "kernel_completion": row[3],
                    "creator_id": str(row[4]) if row[4] and not isinstance(row[4], str) else row[4],
                    "created_at": row[5].isoformat() if hasattr(row[5], 'isoformat') else row[5],
                    "updated_at": row[6].isoformat() if hasattr(row[6], 'isoformat') else row[6],
                }
                for row in result
            ]

    def get_ideas_count(self, objective_id: UUID) -> int:
        """Get count of ideas linked to this objective."""
        with get_db() as db:
            result = db.execute(
                """
                SELECT COUNT(*)
                FROM idea_objective_links l
                INNER JOIN ideas i ON l.idea_id = i.id
                WHERE l.objective_id = ?
                  AND i.status != 'archived'
                """,
                [str(objective_id)],
            ).fetchone()

            return result[0] if result else 0

    def _row_to_objective(self, row) -> Objective:
        """Convert a database row to an Objective object."""
        (
            id_,
            org_id,
            title,
            description,
            owner_id,
            timeframe,
            status,
            created_at,
            created_by,
        ) = row

        return Objective(
            id=UUID(id_) if isinstance(id_, str) else id_,
            org_id=UUID(org_id) if isinstance(org_id, str) else org_id,
            title=title,
            description=description,
            owner_id=(
                UUID(owner_id)
                if owner_id and isinstance(owner_id, str)
                else owner_id
            ),
            timeframe=timeframe,
            status=status,
            created_at=(
                datetime.fromisoformat(created_at)
                if isinstance(created_at, str)
                else created_at
            ),
            created_by=(
                UUID(created_by)
                if created_by and isinstance(created_by, str)
                else created_by
            ),
        )
