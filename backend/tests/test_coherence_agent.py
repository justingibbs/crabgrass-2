"""Tests for the CoherenceAgent."""

import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, AsyncMock
from uuid import uuid4

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_coherence.duckdb")
os.environ["STORAGE_ROOT"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_storage")

from crabgrass.db.connection import get_connection, close_connection, reset_database
from crabgrass.db.migrations import run_migrations, SALLY_USER_ID, ACME_ORG_ID
from crabgrass.concepts.agents.coherence_agent import CoherenceAgent, coherence_agent, FEEDBACK_TASKS_FILENAME
from crabgrass.concepts.idea import IdeaConcept
from crabgrass.concepts.kernel_file import KernelFileConcept
from crabgrass.concepts.context_file import context_file_concept
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
    idea = idea_concept.create(
        org_id=ACME_ORG_ID,
        user_id=SALLY_USER_ID,
        title="Test Idea for Coherence Agent",
    )
    on_idea_created(idea)
    return idea.id


class TestCoherenceAgentEvaluation:
    """Tests for CoherenceAgent evaluation."""

    def test_agent_type(self):
        """Agent has correct type."""
        assert coherence_agent.AGENT_TYPE == "coherence"

    @pytest.mark.asyncio
    async def test_evaluate_creates_feedback_file(self, idea_id):
        """Evaluation creates feedback-tasks.md file."""
        with patch("crabgrass.concepts.agents.coherence_agent.generate_content") as mock_gen:
            mock_gen.return_value = """# Idea Feedback & Tasks

*Last evaluated: 2026-01-03 12:00 UTC*
*Kernel files complete: 0/4*

## Coherence Assessment

### What's Working
- Good initial structure

### Areas for Improvement
- Challenge needs more specificity

## Recommended Tasks

### High Priority
- [ ] Define the core challenge more clearly

### Next Steps
- [ ] Start with Challenge.md
"""
            result = await coherence_agent.evaluate(idea_id)

            assert result.idea_id == idea_id
            assert "Idea Feedback" in result.feedback_content

            # Check that file was created
            feedback_file = context_file_concept.get(idea_id, FEEDBACK_TASKS_FILENAME)
            assert feedback_file is not None
            assert feedback_file.created_by_agent is True

    @pytest.mark.asyncio
    async def test_evaluate_updates_existing_feedback_file(self, idea_id):
        """Evaluation updates existing feedback-tasks.md file."""
        # Create initial feedback file
        context_file_concept.create(
            idea_id=idea_id,
            filename=FEEDBACK_TASKS_FILENAME,
            content="# Initial Feedback\n\nOld content",
            created_by_agent=True,
        )

        with patch("crabgrass.concepts.agents.coherence_agent.generate_content") as mock_gen:
            mock_gen.return_value = "# Updated Feedback\n\nNew content"

            await coherence_agent.evaluate(idea_id)

            # Check that file was updated
            feedback_file = context_file_concept.get(idea_id, FEEDBACK_TASKS_FILENAME)
            assert "Updated Feedback" in feedback_file.content

    @pytest.mark.asyncio
    async def test_evaluate_strips_markdown_code_blocks(self, idea_id):
        """Evaluation strips markdown code blocks from response."""
        with patch("crabgrass.concepts.agents.coherence_agent.generate_content") as mock_gen:
            mock_gen.return_value = """```markdown
# Idea Feedback & Tasks

Content here
```"""
            result = await coherence_agent.evaluate(idea_id)

            # Should not have the code block markers
            assert not result.feedback_content.startswith("```")
            assert not result.feedback_content.endswith("```")
            assert "# Idea Feedback" in result.feedback_content

    @pytest.mark.asyncio
    async def test_evaluate_handles_error(self, idea_id):
        """Evaluation handles API errors gracefully."""
        with patch("crabgrass.concepts.agents.coherence_agent.generate_content") as mock_gen:
            mock_gen.side_effect = Exception("API Error")

            result = await coherence_agent.evaluate(idea_id)

            assert result.idea_id == idea_id
            assert "Unable to complete evaluation" in result.feedback_content

    @pytest.mark.asyncio
    async def test_evaluate_includes_kernel_content(self, idea_id, kernel_file_concept):
        """Evaluation includes all kernel file content in prompt."""
        # Update a kernel file
        kernel_file_concept.update(
            idea_id, "challenge", "# Challenge\n\nReduce checkout abandonment by 50%", SALLY_USER_ID
        )

        with patch("crabgrass.concepts.agents.coherence_agent.generate_content") as mock_gen:
            mock_gen.return_value = "# Feedback"

            await coherence_agent.evaluate(idea_id)

            # Check that the prompt included the challenge content
            call_args = mock_gen.call_args
            prompt = call_args[0][0]  # First positional arg
            assert "checkout abandonment" in prompt


class TestCoherenceAgentCoaching:
    """Tests for CoherenceAgent coaching."""

    @pytest.fixture
    def session_id(self, idea_id):
        """Create a test session and return its ID."""
        session = session_concept.create(
            idea_id=idea_id,
            user_id=SALLY_USER_ID,
            agent_type="coherence",
            file_type=None,  # CoherenceAgent is idea-level
        )
        return session.id

    @pytest.mark.asyncio
    async def test_coach_returns_response(self, idea_id, session_id):
        """Coach returns a response."""
        with patch("crabgrass.concepts.agents.coherence_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Based on your kernel files, I suggest focusing on..."

            response = await coherence_agent.coach(
                idea_id=idea_id,
                user_message="What should I work on next?",
                session_id=session_id,
            )

            assert "suggest focusing" in response
            assert mock_chat.called

    @pytest.mark.asyncio
    async def test_coach_includes_all_kernel_files(self, idea_id, session_id, kernel_file_concept):
        """Coach includes all kernel file content in context."""
        # Update kernel files with specific content
        kernel_file_concept.update(
            idea_id, "summary", "# Summary\n\nThis is a mobile app", SALLY_USER_ID
        )
        kernel_file_concept.update(
            idea_id, "challenge", "# Challenge\n\nUsers abandon carts", SALLY_USER_ID
        )

        with patch("crabgrass.concepts.agents.coherence_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Response"

            await coherence_agent.coach(
                idea_id=idea_id,
                user_message="Help me",
                session_id=session_id,
            )

            # Check that kernel content was included
            call_args = mock_chat.call_args
            messages = call_args[0][0]
            context_message = messages[0]["content"]

            assert "mobile app" in context_message
            assert "abandon carts" in context_message

    @pytest.mark.asyncio
    async def test_coach_includes_feedback_file(self, idea_id, session_id):
        """Coach includes feedback-tasks.md in context."""
        # Create feedback file
        context_file_concept.create(
            idea_id=idea_id,
            filename=FEEDBACK_TASKS_FILENAME,
            content="# Feedback\n\n- Work on Challenge.md next",
            created_by_agent=True,
        )

        with patch("crabgrass.concepts.agents.coherence_agent.chat_with_history") as mock_chat:
            mock_chat.return_value = "Response"

            await coherence_agent.coach(
                idea_id=idea_id,
                user_message="What's next?",
                session_id=session_id,
            )

            # Check that feedback was included
            call_args = mock_chat.call_args
            messages = call_args[0][0]
            context_message = messages[0]["content"]

            assert "Work on Challenge.md next" in context_message

    @pytest.mark.asyncio
    async def test_coach_handles_error(self, idea_id, session_id):
        """Coach handles errors gracefully."""
        with patch("crabgrass.concepts.agents.coherence_agent.chat_with_history") as mock_chat:
            mock_chat.side_effect = Exception("API Error")

            response = await coherence_agent.coach(
                idea_id=idea_id,
                user_message="Help",
                session_id=session_id,
            )

            assert "trouble responding" in response.lower()


class TestCoherenceAgentHelpers:
    """Tests for CoherenceAgent helper methods."""

    def test_get_all_kernel_content(self, idea_id, kernel_file_concept):
        """Helper gets all kernel file content."""
        kernel_file_concept.update(
            idea_id, "summary", "Summary content", SALLY_USER_ID
        )

        content = coherence_agent._get_all_kernel_content(idea_id)

        assert "summary" in content
        assert "challenge" in content
        assert "approach" in content
        assert "coherent_steps" in content
        assert content["summary"] == "Summary content"

    def test_get_kernel_complete_count(self, idea_id, kernel_file_concept):
        """Helper gets correct completion count."""
        assert coherence_agent._get_kernel_complete_count(idea_id) == 0

        kernel_file_concept.mark_complete(idea_id, "summary")
        kernel_file_concept.mark_complete(idea_id, "challenge")

        assert coherence_agent._get_kernel_complete_count(idea_id) == 2

    def test_get_existing_feedback_returns_content(self, idea_id):
        """Helper returns existing feedback content."""
        context_file_concept.create(
            idea_id=idea_id,
            filename=FEEDBACK_TASKS_FILENAME,
            content="Existing feedback",
            created_by_agent=True,
        )

        feedback = coherence_agent._get_existing_feedback(idea_id)
        assert feedback == "Existing feedback"

    def test_get_existing_feedback_returns_default(self, idea_id):
        """Helper returns default message when no feedback exists."""
        feedback = coherence_agent._get_existing_feedback(idea_id)
        assert "No previous feedback" in feedback
