"""Tests for the Agent API routes."""

import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, AsyncMock
from uuid import uuid4

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_agent.duckdb")

from fastapi.testclient import TestClient
from crabgrass.main import app
from crabgrass.db.connection import get_connection, close_connection, reset_database
from crabgrass.db.migrations import run_migrations, SALLY_USER_ID, SAM_USER_ID


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test."""
    reset_database()
    get_connection()
    run_migrations()
    yield
    close_connection()


@pytest.fixture
def client():
    """Create a test client authenticated as Sally."""
    c = TestClient(app)
    c.cookies.set("crabgrass_dev_user", str(SALLY_USER_ID))
    return c


class TestAgentChatAPI:
    """Tests for agent chat endpoints."""

    @pytest.fixture
    def idea_id(self, client):
        """Create a test idea and return its ID."""
        response = client.post(
            "/api/ideas",
            json={"title": "Test Idea for Chat"},
        )
        assert response.status_code == 200
        return response.json()["id"]

    def test_chat_requires_idea(self, client):
        """Chat fails if idea doesn't exist."""
        fake_id = str(uuid4())
        response = client.post(
            f"/api/ideas/{fake_id}/kernel/challenge/chat",
            json={"message": "Hello"},
        )
        assert response.status_code == 404

    def test_chat_validates_file_type(self, client, idea_id):
        """Chat fails for invalid file type."""
        response = client.post(
            f"/api/ideas/{idea_id}/kernel/invalid/chat",
            json={"message": "Hello"},
        )
        assert response.status_code == 400

    def test_chat_with_challenge_agent(self, client, idea_id):
        """Chat with challenge agent returns response."""
        with patch("crabgrass.concepts.agents.challenge_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "This is a test response from the agent."

            response = client.post(
                f"/api/ideas/{idea_id}/kernel/challenge/chat",
                json={"message": "Help me with my challenge"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "session_id" in data
            assert data["agent_type"] == "challenge"

    def test_chat_creates_session(self, client, idea_id):
        """Chat creates a session if none exists."""
        with patch("crabgrass.concepts.agents.challenge_agent.chat_with_history") as mock:
            mock.return_value = "Test response"

            response = client.post(
                f"/api/ideas/{idea_id}/kernel/challenge/chat",
                json={"message": "Hello"},
            )

            assert response.status_code == 200
            session_id = response.json()["session_id"]
            assert session_id is not None

    def test_chat_uses_existing_session(self, client, idea_id):
        """Chat uses provided session ID."""
        with patch("crabgrass.concepts.agents.challenge_agent.chat_with_history") as mock:
            mock.return_value = "Test response"

            # First message creates session
            response1 = client.post(
                f"/api/ideas/{idea_id}/kernel/challenge/chat",
                json={"message": "First message"},
            )
            session_id = response1.json()["session_id"]

            # Second message uses same session
            response2 = client.post(
                f"/api/ideas/{idea_id}/kernel/challenge/chat",
                json={"message": "Second message", "session_id": session_id},
            )

            assert response2.status_code == 200
            assert response2.json()["session_id"] == session_id

    def test_chat_only_challenge_agent_available(self, client, idea_id):
        """Only challenge agent is available in Slice 5."""
        # summary, approach, and coherent_steps should fail
        for file_type in ["summary", "approach", "coherent_steps"]:
            response = client.post(
                f"/api/ideas/{idea_id}/kernel/{file_type}/chat",
                json={"message": "Hello"},
            )
            assert response.status_code == 400
            assert "No agent available" in response.json()["detail"]


class TestSessionsAPI:
    """Tests for session list/get endpoints."""

    @pytest.fixture
    def idea_id(self, client):
        """Create a test idea and return its ID."""
        response = client.post(
            "/api/ideas",
            json={"title": "Test Idea for Sessions"},
        )
        return response.json()["id"]

    def test_list_sessions_empty(self, client, idea_id):
        """List sessions returns empty list initially."""
        response = client.get(
            f"/api/ideas/{idea_id}/kernel/challenge/sessions",
        )

        assert response.status_code == 200
        assert response.json()["sessions"] == []

    def test_list_sessions_after_chat(self, client, idea_id):
        """List sessions returns sessions after chat."""
        with patch("crabgrass.concepts.agents.challenge_agent.chat_with_history") as mock:
            mock.return_value = "Test response"

            # Create a session via chat
            client.post(
                f"/api/ideas/{idea_id}/kernel/challenge/chat",
                json={"message": "Hello"},
            )

            # List sessions
            response = client.get(
                f"/api/ideas/{idea_id}/kernel/challenge/sessions",
            )

            assert response.status_code == 200
            sessions = response.json()["sessions"]
            assert len(sessions) == 1
            assert sessions[0]["agent_type"] == "challenge"

    def test_get_session_with_messages(self, client, idea_id):
        """Get session returns messages."""
        with patch("crabgrass.concepts.agents.challenge_agent.chat_with_history") as mock:
            mock.return_value = "Test response"

            # Create a session via chat
            chat_response = client.post(
                f"/api/ideas/{idea_id}/kernel/challenge/chat",
                json={"message": "Hello"},
            )
            session_id = chat_response.json()["session_id"]

            # Get session with messages
            response = client.get(
                f"/api/ideas/{idea_id}/sessions/{session_id}",
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session"]["id"] == session_id
            assert len(data["messages"]) == 2  # user message + agent response

    def test_get_nonexistent_session(self, client, idea_id):
        """Get nonexistent session returns 404."""
        fake_session_id = str(uuid4())
        response = client.get(
            f"/api/ideas/{idea_id}/sessions/{fake_session_id}",
        )
        assert response.status_code == 404
