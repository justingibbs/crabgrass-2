"""Tests for the Session concept."""

import pytest
from pathlib import Path
import tempfile
import os
from uuid import uuid4

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_session.duckdb")

from crabgrass.concepts.session import SessionConcept, session_concept
from crabgrass.concepts.idea import IdeaConcept
from crabgrass.sync.synchronizations import on_idea_created
from crabgrass.db.connection import get_connection, close_connection, reset_database
from crabgrass.db.migrations import run_migrations, SALLY_USER_ID, ACME_ORG_ID


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test."""
    reset_database()
    get_connection()
    run_migrations()
    yield
    close_connection()


@pytest.fixture
def idea_id():
    """Create a test idea and return its ID."""
    idea_concept = IdeaConcept()
    idea = idea_concept.create(
        org_id=ACME_ORG_ID,
        user_id=SALLY_USER_ID,
        title="Test Idea for Sessions",
    )
    on_idea_created(idea)
    return idea.id


class TestSessionConcept:
    """Tests for Session concept."""

    def test_create_session(self, idea_id):
        """Create a session."""
        session = session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="challenge",
            file_type="challenge",
        )

        assert session.id is not None
        assert session.idea_id == idea_id
        assert session.user_id == SALLY_USER_ID
        assert session.agent_type == "challenge"
        assert session.file_type == "challenge"

    def test_get_session(self, idea_id):
        """Get a session by ID."""
        created = session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="challenge",
            file_type="challenge",
        )

        retrieved = session_concept.get(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.agent_type == "challenge"

    def test_get_nonexistent_session(self):
        """Get a nonexistent session returns None."""
        result = session_concept.get(uuid4())
        assert result is None

    def test_list_sessions_for_idea(self, idea_id):
        """List sessions for an idea."""
        # Create multiple sessions
        session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="challenge",
            file_type="challenge",
        )
        session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="summary",
            file_type="summary",
        )

        sessions = session_concept.list_for_idea(idea_id)

        assert len(sessions) == 2

    def test_list_sessions_filtered_by_agent_type(self, idea_id):
        """List sessions filtered by agent type."""
        session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="challenge",
            file_type="challenge",
        )
        session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="summary",
            file_type="summary",
        )

        sessions = session_concept.list_for_idea(idea_id, agent_type="challenge")

        assert len(sessions) == 1
        assert sessions[0].agent_type == "challenge"

    def test_get_or_create_creates_new(self, idea_id):
        """get_or_create creates a new session if none exists."""
        session = session_concept.get_or_create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="challenge",
            file_type="challenge",
        )

        assert session.id is not None
        assert session.agent_type == "challenge"

    def test_get_or_create_returns_existing(self, idea_id):
        """get_or_create returns existing session."""
        created = session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="challenge",
            file_type="challenge",
        )

        session = session_concept.get_or_create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="challenge",
            file_type="challenge",
        )

        assert session.id == created.id

    def test_add_message(self, idea_id):
        """Add a message to a session."""
        session = session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="challenge",
            file_type="challenge",
        )

        message = session_concept.add_message(
            session_id=session.id,
            role="user",
            content="Hello, agent!",
        )

        assert message.id is not None
        assert message.session_id == session.id
        assert message.role == "user"
        assert message.content == "Hello, agent!"

    def test_get_history(self, idea_id):
        """Get message history for a session."""
        session = session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="challenge",
            file_type="challenge",
        )

        # Add messages
        session_concept.add_message(session.id, "user", "First message")
        session_concept.add_message(session.id, "agent", "First response")
        session_concept.add_message(session.id, "user", "Second message")

        history = session_concept.get_history(session.id)

        assert len(history) == 3
        assert history[0].content == "First message"
        assert history[1].content == "First response"
        assert history[2].content == "Second message"

    def test_get_history_ordered_by_created_at(self, idea_id):
        """History is ordered by creation time."""
        session = session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="challenge",
            file_type="challenge",
        )

        session_concept.add_message(session.id, "user", "First")
        session_concept.add_message(session.id, "agent", "Second")
        session_concept.add_message(session.id, "user", "Third")

        history = session_concept.get_history(session.id)

        assert [m.content for m in history] == ["First", "Second", "Third"]
