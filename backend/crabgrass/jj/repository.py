"""JJ (Jujutsu) repository wrapper for version control of idea files."""

import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import structlog

from ..config import settings

logger = structlog.get_logger()


@dataclass
class Commit:
    """Represents a JJ commit/change."""

    change_id: str
    commit_id: str
    description: str
    timestamp: datetime
    author: str


class JJRepository:
    """
    Wrapper around the JJ CLI for managing idea repositories.

    Each idea gets its own JJ repository at {STORAGE_ROOT}/ideas/{idea_id}/
    """

    def __init__(self):
        self.storage_root = settings.storage_root
        self._ensure_jj_available()

    def _ensure_jj_available(self) -> None:
        """Verify JJ is installed and available."""
        if not shutil.which("jj"):
            raise RuntimeError("JJ (Jujutsu) is not installed or not in PATH")

    def _get_repo_path(self, idea_id: str) -> Path:
        """Get the repository path for an idea."""
        return self.storage_root / str(idea_id)

    def _run_jj(
        self,
        idea_id: str,
        args: list[str],
        check: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Run a JJ command in the idea's repository.

        Args:
            idea_id: The idea ID (repository name)
            args: JJ command arguments (without 'jj' prefix)
            check: Whether to raise on non-zero exit

        Returns:
            CompletedProcess with stdout/stderr
        """
        repo_path = self._get_repo_path(idea_id)

        cmd = ["jj"] + args

        logger.debug(
            "jj_command",
            idea_id=idea_id,
            command=" ".join(cmd),
            cwd=str(repo_path),
        )

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )

        if check and result.returncode != 0:
            logger.error(
                "jj_command_failed",
                idea_id=idea_id,
                command=" ".join(cmd),
                returncode=result.returncode,
                stderr=result.stderr,
            )
            raise RuntimeError(f"JJ command failed: {result.stderr}")

        return result

    def initialize(self, idea_id: str) -> Path:
        """
        Initialize a new JJ repository for an idea.

        Creates the directory structure and initializes JJ.

        Args:
            idea_id: The idea ID

        Returns:
            Path to the repository
        """
        repo_path = self._get_repo_path(idea_id)

        # Create directory structure
        repo_path.mkdir(parents=True, exist_ok=True)
        kernel_dir = repo_path / "kernel"
        kernel_dir.mkdir(exist_ok=True)

        # Check if already initialized
        jj_dir = repo_path / ".jj"
        if jj_dir.exists():
            logger.info("jj_repo_already_exists", idea_id=idea_id, path=str(repo_path))
            return repo_path

        # Initialize JJ repository with Git backend
        result = subprocess.run(
            ["jj", "git", "init"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to initialize JJ repo: {result.stderr}")

        logger.info("jj_repo_initialized", idea_id=idea_id, path=str(repo_path))

        return repo_path

    def write_file(self, idea_id: str, file_path: str, content: str) -> None:
        """
        Write a file to the repository.

        JJ automatically tracks file changes.

        Args:
            idea_id: The idea ID
            file_path: Relative path within the repo (e.g., "kernel/Challenge.md")
            content: File content
        """
        repo_path = self._get_repo_path(idea_id)
        full_path = repo_path / file_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        full_path.write_text(content, encoding="utf-8")

        logger.debug(
            "jj_file_written",
            idea_id=idea_id,
            file_path=file_path,
            size=len(content),
        )

    def read_file(self, idea_id: str, file_path: str) -> Optional[str]:
        """
        Read a file from the repository.

        Args:
            idea_id: The idea ID
            file_path: Relative path within the repo

        Returns:
            File content or None if not found
        """
        repo_path = self._get_repo_path(idea_id)
        full_path = repo_path / file_path

        if not full_path.exists():
            return None

        return full_path.read_text(encoding="utf-8")

    def delete_file(self, idea_id: str, file_path: str) -> bool:
        """
        Delete a file from the repository.

        JJ automatically tracks the deletion.

        Args:
            idea_id: The idea ID
            file_path: Relative path within the repo

        Returns:
            True if file was deleted, False if not found
        """
        repo_path = self._get_repo_path(idea_id)
        full_path = repo_path / file_path

        if not full_path.exists():
            return False

        full_path.unlink()

        logger.debug(
            "jj_file_deleted",
            idea_id=idea_id,
            file_path=file_path,
        )

        return True

    def commit(self, idea_id: str, message: str) -> str:
        """
        Commit current changes with a message.

        In JJ, this creates a new change and describes it.

        Args:
            idea_id: The idea ID
            message: Commit message

        Returns:
            The new commit/change ID
        """
        # Describe the current change
        self._run_jj(idea_id, ["describe", "-m", message])

        # Create a new empty change to work on
        result = self._run_jj(idea_id, ["new"])

        # Get the commit ID of what we just described
        log_result = self._run_jj(
            idea_id,
            ["log", "-r", "@-", "--no-graph", "-T", 'commit_id ++ "\n"', "-n", "1"]
        )

        commit_id = log_result.stdout.strip()[:12] if log_result.stdout else "unknown"

        logger.info(
            "jj_commit_created",
            idea_id=idea_id,
            message=message,
            commit_id=commit_id,
        )

        return commit_id

    def get_history(
        self,
        idea_id: str,
        file_path: Optional[str] = None,
        limit: int = 50
    ) -> list[Commit]:
        """
        Get commit history for the repository or a specific file.

        Args:
            idea_id: The idea ID
            file_path: Optional file path to filter history
            limit: Maximum number of commits to return

        Returns:
            List of Commit objects, newest first
        """
        repo_path = self._get_repo_path(idea_id)

        # Check if repo exists
        if not (repo_path / ".jj").exists():
            return []

        # Build the log command
        # Template format: change_id|commit_id|description|timestamp|author
        template = (
            'change_id.short() ++ "|" ++ '
            'commit_id.short() ++ "|" ++ '
            'description.first_line() ++ "|" ++ '
            'committer.timestamp() ++ "|" ++ '
            'author.email() ++ "\n"'
        )

        args = [
            "log",
            "--no-graph",
            "-T", template,
            "-n", str(limit),
        ]

        result = self._run_jj(idea_id, args, check=False)

        if result.returncode != 0:
            logger.warning(
                "jj_log_failed",
                idea_id=idea_id,
                stderr=result.stderr,
            )
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue

            parts = line.split("|", 4)
            if len(parts) < 5:
                continue

            change_id, commit_id, description, timestamp_str, author = parts

            # Skip empty descriptions (working copy)
            if not description.strip():
                continue

            # Parse timestamp (JJ format: 2024-01-15 10:30:00.000 -08:00)
            try:
                # Simplify timestamp parsing - just use the date part
                timestamp = datetime.fromisoformat(timestamp_str.split()[0])
            except (ValueError, IndexError):
                timestamp = datetime.now()

            commits.append(Commit(
                change_id=change_id,
                commit_id=commit_id,
                description=description,
                timestamp=timestamp,
                author=author,
            ))

        return commits

    def exists(self, idea_id: str) -> bool:
        """Check if a repository exists for the given idea."""
        repo_path = self._get_repo_path(idea_id)
        return (repo_path / ".jj").exists()

    def get_file_at_revision(
        self,
        idea_id: str,
        file_path: str,
        change_id: str,
    ) -> Optional[str]:
        """
        Get file content at a specific revision.

        Args:
            idea_id: The idea ID
            file_path: Relative path within the repo (e.g., "kernel/Challenge.md")
            change_id: The JJ change ID to retrieve from

        Returns:
            File content at that revision, or None if not found
        """
        repo_path = self._get_repo_path(idea_id)

        # Check if repo exists
        if not (repo_path / ".jj").exists():
            return None

        # Use jj file show to get content at revision
        # Format: jj file show -r <revision> <path>
        result = self._run_jj(
            idea_id,
            ["file", "show", "-r", change_id, file_path],
            check=False,
        )

        if result.returncode != 0:
            logger.warning(
                "jj_file_show_failed",
                idea_id=idea_id,
                file_path=file_path,
                change_id=change_id,
                stderr=result.stderr,
            )
            return None

        return result.stdout


# Singleton instance
jj_repository = JJRepository()
