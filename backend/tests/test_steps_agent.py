"""Tests for the StepsAgent."""

import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, AsyncMock
from uuid import uuid4

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_steps.duckdb")

from crabgrass.db.connection import get_connection, close_connection, reset_database
from crabgrass.db.migrations import run_migrations, SALLY_USER_ID
from crabgrass.concepts.agents.steps_agent import StepsAgent, steps_agent
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
        title="Test Idea for Steps Agent",
    )
    on_idea_created(idea)
    return idea.id


class TestStepsAgentEvaluation:
    """Tests for StepsAgent evaluation."""

    def test_agent_type_and_file_type(self):
        """Agent has correct type and file type."""
        assert steps_agent.AGENT_TYPE == "steps"
        assert steps_agent.FILE_TYPE == "coherent_steps"
        assert steps_agent.COMPLETION_CRITERIA == ["concrete", "sequenced", "assignable"]

    @pytest.mark.asyncio
    async def test_evaluate_empty_content(self, idea_id):
        """Evaluation of empty content returns incomplete."""
        result = await steps_agent.evaluate(idea_id, "")

        assert result.is_complete is False
        assert result.concrete is False
        assert result.sequenced is False
        assert result.assignable is False
        assert "early stages" in result.overall_feedback.lower()

    @pytest.mark.asyncio
    async def test_evaluate_short_content(self, idea_id):
        """Evaluation of short content returns incomplete."""
        result = await steps_agent.evaluate(idea_id, "Short text")

        assert result.is_complete is False
        assert "early stages" in result.overall_feedback.lower()

    @pytest.mark.asyncio
    async def test_evaluate_fetches_approach_content(self, idea_id, kernel_file_concept):
        """Evaluation fetches Approach.md content for context."""
        # Update the approach file with specific content
        kernel_file_concept.update(
            idea_id=idea_id,
            file_type="approach",
            content="Our approach is to build a mobile-first solution with offline sync.",
            user_id=SALLY_USER_ID,
        )

        content = "A " * 100  # Steps content long enough to trigger evaluation

        with patch("crabgrass.concepts.agents.steps_agent.generate_json") as mock_gen:
            mock_gen.return_value = {
                "concrete": True,
                "concrete_feedback": "Steps are specific",
                "sequenced": False,
                "sequenced_feedback": "Order unclear",
                "assignable": True,
                "assignable_feedback": "Owners identified",
                "overall_feedback": "Good but needs sequencing",
            }

            await steps_agent.evaluate(idea_id, content)

            # Check that the prompt included approach content
            call_args = mock_gen.call_args
            prompt = call_args[0][0]  # First positional arg
            assert "mobile-first solution" in prompt

    @pytest.mark.asyncio
    async def test_evaluate_calls_gemini(self, idea_id):
        """Evaluation calls Gemini API with correct criteria."""
        content = "A " * 100

        with patch("crabgrass.concepts.agents.steps_agent.generate_json") as mock_gen:
            mock_gen.return_value = {
                "concrete": True,
                "concrete_feedback": "Concrete feedback",
                "sequenced": True,
                "sequenced_feedback": "Sequenced feedback",
                "assignable": False,
                "assignable_feedback": "No owners assigned",
                "overall_feedback": "Need to assign owners",
            }

            result = await steps_agent.evaluate(idea_id, content)

            assert mock_gen.called
            assert result.concrete is True
            assert result.sequenced is True
            assert result.assignable is False
            assert result.is_complete is False

    @pytest.mark.asyncio
    async def test_evaluate_marks_complete(self, idea_id, kernel_file_concept):
        """Evaluation marks file complete when all criteria met."""
        content = "A " * 100

        with patch("crabgrass.concepts.agents.steps_agent.generate_json") as mock_gen:
            mock_gen.return_value = {
                "concrete": True,
                "concrete_feedback": "Very specific",
                "sequenced": True,
                "sequenced_feedback": "Clear order",
                "assignable": True,
                "assignable_feedback": "All steps have owners",
                "overall_feedback": "Excellent steps!",
            }

            result = await steps_agent.evaluate(idea_id, content)

            assert result.is_complete is True

            # Check that the file was marked complete
            kernel_file = kernel_file_concept.get(idea_id, "coherent_steps")
            assert kernel_file.is_complete is True

    @pytest.mark.asyncio
    async def test_evaluate_handles_error(self, idea_id):
        """Evaluation handles API errors gracefully."""
        content = "A " * 100

        with patch("crabgrass.concepts.agents.steps_agent.generate_json") as mock_gen:
            mock_gen.side_effect = Exception("API Error")

            result = await steps_agent.evaluate(idea_id, content)

            assert result.is_complete is False
            assert "trouble evaluating" in result.overall_feedback.lower()


class TestStepsAgentCoaching:
    """Tests for StepsAgent coaching."""

    @pytest.fixture
    def session_id(self, idea_id):
        """Create a test session and return its ID."""
        session = session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="steps",
            file_type="coherent_steps",
        )
        return session.id

    @pytest.mark.asyncio
    async def test_coach_returns_response(self, idea_id, session_id):
        """Coach returns a response."""
        with patch("crabgrass.concepts.agents.steps_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Here's how to improve your steps..."

            response = await steps_agent.coach(
                idea_id=idea_id,
                content="My current steps content",
                user_message="Are these steps clear enough?",
                session_id=session_id,
            )

            assert response == "Here's how to improve your steps..."
            assert mock_chat.called

    @pytest.mark.asyncio
    async def test_coach_includes_approach_context(self, idea_id, session_id, kernel_file_concept):
        """Coach includes Approach.md content in context."""
        # Update the approach file
        kernel_file_concept.update(
            idea_id=idea_id,
            file_type="approach",
            content="The approach is to use microservices architecture.",
            user_id=SALLY_USER_ID,
        )

        with patch("crabgrass.concepts.agents.steps_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Response"

            await steps_agent.coach(
                idea_id=idea_id,
                content="My steps content",
                user_message="Help please",
                session_id=session_id,
            )

            # Check that approach content was included
            call_args = mock_chat.call_args
            messages = call_args[0][0]
            context_message = messages[0]["content"]
            assert "microservices architecture" in context_message
            assert "CoherentSteps.md" in context_message
            assert "Approach.md" in context_message

    @pytest.mark.asyncio
    async def test_coach_handles_error(self, idea_id, session_id):
        """Coach handles errors gracefully."""
        with patch("crabgrass.concepts.agents.steps_agent.chat_with_history") as mock_chat:
            mock_chat.side_effect = Exception("API Error")

            response = await steps_agent.coach(
                idea_id=idea_id,
                content="Content",
                user_message="Help",
                session_id=session_id,
            )

            assert "trouble responding" in response.lower()
