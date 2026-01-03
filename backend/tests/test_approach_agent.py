"""Tests for the ApproachAgent."""

import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, AsyncMock
from uuid import uuid4

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_approach.duckdb")

from crabgrass.db.connection import get_connection, close_connection, reset_database
from crabgrass.db.migrations import run_migrations, SALLY_USER_ID
from crabgrass.concepts.agents.approach_agent import ApproachAgent, approach_agent
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
        title="Test Idea for Approach Agent",
    )
    on_idea_created(idea)
    return idea.id


class TestApproachAgentEvaluation:
    """Tests for ApproachAgent evaluation."""

    def test_agent_type_and_file_type(self):
        """Agent has correct type and file type."""
        assert approach_agent.AGENT_TYPE == "approach"
        assert approach_agent.FILE_TYPE == "approach"
        assert approach_agent.COMPLETION_CRITERIA == ["feasible", "differentiated", "addresses_challenge"]

    @pytest.mark.asyncio
    async def test_evaluate_empty_content(self, idea_id):
        """Evaluation of empty content returns incomplete."""
        result = await approach_agent.evaluate(idea_id, "")

        assert result.is_complete is False
        assert result.feasible is False
        assert result.differentiated is False
        assert result.addresses_challenge is False
        assert "early stages" in result.overall_feedback.lower()

    @pytest.mark.asyncio
    async def test_evaluate_short_content(self, idea_id):
        """Evaluation of short content returns incomplete."""
        result = await approach_agent.evaluate(idea_id, "Short text")

        assert result.is_complete is False
        assert "early stages" in result.overall_feedback.lower()

    @pytest.mark.asyncio
    async def test_evaluate_fetches_challenge_content(self, idea_id, kernel_file_concept):
        """Evaluation fetches Challenge.md content for context."""
        # Update the challenge file with specific content
        kernel_file_concept.update(
            idea_id=idea_id,
            file_type="challenge",
            content="Our challenge is reducing customer churn by 20%.",
            user_id=SALLY_USER_ID,
        )

        content = "A " * 100  # Approach content long enough to trigger evaluation

        with patch("crabgrass.concepts.agents.approach_agent.generate_json") as mock_gen:
            mock_gen.return_value = {
                "feasible": True,
                "feasible_feedback": "Can be done",
                "differentiated": False,
                "differentiated_feedback": "Needs unique angle",
                "addresses_challenge": True,
                "addresses_challenge_feedback": "Addresses churn",
                "overall_feedback": "Good but needs differentiation",
            }

            await approach_agent.evaluate(idea_id, content)

            # Check that the prompt included challenge content
            call_args = mock_gen.call_args
            prompt = call_args[0][0]  # First positional arg
            assert "reducing customer churn" in prompt

    @pytest.mark.asyncio
    async def test_evaluate_calls_gemini(self, idea_id):
        """Evaluation calls Gemini API with correct criteria."""
        content = "A " * 100

        with patch("crabgrass.concepts.agents.approach_agent.generate_json") as mock_gen:
            mock_gen.return_value = {
                "feasible": True,
                "feasible_feedback": "Feasible feedback",
                "differentiated": True,
                "differentiated_feedback": "Differentiated feedback",
                "addresses_challenge": False,
                "addresses_challenge_feedback": "Doesn't address the challenge",
                "overall_feedback": "Need to connect to challenge",
            }

            result = await approach_agent.evaluate(idea_id, content)

            assert mock_gen.called
            assert result.feasible is True
            assert result.differentiated is True
            assert result.addresses_challenge is False
            assert result.is_complete is False

    @pytest.mark.asyncio
    async def test_evaluate_marks_complete(self, idea_id, kernel_file_concept):
        """Evaluation marks file complete when all criteria met."""
        content = "A " * 100

        with patch("crabgrass.concepts.agents.approach_agent.generate_json") as mock_gen:
            mock_gen.return_value = {
                "feasible": True,
                "feasible_feedback": "Very feasible",
                "differentiated": True,
                "differentiated_feedback": "Unique approach",
                "addresses_challenge": True,
                "addresses_challenge_feedback": "Directly addresses problem",
                "overall_feedback": "Excellent approach!",
            }

            result = await approach_agent.evaluate(idea_id, content)

            assert result.is_complete is True

            # Check that the file was marked complete
            kernel_file = kernel_file_concept.get(idea_id, "approach")
            assert kernel_file.is_complete is True

    @pytest.mark.asyncio
    async def test_evaluate_handles_error(self, idea_id):
        """Evaluation handles API errors gracefully."""
        content = "A " * 100

        with patch("crabgrass.concepts.agents.approach_agent.generate_json") as mock_gen:
            mock_gen.side_effect = Exception("API Error")

            result = await approach_agent.evaluate(idea_id, content)

            assert result.is_complete is False
            assert "trouble evaluating" in result.overall_feedback.lower()


class TestApproachAgentCoaching:
    """Tests for ApproachAgent coaching."""

    @pytest.fixture
    def session_id(self, idea_id):
        """Create a test session and return its ID."""
        session = session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="approach",
            file_type="approach",
        )
        return session.id

    @pytest.mark.asyncio
    async def test_coach_returns_response(self, idea_id, session_id):
        """Coach returns a response."""
        with patch("crabgrass.concepts.agents.approach_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Here's how to improve your approach..."

            response = await approach_agent.coach(
                idea_id=idea_id,
                content="My current approach content",
                user_message="Is this feasible?",
                session_id=session_id,
            )

            assert response == "Here's how to improve your approach..."
            assert mock_chat.called

    @pytest.mark.asyncio
    async def test_coach_includes_challenge_context(self, idea_id, session_id, kernel_file_concept):
        """Coach includes Challenge.md content in context."""
        # Update the challenge file
        kernel_file_concept.update(
            idea_id=idea_id,
            file_type="challenge",
            content="The challenge is to improve user retention.",
            user_id=SALLY_USER_ID,
        )

        with patch("crabgrass.concepts.agents.approach_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Response"

            await approach_agent.coach(
                idea_id=idea_id,
                content="My approach content",
                user_message="Help please",
                session_id=session_id,
            )

            # Check that challenge content was included
            call_args = mock_chat.call_args
            messages = call_args[0][0]
            context_message = messages[0]["content"]
            assert "improve user retention" in context_message
            assert "Approach.md" in context_message
            assert "Challenge.md" in context_message

    @pytest.mark.asyncio
    async def test_coach_handles_error(self, idea_id, session_id):
        """Coach handles errors gracefully."""
        with patch("crabgrass.concepts.agents.approach_agent.chat_with_history") as mock_chat:
            mock_chat.side_effect = Exception("API Error")

            response = await approach_agent.coach(
                idea_id=idea_id,
                content="Content",
                user_message="Help",
                session_id=session_id,
            )

            assert "trouble responding" in response.lower()
