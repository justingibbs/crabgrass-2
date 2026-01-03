"""Tests for context file API routes (Slice 8)."""

import pytest
from pathlib import Path
import tempfile
import os
from uuid import UUID
from unittest.mock import patch, AsyncMock

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_context_files.duckdb")
os.environ["STORAGE_ROOT"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_storage")

from fastapi.testclient import TestClient

from crabgrass.main import app
from crabgrass.db.connection import get_connection, close_connection, reset_database
from crabgrass.db.migrations import run_migrations, SALLY_USER_ID, SAM_USER_ID, ACME_ORG_ID
from crabgrass.concepts.idea import IdeaConcept
from crabgrass.concepts.context_file import context_file_concept
from crabgrass.sync.synchronizations import on_idea_created

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test."""
    reset_database()
    get_connection()
    run_migrations()
    yield
    close_connection()


@pytest.fixture
def idea_concept():
    return IdeaConcept()


@pytest.fixture
def idea_id(idea_concept):
    """Create a test idea."""
    idea = idea_concept.create(
        org_id=ACME_ORG_ID,
        user_id=SALLY_USER_ID,
        title="Test Idea for Context Files",
    )
    on_idea_created(idea)
    return str(idea.id)


@pytest.fixture
def sally_cookie():
    return {"crabgrass_dev_user": str(SALLY_USER_ID)}


@pytest.fixture
def sam_cookie():
    return {"crabgrass_dev_user": str(SAM_USER_ID)}


class TestContextFileCreate:
    """Tests for POST /api/ideas/{id}/context."""

    def test_create_context_file(self, idea_id, sally_cookie):
        """Create a new context file."""
        response = client.post(
            f"/api/ideas/{idea_id}/context",
            json={"filename": "research.md", "content": "# Research Notes"},
            cookies=sally_cookie,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "research.md"
        assert data["content"] == "# Research Notes"
        assert "id" in data
        assert data["created_by_agent"] is False

    def test_create_context_file_empty_content(self, idea_id, sally_cookie):
        """Create a context file with empty content."""
        response = client.post(
            f"/api/ideas/{idea_id}/context",
            json={"filename": "empty.md", "content": ""},
            cookies=sally_cookie,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "empty.md"
        assert data["content"] == ""

    def test_create_context_file_duplicate_name(self, idea_id, sally_cookie):
        """Cannot create a file with duplicate name."""
        # Create first file
        client.post(
            f"/api/ideas/{idea_id}/context",
            json={"filename": "duplicate.md", "content": "First"},
            cookies=sally_cookie,
        )

        # Try to create with same name
        response = client.post(
            f"/api/ideas/{idea_id}/context",
            json={"filename": "duplicate.md", "content": "Second"},
            cookies=sally_cookie,
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_context_file_invalid_idea(self, sally_cookie):
        """Cannot create file for invalid idea."""
        fake_id = "99999999-9999-9999-9999-999999999999"
        response = client.post(
            f"/api/ideas/{fake_id}/context",
            json={"filename": "test.md", "content": ""},
            cookies=sally_cookie,
        )

        assert response.status_code == 404


class TestContextFileUpdate:
    """Tests for PUT /api/ideas/{id}/context/{file_id}."""

    def test_update_context_file(self, idea_id, sally_cookie):
        """Update a context file's content."""
        # Create a file first
        create_response = client.post(
            f"/api/ideas/{idea_id}/context",
            json={"filename": "update-test.md", "content": "Original"},
            cookies=sally_cookie,
        )
        file_id = create_response.json()["id"]

        # Update it
        response = client.put(
            f"/api/ideas/{idea_id}/context/{file_id}",
            json={"content": "Updated content"},
            cookies=sally_cookie,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated content"
        assert data["filename"] == "update-test.md"

    def test_update_nonexistent_file(self, idea_id, sally_cookie):
        """Cannot update nonexistent file."""
        fake_file_id = "99999999-9999-9999-9999-999999999999"
        response = client.put(
            f"/api/ideas/{idea_id}/context/{fake_file_id}",
            json={"content": "New content"},
            cookies=sally_cookie,
        )

        assert response.status_code == 404


class TestContextFileDelete:
    """Tests for DELETE /api/ideas/{id}/context/{file_id}."""

    def test_delete_context_file(self, idea_id, sally_cookie):
        """Delete a context file."""
        # Create a file first
        create_response = client.post(
            f"/api/ideas/{idea_id}/context",
            json={"filename": "delete-test.md", "content": "To be deleted"},
            cookies=sally_cookie,
        )
        file_id = create_response.json()["id"]

        # Delete it
        response = client.delete(
            f"/api/ideas/{idea_id}/context/{file_id}",
            cookies=sally_cookie,
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it's gone
        get_response = client.get(
            f"/api/ideas/{idea_id}/context/{file_id}",
            cookies=sally_cookie,
        )
        assert get_response.status_code == 404

    def test_delete_nonexistent_file(self, idea_id, sally_cookie):
        """Cannot delete nonexistent file."""
        fake_file_id = "99999999-9999-9999-9999-999999999999"
        response = client.delete(
            f"/api/ideas/{idea_id}/context/{fake_file_id}",
            cookies=sally_cookie,
        )

        assert response.status_code == 404


class TestContextFileChat:
    """Tests for POST /api/ideas/{id}/context/{file_id}/chat."""

    def test_chat_with_context_agent(self, idea_id, sally_cookie):
        """Chat with the ContextAgent."""
        # Create a file first
        create_response = client.post(
            f"/api/ideas/{idea_id}/context",
            json={"filename": "chat-test.md", "content": "Some research content"},
            cookies=sally_cookie,
        )
        file_id = create_response.json()["id"]

        # Mock the agent response
        with patch("crabgrass.api.routes.files.context_agent.coach", new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = "Here are some insights from your file..."

            response = client.post(
                f"/api/ideas/{idea_id}/context/{file_id}/chat",
                json={"message": "What insights can you find?"},
                cookies=sally_cookie,
            )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data

    def test_chat_continues_session(self, idea_id, sally_cookie):
        """Chat continues in same session when session_id provided."""
        # Create a file first
        create_response = client.post(
            f"/api/ideas/{idea_id}/context",
            json={"filename": "session-test.md", "content": "Content"},
            cookies=sally_cookie,
        )
        file_id = create_response.json()["id"]

        with patch("crabgrass.api.routes.files.context_agent.coach", new_callable=AsyncMock) as mock_coach:
            mock_coach.return_value = "Response 1"

            # First message
            first_response = client.post(
                f"/api/ideas/{idea_id}/context/{file_id}/chat",
                json={"message": "First message"},
                cookies=sally_cookie,
            )
            session_id = first_response.json()["session_id"]

            mock_coach.return_value = "Response 2"

            # Second message with session_id
            second_response = client.post(
                f"/api/ideas/{idea_id}/context/{file_id}/chat",
                json={"message": "Second message", "session_id": session_id},
                cookies=sally_cookie,
            )

        assert second_response.status_code == 200
        assert second_response.json()["session_id"] == session_id

    def test_chat_with_nonexistent_file(self, idea_id, sally_cookie):
        """Cannot chat with nonexistent file."""
        fake_file_id = "99999999-9999-9999-9999-999999999999"
        response = client.post(
            f"/api/ideas/{idea_id}/context/{fake_file_id}/chat",
            json={"message": "Hello"},
            cookies=sally_cookie,
        )

        assert response.status_code == 404
