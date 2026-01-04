"""ObjectiveFile concept - the markdown file for an objective."""

from dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional
import hashlib
import structlog

from ..db.connection import get_db
from ..db.migrations import OBJECTIVE_FILE_TEMPLATE

logger = structlog.get_logger()


@dataclass
class ObjectiveFile:
    """State representation of an ObjectiveFile."""

    id: UUID
    objective_id: UUID
    content: str
    content_hash: Optional[str]
    updated_at: datetime
    updated_by: Optional[UUID]


class ObjectiveFileConcept:
    """Actions for the ObjectiveFile concept."""

    def initialize(self, objective_id: UUID, user_id: UUID) -> ObjectiveFile:
        """
        Initialize the objective file for a new objective.

        Creates it with template content.
        """
        file_id = uuid4()
        now = datetime.now(timezone.utc)
        content = OBJECTIVE_FILE_TEMPLATE
        content_hash = self._hash_content(content)

        with get_db() as db:
            db.execute(
                """
                INSERT INTO objective_files (id, objective_id, content, content_hash, updated_at, updated_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    str(file_id),
                    str(objective_id),
                    content,
                    content_hash,
                    now.isoformat(),
                    str(user_id),
                ],
            )

        logger.info("objective_file_initialized", objective_id=str(objective_id))

        return ObjectiveFile(
            id=file_id,
            objective_id=objective_id,
            content=content,
            content_hash=content_hash,
            updated_at=now,
            updated_by=user_id,
        )

    def get(self, objective_id: UUID) -> Optional[ObjectiveFile]:
        """Get the objective file by objective ID."""
        with get_db() as db:
            result = db.execute(
                """
                SELECT id, objective_id, content, content_hash, updated_at, updated_by
                FROM objective_files
                WHERE objective_id = ?
                """,
                [str(objective_id)],
            ).fetchone()

            if not result:
                return None

            return self._row_to_objective_file(result)

    def update(
        self, objective_id: UUID, content: str, user_id: UUID
    ) -> Optional[ObjectiveFile]:
        """Update the objective file content."""
        now = datetime.now(timezone.utc)
        content_hash = self._hash_content(content)

        with get_db() as db:
            db.execute(
                """
                UPDATE objective_files
                SET content = ?, content_hash = ?, updated_at = ?, updated_by = ?
                WHERE objective_id = ?
                """,
                [
                    content,
                    content_hash,
                    now.isoformat(),
                    str(user_id),
                    str(objective_id),
                ],
            )

        logger.info("objective_file_updated", objective_id=str(objective_id))

        return self.get(objective_id)

    def _hash_content(self, content: str) -> str:
        """Generate a hash of the content for change detection."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _row_to_objective_file(self, row) -> ObjectiveFile:
        """Convert a database row to an ObjectiveFile object."""
        (
            id_,
            objective_id,
            content,
            content_hash,
            updated_at,
            updated_by,
        ) = row

        return ObjectiveFile(
            id=UUID(id_) if isinstance(id_, str) else id_,
            objective_id=UUID(objective_id) if isinstance(objective_id, str) else objective_id,
            content=content or "",
            content_hash=content_hash,
            updated_at=(
                datetime.fromisoformat(updated_at)
                if isinstance(updated_at, str)
                else updated_at
            ),
            updated_by=(
                UUID(updated_by)
                if updated_by and isinstance(updated_by, str)
                else updated_by
            ),
        )
