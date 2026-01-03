"""Version concept - manages version control for idea files via JJ."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional
from pathlib import Path
import structlog

from ..jj.repository import jj_repository, Commit

logger = structlog.get_logger()


# Mapping of kernel file types to their filenames
KERNEL_FILE_NAMES = {
    "summary": "Summary.md",
    "challenge": "Challenge.md",
    "approach": "Approach.md",
    "coherent_steps": "CoherentSteps.md",
}


@dataclass
class Version:
    """Represents a version (commit) of a file."""

    commit_id: str
    change_id: str
    message: str
    timestamp: datetime
    author: str


class VersionConcept:
    """
    Actions for the Version concept.

    Wraps JJ repository operations for idea version control.
    """

    def initialize(self, idea_id: UUID) -> Path:
        """
        Initialize version control for a new idea.

        Creates a JJ repository and initial directory structure.

        Args:
            idea_id: The idea UUID

        Returns:
            Path to the repository
        """
        logger.info("version_initialize", idea_id=str(idea_id))
        return jj_repository.initialize(str(idea_id))

    def commit(
        self,
        idea_id: UUID,
        file_type: str,
        content: str,
        user_name: str = "Crabgrass User"
    ) -> str:
        """
        Commit a kernel file change.

        Writes the file to the repository and creates a commit.

        Args:
            idea_id: The idea UUID
            file_type: Kernel file type (summary, challenge, approach, coherent_steps)
            content: The new file content
            user_name: Name of the user making the change

        Returns:
            The commit ID
        """
        idea_id_str = str(idea_id)

        # Ensure repo is initialized
        if not jj_repository.exists(idea_id_str):
            logger.info("version_auto_initialize", idea_id=idea_id_str)
            jj_repository.initialize(idea_id_str)

        # Get the filename for this file type
        filename = KERNEL_FILE_NAMES.get(file_type)
        if not filename:
            raise ValueError(f"Unknown kernel file type: {file_type}")

        file_path = f"kernel/{filename}"

        # Write the file
        jj_repository.write_file(idea_id_str, file_path, content)

        # Create commit with descriptive message
        message = f"Update {filename}"
        commit_id = jj_repository.commit(idea_id_str, message)

        logger.info(
            "version_committed",
            idea_id=idea_id_str,
            file_type=file_type,
            commit_id=commit_id,
        )

        return commit_id

    def get_history(
        self,
        idea_id: UUID,
        file_type: Optional[str] = None,
        limit: int = 50
    ) -> list[Version]:
        """
        Get version history for an idea or specific file.

        Args:
            idea_id: The idea UUID
            file_type: Optional kernel file type to filter by
            limit: Maximum versions to return

        Returns:
            List of Version objects, newest first
        """
        idea_id_str = str(idea_id)

        if not jj_repository.exists(idea_id_str):
            return []

        # Get file path if filtering by file type
        file_path = None
        if file_type:
            filename = KERNEL_FILE_NAMES.get(file_type)
            if filename:
                file_path = f"kernel/{filename}"

        commits = jj_repository.get_history(idea_id_str, file_path, limit)

        return [
            Version(
                commit_id=c.commit_id,
                change_id=c.change_id,
                message=c.description,
                timestamp=c.timestamp,
                author=c.author,
            )
            for c in commits
        ]

    def get_file_content_at_version(
        self,
        idea_id: UUID,
        file_type: str,
        commit_id: str
    ) -> Optional[str]:
        """
        Get file content at a specific version.

        Note: For MVP, we return current content. Full restore is future work.

        Args:
            idea_id: The idea UUID
            file_type: Kernel file type
            commit_id: The commit ID to retrieve

        Returns:
            File content or None if not found
        """
        # For MVP, just read current file
        # TODO: Implement jj cat or jj show for historical content
        idea_id_str = str(idea_id)
        filename = KERNEL_FILE_NAMES.get(file_type)

        if not filename:
            return None

        file_path = f"kernel/{filename}"
        return jj_repository.read_file(idea_id_str, file_path)

    def write_initial_files(
        self,
        idea_id: UUID,
        kernel_files: dict[str, str]
    ) -> None:
        """
        Write initial kernel files to the repository.

        Called after idea creation to populate the repo.

        Args:
            idea_id: The idea UUID
            kernel_files: Dict mapping file_type to content
        """
        idea_id_str = str(idea_id)

        for file_type, content in kernel_files.items():
            filename = KERNEL_FILE_NAMES.get(file_type)
            if filename:
                file_path = f"kernel/{filename}"
                jj_repository.write_file(idea_id_str, file_path, content)

        # Commit the initial files
        jj_repository.commit(idea_id_str, "Initialize kernel files")

        logger.info(
            "version_initial_files_written",
            idea_id=idea_id_str,
            file_count=len(kernel_files),
        )


# Singleton instance
version_concept = VersionConcept()
