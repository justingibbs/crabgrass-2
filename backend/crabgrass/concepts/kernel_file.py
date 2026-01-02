"""KernelFile concept - the four required structured files for an idea."""

from dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional
import hashlib

from ..db.connection import get_db
from ..db.migrations import KERNEL_FILE_TYPES, KERNEL_FILE_TEMPLATES


@dataclass
class KernelFile:
    """State representation of a KernelFile."""

    id: UUID
    idea_id: UUID
    file_type: str  # 'summary' | 'challenge' | 'approach' | 'coherent_steps'
    content: str
    content_hash: Optional[str]
    is_complete: bool
    updated_at: datetime
    updated_by: Optional[UUID]


class KernelFileConcept:
    """Actions for the KernelFile concept."""

    def initialize_all(self, idea_id: UUID, user_id: UUID) -> list[KernelFile]:
        """
        Initialize all 4 kernel files for a new idea.

        Creates them with template content.
        """
        now = datetime.now(timezone.utc)
        files = []

        with get_db() as db:
            for file_type in KERNEL_FILE_TYPES:
                file_id = uuid4()
                content = KERNEL_FILE_TEMPLATES[file_type]
                content_hash = self._hash_content(content)

                db.execute(
                    """
                    INSERT INTO kernel_files (id, idea_id, file_type, content, content_hash, is_complete, updated_at, updated_by)
                    VALUES (?, ?, ?, ?, ?, FALSE, ?, ?)
                    """,
                    [
                        str(file_id),
                        str(idea_id),
                        file_type,
                        content,
                        content_hash,
                        now.isoformat(),
                        str(user_id),
                    ],
                )

                files.append(
                    KernelFile(
                        id=file_id,
                        idea_id=idea_id,
                        file_type=file_type,
                        content=content,
                        content_hash=content_hash,
                        is_complete=False,
                        updated_at=now,
                        updated_by=user_id,
                    )
                )

        return files

    def get(self, idea_id: UUID, file_type: str) -> Optional[KernelFile]:
        """Get a kernel file by idea ID and type."""
        with get_db() as db:
            result = db.execute(
                """
                SELECT id, idea_id, file_type, content, content_hash, is_complete, updated_at, updated_by
                FROM kernel_files
                WHERE idea_id = ? AND file_type = ?
                """,
                [str(idea_id), file_type],
            ).fetchone()

            if not result:
                return None

            return self._row_to_kernel_file(result)

    def get_all(self, idea_id: UUID) -> list[KernelFile]:
        """Get all kernel files for an idea."""
        with get_db() as db:
            result = db.execute(
                """
                SELECT id, idea_id, file_type, content, content_hash, is_complete, updated_at, updated_by
                FROM kernel_files
                WHERE idea_id = ?
                ORDER BY
                    CASE file_type
                        WHEN 'summary' THEN 1
                        WHEN 'challenge' THEN 2
                        WHEN 'approach' THEN 3
                        WHEN 'coherent_steps' THEN 4
                    END
                """,
                [str(idea_id)],
            ).fetchall()

            return [self._row_to_kernel_file(row) for row in result]

    def update(
        self, idea_id: UUID, file_type: str, content: str, user_id: UUID
    ) -> Optional[KernelFile]:
        """Update kernel file content."""
        now = datetime.now(timezone.utc)
        content_hash = self._hash_content(content)

        with get_db() as db:
            db.execute(
                """
                UPDATE kernel_files
                SET content = ?, content_hash = ?, updated_at = ?, updated_by = ?
                WHERE idea_id = ? AND file_type = ?
                """,
                [
                    content,
                    content_hash,
                    now.isoformat(),
                    str(user_id),
                    str(idea_id),
                    file_type,
                ],
            )

        return self.get(idea_id, file_type)

    def mark_complete(self, idea_id: UUID, file_type: str) -> Optional[KernelFile]:
        """Mark a kernel file as complete."""
        now = datetime.now(timezone.utc)

        with get_db() as db:
            db.execute(
                """
                UPDATE kernel_files
                SET is_complete = TRUE, updated_at = ?
                WHERE idea_id = ? AND file_type = ?
                """,
                [now.isoformat(), str(idea_id), file_type],
            )

        return self.get(idea_id, file_type)

    def mark_incomplete(self, idea_id: UUID, file_type: str) -> Optional[KernelFile]:
        """Mark a kernel file as incomplete."""
        now = datetime.now(timezone.utc)

        with get_db() as db:
            db.execute(
                """
                UPDATE kernel_files
                SET is_complete = FALSE, updated_at = ?
                WHERE idea_id = ? AND file_type = ?
                """,
                [now.isoformat(), str(idea_id), file_type],
            )

        return self.get(idea_id, file_type)

    def get_completion_count(self, idea_id: UUID) -> int:
        """Get the count of completed kernel files for an idea."""
        with get_db() as db:
            result = db.execute(
                """
                SELECT COUNT(*) FROM kernel_files
                WHERE idea_id = ? AND is_complete = TRUE
                """,
                [str(idea_id)],
            ).fetchone()

            return result[0] if result else 0

    def _hash_content(self, content: str) -> str:
        """Generate a hash of the content for change detection."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _row_to_kernel_file(self, row) -> KernelFile:
        """Convert a database row to a KernelFile object."""
        (
            id_,
            idea_id,
            file_type,
            content,
            content_hash,
            is_complete,
            updated_at,
            updated_by,
        ) = row

        return KernelFile(
            id=UUID(id_) if isinstance(id_, str) else id_,
            idea_id=UUID(idea_id) if isinstance(idea_id, str) else idea_id,
            file_type=file_type,
            content=content or "",
            content_hash=content_hash,
            is_complete=bool(is_complete),
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
