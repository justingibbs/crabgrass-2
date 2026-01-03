"""Tests for coherence API routes."""

import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, AsyncMock
from uuid import UUID
from fastapi.testclient import TestClient

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_coherence_api.duckdb")
os.environ["STORAGE_ROOT"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_storage")

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
    """Create a test idea and return its ID."""
    idea = idea_concept.create(
        org_id=ACME_ORG_ID,
        user_id=SALLY_USER_ID,
        title="Test Idea for API",
    )
    on_idea_created(idea)
    return str(idea.id)


@pytest.fixture
def sally_cookie():
    """Cookie for Sally user."""
    return {"crabgrass_dev_user": str(SALLY_USER_ID)}


class TestCoherenceChatEndpoint:
    """Tests for POST /api/ideas/{id}/coherence/chat."""

    @pytest.mark.asyncio
    async def test_chat_returns_response(self, idea_id, sally_cookie):
        """Chat endpoint returns agent response."""
        with patch("crabgrass.concepts.agents.coherence_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Here's my advice on your idea..."

            response = client.post(
                f"/api/ideas/{idea_id}/coherence/chat",
                json={"message": "What should I work on next?"},
                cookies=sally_cookie,
            )

            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "session_id" in data
            assert data["response"] == "Here's my advice on your idea..."

    @pytest.mark.asyncio
    async def test_chat_creates_session(self, idea_id, sally_cookie):
        """Chat endpoint creates a session on first message."""
        with patch("crabgrass.concepts.agents.coherence_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Response"

            response = client.post(
                f"/api/ideas/{idea_id}/coherence/chat",
                json={"message": "Hello"},
                cookies=sally_cookie,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] is not None

            # Second message should use same session
            response2 = client.post(
                f"/api/ideas/{idea_id}/coherence/chat",
                json={"message": "Follow up", "session_id": data["session_id"]},
                cookies=sally_cookie,
            )

            assert response2.status_code == 200
            assert response2.json()["session_id"] == data["session_id"]

    def test_chat_requires_valid_idea(self, sally_cookie):
        """Chat endpoint returns 404 for invalid idea."""
        fake_id = "99999999-9999-9999-9999-999999999999"
        response = client.post(
            f"/api/ideas/{fake_id}/coherence/chat",
            json={"message": "Hello"},
            cookies=sally_cookie,
        )

        assert response.status_code == 404


class TestCoherenceEvaluateEndpoint:
    """Tests for POST /api/ideas/{id}/coherence/evaluate."""

    @pytest.mark.asyncio
    async def test_evaluate_creates_feedback_file(self, idea_id, sally_cookie):
        """Evaluate endpoint creates feedback-tasks.md."""
        with patch("crabgrass.concepts.agents.coherence_agent.generate_content") as mock_gen:
            mock_gen.return_value = "# Idea Feedback & Tasks\n\nYour feedback here."

            response = client.post(
                f"/api/ideas/{idea_id}/coherence/evaluate",
                cookies=sally_cookie,
            )

            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert "Idea Feedback" in data["content"]
            assert "kernel_complete_count" in data

    @pytest.mark.asyncio
    async def test_evaluate_returns_file_id(self, idea_id, sally_cookie):
        """Evaluate endpoint returns feedback file ID."""
        with patch("crabgrass.concepts.agents.coherence_agent.generate_content") as mock_gen:
            mock_gen.return_value = "# Feedback"

            response = client.post(
                f"/api/ideas/{idea_id}/coherence/evaluate",
                cookies=sally_cookie,
            )

            assert response.status_code == 200
            data = response.json()
            assert "feedback_file_id" in data
            # The file should have been created
            assert data["feedback_file_id"] is not None

    def test_evaluate_requires_valid_idea(self, sally_cookie):
        """Evaluate endpoint returns 404 for invalid idea."""
        fake_id = "99999999-9999-9999-9999-999999999999"
        response = client.post(
            f"/api/ideas/{fake_id}/coherence/evaluate",
            cookies=sally_cookie,
        )

        assert response.status_code == 404


class TestContextFilesListEndpoint:
    """Tests for GET /api/ideas/{id}/context."""

    def test_list_returns_empty(self, idea_id, sally_cookie):
        """List returns empty when no context files."""
        response = client.get(
            f"/api/ideas/{idea_id}/context",
            cookies=sally_cookie,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["files"] == []

    def test_list_returns_files(self, idea_id, sally_cookie):
        """List returns context files."""
        # Create some context files
        context_file_concept.create(
            idea_id=UUID(idea_id),
            filename="notes.md",
            content="My notes",
            user_id=SALLY_USER_ID,
        )
        context_file_concept.create(
            idea_id=UUID(idea_id),
            filename="feedback-tasks.md",
            content="Feedback",
            created_by_agent=True,
        )

        response = client.get(
            f"/api/ideas/{idea_id}/context",
            cookies=sally_cookie,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["files"]) == 2

        filenames = {f["filename"] for f in data["files"]}
        assert "notes.md" in filenames
        assert "feedback-tasks.md" in filenames

    def test_list_includes_metadata(self, idea_id, sally_cookie):
        """List includes file metadata."""
        context_file_concept.create(
            idea_id=UUID(idea_id),
            filename="research.md",
            content="Research data",
            user_id=SALLY_USER_ID,
            created_by_agent=False,
        )

        response = client.get(
            f"/api/ideas/{idea_id}/context",
            cookies=sally_cookie,
        )

        assert response.status_code == 200
        file_data = response.json()["files"][0]

        assert "id" in file_data
        assert "filename" in file_data
        assert "size_bytes" in file_data
        assert "created_by_agent" in file_data
        assert "created_at" in file_data
        assert "updated_at" in file_data

    def test_list_requires_valid_idea(self, sally_cookie):
        """List endpoint returns 404 for invalid idea."""
        fake_id = "99999999-9999-9999-9999-999999999999"
        response = client.get(
            f"/api/ideas/{fake_id}/context",
            cookies=sally_cookie,
        )

        assert response.status_code == 404


class TestContextFileGetEndpoint:
    """Tests for GET /api/ideas/{id}/context/{file_id}."""

    def test_get_context_file(self, idea_id, sally_cookie):
        """Get a context file returns content."""
        # Create a context file
        context_file = context_file_concept.create(
            idea_id=UUID(idea_id),
            filename="notes.md",
            content="# Notes\n\nSome content here.",
            user_id=SALLY_USER_ID,
        )

        response = client.get(
            f"/api/ideas/{idea_id}/context/{context_file.id}",
            cookies=sally_cookie,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "notes.md"
        assert data["content"] == "# Notes\n\nSome content here."
        assert "id" in data
        assert "size_bytes" in data

    def test_get_nonexistent_file_returns_404(self, idea_id, sally_cookie):
        """Get nonexistent file returns 404."""
        fake_file_id = "99999999-9999-9999-9999-999999999999"
        response = client.get(
            f"/api/ideas/{idea_id}/context/{fake_file_id}",
            cookies=sally_cookie,
        )

        assert response.status_code == 404

    def test_get_context_file_invalid_idea(self, idea_id, sally_cookie):
        """Get context file with invalid idea returns 404."""
        # Create a context file first
        context_file = context_file_concept.create(
            idea_id=UUID(idea_id),
            filename="notes.md",
            content="# Notes",
            user_id=SALLY_USER_ID,
        )

        fake_idea_id = "99999999-9999-9999-9999-999999999999"
        response = client.get(
            f"/api/ideas/{fake_idea_id}/context/{context_file.id}",
            cookies=sally_cookie,
        )

        assert response.status_code == 404


class TestCoherenceSessionsEndpoint:
    """Tests for GET /api/ideas/{id}/coherence/sessions."""

    def test_list_sessions_empty(self, idea_id, sally_cookie):
        """List returns empty when no sessions."""
        response = client.get(
            f"/api/ideas/{idea_id}/coherence/sessions",
            cookies=sally_cookie,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []

    @pytest.mark.asyncio
    async def test_list_sessions_after_chat(self, idea_id, sally_cookie):
        """List returns sessions after chat."""
        with patch("crabgrass.concepts.agents.coherence_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Response"

            # Create a session via chat
            client.post(
                f"/api/ideas/{idea_id}/coherence/chat",
                json={"message": "Hello"},
                cookies=sally_cookie,
            )

        response = client.get(
            f"/api/ideas/{idea_id}/coherence/sessions",
            cookies=sally_cookie,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["agent_type"] == "coherence"
