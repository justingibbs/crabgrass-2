"""Embedding concept - generate and store vector embeddings for kernel files."""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import google.generativeai as genai
import structlog

from ..config import settings
from ..db.connection import get_db

logger = structlog.get_logger()

# Configure the Gemini client
genai.configure(api_key=settings.google_api_key)

# Embedding model - text-embedding-004 produces 768-dimensional vectors
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIMENSION = 768


@dataclass
class KernelEmbedding:
    """A stored embedding for a kernel file."""

    id: UUID
    kernel_file_id: UUID
    idea_id: UUID
    file_type: str
    embedding: list[float]
    content_hash: str
    created_at: datetime


class EmbeddingConcept:
    """Actions for generating and storing embeddings."""

    def generate(self, content: str) -> list[float]:
        """
        Generate a 768-dimensional embedding vector for content.

        Args:
            content: Text content to embed

        Returns:
            List of 768 floats representing the embedding vector
        """
        if not content or not content.strip():
            # Return zero vector for empty content
            return [0.0] * EMBEDDING_DIMENSION

        try:
            result = genai.embed_content(
                model=f"models/{EMBEDDING_MODEL}",
                content=content,
                task_type="RETRIEVAL_DOCUMENT",
            )

            embedding = result["embedding"]

            logger.debug(
                "embedding_generated",
                content_length=len(content),
                embedding_dim=len(embedding),
            )

            return embedding

        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            # Return zero vector on failure to avoid breaking the flow
            return [0.0] * EMBEDDING_DIMENSION

    def content_hash(self, content: str) -> str:
        """Generate a hash of content for change detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def store(
        self,
        kernel_file_id: UUID,
        idea_id: UUID,
        file_type: str,
        embedding: list[float],
        content_hash: str,
    ) -> KernelEmbedding:
        """
        Store an embedding in the database.

        Replaces any existing embedding for this kernel file.

        Args:
            kernel_file_id: The kernel file ID
            idea_id: The idea ID
            file_type: The file type (summary, challenge, approach, coherent_steps)
            embedding: The 768-dimensional vector
            content_hash: Hash of content for change detection

        Returns:
            The stored embedding
        """
        embedding_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        with get_db() as db:
            # Delete existing embedding for this kernel file
            db.execute(
                "DELETE FROM kernel_embeddings WHERE kernel_file_id = ?",
                [str(kernel_file_id)],
            )

            # Insert new embedding
            db.execute(
                """
                INSERT INTO kernel_embeddings
                (id, kernel_file_id, idea_id, file_type, embedding, content_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(embedding_id),
                    str(kernel_file_id),
                    str(idea_id),
                    file_type,
                    embedding,
                    content_hash,
                    now.isoformat(),
                ],
            )

        logger.info(
            "embedding_stored",
            embedding_id=str(embedding_id),
            kernel_file_id=str(kernel_file_id),
            file_type=file_type,
        )

        return KernelEmbedding(
            id=embedding_id,
            kernel_file_id=kernel_file_id,
            idea_id=idea_id,
            file_type=file_type,
            embedding=embedding,
            content_hash=content_hash,
            created_at=now,
        )

    def get(self, kernel_file_id: UUID) -> Optional[KernelEmbedding]:
        """
        Get the embedding for a kernel file.

        Args:
            kernel_file_id: The kernel file ID

        Returns:
            The embedding or None if not found
        """
        with get_db() as db:
            result = db.execute(
                "SELECT * FROM kernel_embeddings WHERE kernel_file_id = ?",
                [str(kernel_file_id)],
            ).fetchone()

            if not result:
                return None

            return self._row_to_embedding(result)

    def get_by_idea_and_type(
        self, idea_id: UUID, file_type: str
    ) -> Optional[KernelEmbedding]:
        """
        Get the embedding for a kernel file by idea ID and file type.

        Args:
            idea_id: The idea ID
            file_type: The file type

        Returns:
            The embedding or None if not found
        """
        with get_db() as db:
            result = db.execute(
                "SELECT * FROM kernel_embeddings WHERE idea_id = ? AND file_type = ?",
                [str(idea_id), file_type],
            ).fetchone()

            if not result:
                return None

            return self._row_to_embedding(result)

    def get_hash(self, kernel_file_id: UUID) -> Optional[str]:
        """
        Get just the content hash for a kernel file embedding.

        Useful for checking if re-embedding is needed.

        Args:
            kernel_file_id: The kernel file ID

        Returns:
            The content hash or None if no embedding exists
        """
        with get_db() as db:
            result = db.execute(
                "SELECT content_hash FROM kernel_embeddings WHERE kernel_file_id = ?",
                [str(kernel_file_id)],
            ).fetchone()

            return result[0] if result else None

    def needs_update(self, kernel_file_id: UUID, content: str) -> bool:
        """
        Check if an embedding needs to be updated.

        Args:
            kernel_file_id: The kernel file ID
            content: Current content

        Returns:
            True if embedding doesn't exist or content has changed
        """
        existing_hash = self.get_hash(kernel_file_id)
        if not existing_hash:
            return True

        current_hash = self.content_hash(content)
        return existing_hash != current_hash

    def _row_to_embedding(self, row) -> KernelEmbedding:
        """Convert a database row to a KernelEmbedding object."""
        # Row order: id, kernel_file_id, idea_id, file_type, embedding, content_hash, created_at
        return KernelEmbedding(
            id=UUID(str(row[0])),
            kernel_file_id=UUID(str(row[1])),
            idea_id=UUID(str(row[2])),
            file_type=row[3],
            embedding=list(row[4]) if row[4] else [],
            content_hash=row[5],
            created_at=self._parse_timestamp(row[6]),
        )

    def _parse_timestamp(self, value) -> datetime:
        """Parse a timestamp from the database."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return datetime.fromisoformat(value)
        return value


# Singleton instance
embedding_concept = EmbeddingConcept()
