"""Tests for the SummaryAgent."""

import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, AsyncMock
from uuid import uuid4

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_summary.duckdb")

from crabgrass.db.connection import get_connection, close_connection, reset_database
from crabgrass.db.migrations import run_migrations, SALLY_USER_ID
from crabgrass.concepts.agents.summary_agent import SummaryAgent, summary_agent
from crabgrass.concepts.idea import IdeaConcept
from crabgrass.concepts.kernel_file import KernelFileConcept
from crabgrass.concepts.session import session_concept
from crabgrass.sync.synchronizations import on_idea_created


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
def kernel_file_concept():
    return KernelFileConcept()


@pytest.fixture
def idea_id(idea_concept):
    """Create a test idea and return its ID."""
    from crabgrass.db.connection import get_db

    with get_db() as db:
        result = db.execute(
            "SELECT org_id FROM users WHERE id = ?",
            [str(SALLY_USER_ID)],
        ).fetchone()
        org_id = result[0]

    idea = idea_concept.create(
        org_id=org_id,
        user_id=SALLY_USER_ID,
        title="Test Idea for Summary Agent",
    )
    on_idea_created(idea)
    return idea.id


class TestSummaryAgentEvaluation:
    """Tests for SummaryAgent evaluation."""

    def test_agent_type_and_file_type(self):
        """Agent has correct type and file type."""
        assert summary_agent.AGENT_TYPE == "summary"
        assert summary_agent.FILE_TYPE == "summary"
        assert summary_agent.COMPLETION_CRITERIA == ["clear", "concise", "compelling"]

    @pytest.mark.asyncio
    async def test_evaluate_empty_content(self, idea_id):
        """Evaluation of empty content returns incomplete."""
        result = await summary_agent.evaluate(idea_id, "")

        assert result.is_complete is False
        assert result.clear is False
        assert result.concise is False
        assert result.compelling is False
        assert "early stages" in result.overall_feedback.lower()

    @pytest.mark.asyncio
    async def test_evaluate_short_content(self, idea_id):
        """Evaluation of short content returns incomplete."""
        result = await summary_agent.evaluate(idea_id, "Short text")

        assert result.is_complete is False
        assert "early stages" in result.overall_feedback.lower()

    @pytest.mark.asyncio
    async def test_evaluate_calls_gemini(self, idea_id):
        """Evaluation calls Gemini API with correct prompt."""
        content = "A " * 100  # Content long enough to trigger evaluation

        with patch("crabgrass.concepts.agents.summary_agent.generate_json") as mock_gen:
            mock_gen.return_value = {
                "clear": True,
                "clear_feedback": "Clear feedback",
                "concise": True,
                "concise_feedback": "Concise feedback",
                "compelling": False,
                "compelling_feedback": "Needs to be more compelling",
                "overall_feedback": "Good start, needs more compelling angle",
            }

            result = await summary_agent.evaluate(idea_id, content)

            assert mock_gen.called
            assert result.clear is True
            assert result.concise is True
            assert result.compelling is False
            assert result.is_complete is False

    @pytest.mark.asyncio
    async def test_evaluate_marks_complete(self, idea_id, kernel_file_concept):
        """Evaluation marks file complete when all criteria met."""
        content = "A " * 100

        with patch("crabgrass.concepts.agents.summary_agent.generate_json") as mock_gen:
            mock_gen.return_value = {
                "clear": True,
                "clear_feedback": "Very clear",
                "concise": True,
                "concise_feedback": "Nice and brief",
                "compelling": True,
                "compelling_feedback": "Makes me want to learn more",
                "overall_feedback": "Excellent summary!",
            }

            result = await summary_agent.evaluate(idea_id, content)

            assert result.is_complete is True

            # Check that the file was marked complete
            kernel_file = kernel_file_concept.get(idea_id, "summary")
            assert kernel_file.is_complete is True

    @pytest.mark.asyncio
    async def test_evaluate_handles_error(self, idea_id):
        """Evaluation handles API errors gracefully."""
        content = "A " * 100

        with patch("crabgrass.concepts.agents.summary_agent.generate_json") as mock_gen:
            mock_gen.side_effect = Exception("API Error")

            result = await summary_agent.evaluate(idea_id, content)

            assert result.is_complete is False
            assert "trouble evaluating" in result.overall_feedback.lower()


class TestSummaryAgentCoaching:
    """Tests for SummaryAgent coaching."""

    @pytest.fixture
    def session_id(self, idea_id):
        """Create a test session and return its ID."""
        session = session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="summary",
            file_type="summary",
        )
        return session.id

    @pytest.mark.asyncio
    async def test_coach_returns_response(self, idea_id, session_id):
        """Coach returns a response."""
        with patch("crabgrass.concepts.agents.summary_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Here's how to improve your summary..."

            response = await summary_agent.coach(
                idea_id=idea_id,
                content="My current summary content",
                user_message="How can I make this clearer?",
                session_id=session_id,
            )

            assert response == "Here's how to improve your summary..."
            assert mock_chat.called

    @pytest.mark.asyncio
    async def test_coach_includes_content_context(self, idea_id, session_id):
        """Coach includes file content in context."""
        with patch("crabgrass.concepts.agents.summary_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Response"

            await summary_agent.coach(
                idea_id=idea_id,
                content="My specific summary content here",
                user_message="Help please",
                session_id=session_id,
            )

            # Check that content was included in the messages
            call_args = mock_chat.call_args
            messages = call_args[0][0]  # First positional arg
            context_message = messages[0]["content"]
            assert "My specific summary content here" in context_message

    @pytest.mark.asyncio
    async def test_coach_handles_error(self, idea_id, session_id):
        """Coach handles errors gracefully."""
        with patch("crabgrass.concepts.agents.summary_agent.chat_with_history") as mock_chat:
            mock_chat.side_effect = Exception("API Error")

            response = await summary_agent.coach(
                idea_id=idea_id,
                content="Content",
                user_message="Help",
                session_id=session_id,
            )

            assert "trouble responding" in response.lower()
