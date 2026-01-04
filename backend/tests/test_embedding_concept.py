"""Tests for the Embedding concept."""

import uuid
from unittest.mock import patch
from pathlib import Path
import tempfile
import os

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_embedding.duckdb")

import pytest
from fastapi.testclient import TestClient

from crabgrass.main import app
from crabgrass.concepts.embedding import EmbeddingConcept, EMBEDDING_DIMENSION
from crabgrass.db.connection import get_connection, close_connection, reset_database, get_db
from crabgrass.db.migrations import run_migrations, SALLY_USER_ID


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test."""
    reset_database()
    get_connection()
    run_migrations()
    yield
    close_connection()


@pytest.fixture
def sally_client():
    """Create a test client authenticated as Sally."""
    c = TestClient(app)
    c.cookies.set("crabgrass_dev_user", str(SALLY_USER_ID))
    return c


@pytest.fixture
def test_idea(sally_client):
    """Create a test idea and return its ID and kernel file IDs."""
    response = sally_client.post("/api/ideas", json={"title": "Test Idea"})
    idea_id = response.json()["id"]

    # Get kernel file IDs
    idea_response = sally_client.get(f"/api/ideas/{idea_id}")
    kernel_files = idea_response.json()["kernel_files"]

    # Get the actual kernel file IDs from the database
    with get_db() as db:
        result = db.execute(
            "SELECT id, file_type FROM kernel_files WHERE idea_id = ?",
            [idea_id]
        ).fetchall()
        kernel_file_ids = {row[1]: uuid.UUID(str(row[0])) for row in result}

    return {
        "idea_id": uuid.UUID(idea_id),
        "kernel_file_ids": kernel_file_ids,
    }


class TestEmbeddingConcept:
    """Tests for EmbeddingConcept."""

    def test_generate_returns_correct_dimension(self):
        """Test that generate returns a 768-dimensional vector."""
        concept = EmbeddingConcept()

        with patch("crabgrass.concepts.embedding.genai.embed_content") as mock_embed:
            # Mock the Gemini response
            mock_embed.return_value = {
                "embedding": [0.1] * EMBEDDING_DIMENSION
            }

            embedding = concept.generate("Test content")

            assert len(embedding) == EMBEDDING_DIMENSION
            assert all(isinstance(x, float) for x in embedding)

    def test_generate_with_empty_content_returns_zero_vector(self):
        """Test that empty content returns a zero vector."""
        concept = EmbeddingConcept()

        embedding = concept.generate("")

        assert len(embedding) == EMBEDDING_DIMENSION
        assert all(x == 0.0 for x in embedding)

    def test_generate_with_whitespace_only_returns_zero_vector(self):
        """Test that whitespace-only content returns a zero vector."""
        concept = EmbeddingConcept()

        embedding = concept.generate("   \n\t  ")

        assert len(embedding) == EMBEDDING_DIMENSION
        assert all(x == 0.0 for x in embedding)

    def test_generate_handles_api_error_gracefully(self):
        """Test that API errors return zero vector instead of raising."""
        concept = EmbeddingConcept()

        with patch("crabgrass.concepts.embedding.genai.embed_content") as mock_embed:
            mock_embed.side_effect = Exception("API error")

            embedding = concept.generate("Test content")

            # Should return zero vector on error
            assert len(embedding) == EMBEDDING_DIMENSION
            assert all(x == 0.0 for x in embedding)

    def test_content_hash_returns_consistent_hash(self):
        """Test that content_hash returns consistent values."""
        concept = EmbeddingConcept()

        hash1 = concept.content_hash("Test content")
        hash2 = concept.content_hash("Test content")
        hash3 = concept.content_hash("Different content")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 16  # SHA256 truncated to 16 chars

    def test_store_and_get_roundtrip(self, test_idea):
        """Test that store and get work correctly."""
        concept = EmbeddingConcept()

        idea_id = test_idea["idea_id"]
        kernel_file_id = test_idea["kernel_file_ids"]["summary"]
        file_type = "summary"
        embedding = [0.1] * EMBEDDING_DIMENSION
        content_hash = "abc123"

        # Store the embedding
        stored = concept.store(
            kernel_file_id=kernel_file_id,
            idea_id=idea_id,
            file_type=file_type,
            embedding=embedding,
            content_hash=content_hash,
        )

        assert stored is not None
        assert stored.kernel_file_id == kernel_file_id
        assert stored.idea_id == idea_id
        assert stored.file_type == file_type
        assert stored.content_hash == content_hash

        # Retrieve the embedding
        retrieved = concept.get(kernel_file_id)

        assert retrieved is not None
        assert retrieved.kernel_file_id == kernel_file_id
        assert len(retrieved.embedding) == EMBEDDING_DIMENSION

    def test_store_replaces_existing_embedding(self, test_idea):
        """Test that store replaces existing embedding for same kernel file."""
        concept = EmbeddingConcept()

        idea_id = test_idea["idea_id"]
        kernel_file_id = test_idea["kernel_file_ids"]["challenge"]
        file_type = "challenge"

        # Store first embedding
        concept.store(
            kernel_file_id=kernel_file_id,
            idea_id=idea_id,
            file_type=file_type,
            embedding=[0.1] * EMBEDDING_DIMENSION,
            content_hash="hash1",
        )

        # Store second embedding with same kernel_file_id
        concept.store(
            kernel_file_id=kernel_file_id,
            idea_id=idea_id,
            file_type=file_type,
            embedding=[0.2] * EMBEDDING_DIMENSION,
            content_hash="hash2",
        )

        # Should only have one embedding, with the new hash
        retrieved = concept.get(kernel_file_id)
        assert retrieved.content_hash == "hash2"

    def test_get_by_idea_and_type(self, test_idea):
        """Test get_by_idea_and_type retrieves correct embedding."""
        concept = EmbeddingConcept()

        idea_id = test_idea["idea_id"]
        kernel_file_id = test_idea["kernel_file_ids"]["approach"]
        file_type = "approach"

        concept.store(
            kernel_file_id=kernel_file_id,
            idea_id=idea_id,
            file_type=file_type,
            embedding=[0.5] * EMBEDDING_DIMENSION,
            content_hash="testhash",
        )

        retrieved = concept.get_by_idea_and_type(idea_id, file_type)

        assert retrieved is not None
        assert retrieved.idea_id == idea_id
        assert retrieved.file_type == file_type

    def test_get_returns_none_for_nonexistent(self):
        """Test that get returns None for non-existent embedding."""
        concept = EmbeddingConcept()

        result = concept.get(uuid.uuid4())

        assert result is None

    def test_needs_update_returns_true_for_new_content(self):
        """Test needs_update returns True when no embedding exists."""
        concept = EmbeddingConcept()

        needs = concept.needs_update(uuid.uuid4(), "New content")

        assert needs is True

    def test_needs_update_returns_false_for_unchanged_content(self, test_idea):
        """Test needs_update returns False when content hasn't changed."""
        concept = EmbeddingConcept()

        idea_id = test_idea["idea_id"]
        kernel_file_id = test_idea["kernel_file_ids"]["summary"]
        content = "Test content"
        content_hash = concept.content_hash(content)

        # Store embedding with matching hash
        concept.store(
            kernel_file_id=kernel_file_id,
            idea_id=idea_id,
            file_type="summary",
            embedding=[0.1] * EMBEDDING_DIMENSION,
            content_hash=content_hash,
        )

        needs = concept.needs_update(kernel_file_id, content)

        assert needs is False

    def test_needs_update_returns_true_for_changed_content(self, test_idea):
        """Test needs_update returns True when content has changed."""
        concept = EmbeddingConcept()

        idea_id = test_idea["idea_id"]
        kernel_file_id = test_idea["kernel_file_ids"]["summary"]

        # Store embedding with one hash
        concept.store(
            kernel_file_id=kernel_file_id,
            idea_id=idea_id,
            file_type="summary",
            embedding=[0.1] * EMBEDDING_DIMENSION,
            content_hash="oldhash",
        )

        # Check with different content
        needs = concept.needs_update(kernel_file_id, "Different content")

        assert needs is True

    def test_get_hash_returns_hash_for_existing(self, test_idea):
        """Test get_hash returns the stored hash."""
        concept = EmbeddingConcept()

        idea_id = test_idea["idea_id"]
        kernel_file_id = test_idea["kernel_file_ids"]["summary"]
        expected_hash = "myhash123"

        concept.store(
            kernel_file_id=kernel_file_id,
            idea_id=idea_id,
            file_type="summary",
            embedding=[0.1] * EMBEDDING_DIMENSION,
            content_hash=expected_hash,
        )

        result = concept.get_hash(kernel_file_id)

        assert result == expected_hash

    def test_get_hash_returns_none_for_nonexistent(self):
        """Test get_hash returns None for non-existent embedding."""
        concept = EmbeddingConcept()

        result = concept.get_hash(uuid.uuid4())

        assert result is None
