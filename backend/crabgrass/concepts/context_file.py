"""ContextFile concept - manages optional supporting files for ideas."""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

import structlog

from ..db.connection import get_db
from ..jj.repository import jj_repository

logger = structlog.get_logger()

# Validation constants
MAX_FILE_SIZE_BYTES = 50 * 1024  # 50KB
VALID_FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+\.md$")


@dataclass
class ContextFile:
    """Represents a context file."""

    id: UUID
    idea_id: Optional[UUID]  # For idea context files
    objective_id: Optional[UUID]  # For objective context files
    filename: str
    content: str
    size_bytes: int
    created_by: Optional[UUID]
    created_by_agent: bool
    created_at: datetime
    updated_at: datetime


class ContextFileConcept:
    """
    Actions for the ContextFile concept.

    Context files are optional markdown files that support idea development.
    They are stored in both the database and the JJ repository.
    """

    def _validate_filename(self, filename: str) -> None:
        """Validate filename format."""
        if not VALID_FILENAME_PATTERN.match(filename):
            raise ValueError(
                f"Invalid filename '{filename}'. Must match pattern: "
                "alphanumeric, hyphens, underscores only, ending with .md"
            )

    def _validate_size(self, content: str) -> int:
        """Validate content size and return byte count."""
        size_bytes = len(content.encode("utf-8"))
        if size_bytes > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Content too large ({size_bytes} bytes). "
                f"Maximum size is {MAX_FILE_SIZE_BYTES} bytes (50KB)."
            )
        return size_bytes

    def create(
        self,
        idea_id: Optional[UUID] = None,
        objective_id: Optional[UUID] = None,
        filename: str = "",
        content: str = "",
        user_id: Optional[UUID] = None,
        created_by_agent: bool = False,
    ) -> ContextFile:
        """
        Create a new context file.

        Args:
            idea_id: Parent idea UUID (for idea context files)
            objective_id: Parent objective UUID (for objective context files)
            filename: Filename (must be valid .md format)
            content: File content
            user_id: User creating the file (None if agent)
            created_by_agent: Whether this file was created by an agent

        Returns:
            The created ContextFile

        Raises:
            ValueError: If filename or content is invalid, or if neither idea_id nor objective_id provided
        """
        if not idea_id and not objective_id:
            raise ValueError("Either idea_id or objective_id must be provided")
        if idea_id and objective_id:
            raise ValueError("Cannot specify both idea_id and objective_id")

        self._validate_filename(filename)
        size_bytes = self._validate_size(content)

        file_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        with get_db() as db:
            db.execute(
                """
                INSERT INTO context_files
                (id, idea_id, objective_id, filename, content, size_bytes, created_by, created_by_agent, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(file_id),
                    str(idea_id) if idea_id else None,
                    str(objective_id) if objective_id else None,
                    filename,
                    content,
                    size_bytes,
                    str(user_id) if user_id else None,
                    created_by_agent,
                    now.isoformat(),
                    now.isoformat(),
                ],
            )

        # Write to JJ repository (only for idea context files)
        if idea_id:
            idea_id_str = str(idea_id)
            if jj_repository.exists(idea_id_str):
                file_path = f"context/{filename}"
                jj_repository.write_file(idea_id_str, file_path, content)
                jj_repository.commit(idea_id_str, f"Add context file: {filename}")

        logger.info(
            "context_file_created",
            idea_id=str(idea_id) if idea_id else None,
            objective_id=str(objective_id) if objective_id else None,
            filename=filename,
            size_bytes=size_bytes,
            created_by_agent=created_by_agent,
        )

        return ContextFile(
            id=file_id,
            idea_id=idea_id,
            objective_id=objective_id,
            filename=filename,
            content=content,
            size_bytes=size_bytes,
            created_by=user_id,
            created_by_agent=created_by_agent,
            created_at=now,
            updated_at=now,
        )

    def get(self, idea_id: UUID, filename: str) -> Optional[ContextFile]:
        """
        Get a context file by idea and filename.

        Args:
            idea_id: Parent idea UUID
            filename: The filename to find

        Returns:
            ContextFile or None if not found
        """
        with get_db() as db:
            result = db.execute(
                """
                SELECT id, idea_id, objective_id, filename, content, size_bytes,
                       created_by, created_by_agent, created_at, updated_at
                FROM context_files
                WHERE idea_id = ? AND filename = ?
                """,
                [str(idea_id), filename],
            ).fetchone()

            if not result:
                return None

            return self._row_to_context_file(result)

    def get_by_id(self, file_id: UUID) -> Optional[ContextFile]:
        """
        Get a context file by ID.

        Args:
            file_id: The file UUID

        Returns:
            ContextFile or None if not found
        """
        with get_db() as db:
            result = db.execute(
                """
                SELECT id, idea_id, objective_id, filename, content, size_bytes,
                       created_by, created_by_agent, created_at, updated_at
                FROM context_files
                WHERE id = ?
                """,
                [str(file_id)],
            ).fetchone()

            if not result:
                return None

            return self._row_to_context_file(result)

    def update(
        self,
        idea_id: UUID,
        filename: str,
        content: str,
    ) -> Optional[ContextFile]:
        """
        Update a context file's content.

        Args:
            idea_id: Parent idea UUID
            filename: The filename to update
            content: New content

        Returns:
            Updated ContextFile or None if not found

        Raises:
            ValueError: If content is invalid
        """
        size_bytes = self._validate_size(content)
        now = datetime.now(timezone.utc)

        with get_db() as db:
            # Check if file exists
            existing = db.execute(
                "SELECT id FROM context_files WHERE idea_id = ? AND filename = ?",
                [str(idea_id), filename],
            ).fetchone()

            if not existing:
                return None

            # Update the file
            db.execute(
                """
                UPDATE context_files
                SET content = ?, size_bytes = ?, updated_at = ?
                WHERE idea_id = ? AND filename = ?
                """,
                [content, size_bytes, now.isoformat(), str(idea_id), filename],
            )

        # Write to JJ repository
        idea_id_str = str(idea_id)
        if jj_repository.exists(idea_id_str):
            file_path = f"context/{filename}"
            jj_repository.write_file(idea_id_str, file_path, content)
            jj_repository.commit(idea_id_str, f"Update context file: {filename}")

        logger.info(
            "context_file_updated",
            idea_id=str(idea_id),
            filename=filename,
            size_bytes=size_bytes,
        )

        return self.get(idea_id, filename)

    def create_or_update(
        self,
        idea_id: UUID,
        filename: str,
        content: str,
        user_id: Optional[UUID] = None,
        created_by_agent: bool = False,
    ) -> ContextFile:
        """
        Create a context file or update it if it already exists.

        This is useful for agent-generated files like feedback-tasks.md
        that get regenerated on each evaluation.

        Args:
            idea_id: Parent idea UUID
            filename: Filename
            content: File content
            user_id: User creating/updating (None if agent)
            created_by_agent: Whether this file was created by an agent

        Returns:
            The created or updated ContextFile
        """
        existing = self.get(idea_id, filename)

        if existing:
            return self.update(idea_id, filename, content)
        else:
            return self.create(
                idea_id=idea_id,
                filename=filename,
                content=content,
                user_id=user_id,
                created_by_agent=created_by_agent,
            )

    def list(self, idea_id: UUID) -> List[ContextFile]:
        """
        List all context files for an idea.

        Args:
            idea_id: Parent idea UUID

        Returns:
            List of ContextFiles, ordered by created_at desc
        """
        with get_db() as db:
            results = db.execute(
                """
                SELECT id, idea_id, objective_id, filename, content, size_bytes,
                       created_by, created_by_agent, created_at, updated_at
                FROM context_files
                WHERE idea_id = ?
                ORDER BY created_at DESC
                """,
                [str(idea_id)],
            ).fetchall()

            return [self._row_to_context_file(row) for row in results]

    def list_for_objective(self, objective_id: UUID) -> List[ContextFile]:
        """
        List all context files for an objective.

        Args:
            objective_id: Parent objective UUID

        Returns:
            List of ContextFiles, ordered by created_at desc
        """
        with get_db() as db:
            results = db.execute(
                """
                SELECT id, idea_id, objective_id, filename, content, size_bytes,
                       created_by, created_by_agent, created_at, updated_at
                FROM context_files
                WHERE objective_id = ?
                ORDER BY created_at DESC
                """,
                [str(objective_id)],
            ).fetchall()

            return [self._row_to_context_file(row) for row in results]

    def delete(self, idea_id: UUID, file_id: UUID) -> bool:
        """
        Delete a context file.

        Args:
            idea_id: Parent idea UUID
            file_id: The file UUID to delete

        Returns:
            True if deleted, False if not found
        """
        # First get the file to know its filename for JJ
        file = self.get_by_id(file_id)
        if not file:
            return False

        # Verify the file belongs to the specified idea
        if file.idea_id != idea_id:
            return False

        with get_db() as db:
            result = db.execute(
                "DELETE FROM context_files WHERE id = ? AND idea_id = ?",
                [str(file_id), str(idea_id)],
            )
            # DuckDB doesn't return rowcount the same way, so we check if file existed
            deleted = file is not None

        if deleted:
            # Remove from JJ repository
            idea_id_str = str(idea_id)
            if jj_repository.exists(idea_id_str):
                file_path = f"context/{file.filename}"
                jj_repository.delete_file(idea_id_str, file_path)
                jj_repository.commit(idea_id_str, f"Delete context file: {file.filename}")

            logger.info(
                "context_file_deleted",
                idea_id=str(idea_id),
                file_id=str(file_id),
                filename=file.filename,
            )

        return deleted

    def _row_to_context_file(self, row) -> ContextFile:
        """Convert a database row to a ContextFile object."""
        # Helper to safely convert to UUID
        def to_uuid(val):
            if val is None:
                return None
            if isinstance(val, UUID):
                return val
            return UUID(val)

        # Helper to safely convert to datetime
        def to_datetime(val):
            if isinstance(val, datetime):
                return val
            return datetime.fromisoformat(val)

        # Row order: id, idea_id, objective_id, filename, content, size_bytes,
        #            created_by, created_by_agent, created_at, updated_at
        return ContextFile(
            id=to_uuid(row[0]),
            idea_id=to_uuid(row[1]),
            objective_id=to_uuid(row[2]),
            filename=row[3],
            content=row[4] or "",
            size_bytes=row[5] or 0,
            created_by=to_uuid(row[6]),
            created_by_agent=bool(row[7]),
            created_at=to_datetime(row[8]),
            updated_at=to_datetime(row[9]),
        )


# Singleton instance
context_file_concept = ContextFileConcept()
