"""CoherenceAgent - ensures all kernel files tell a consistent, coherent story."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import structlog

from ...ai.gemini import generate_content, chat_with_history
from ...ai.prompts import COHERENCE_AGENT_SYSTEM_PROMPT, COHERENCE_AGENT_EVALUATION_PROMPT
from ..kernel_file import KernelFileConcept
from ..context_file import context_file_concept
from ..session import session_concept

logger = structlog.get_logger()

# The filename for coherence feedback
FEEDBACK_TASKS_FILENAME = "feedback-tasks.md"


@dataclass
class CoherenceEvaluationResult:
    """Result of evaluating coherence across kernel files."""

    feedback_content: str
    kernel_complete_count: int
    idea_id: UUID


class CoherenceAgent:
    """
    Ensures all kernel files tell a consistent, coherent story.

    Unlike other agents that work on individual files, CoherenceAgent
    operates at the idea level, checking logical connections between
    all four kernel files.
    """

    AGENT_TYPE = "coherence"

    def __init__(self):
        self.kernel_file_concept = KernelFileConcept()

    def _get_all_kernel_content(self, idea_id: UUID) -> dict[str, str]:
        """
        Get all kernel file content for an idea.

        Returns:
            Dict mapping file_type to content
        """
        content = {}
        for file_type in ["summary", "challenge", "approach", "coherent_steps"]:
            kernel_file = self.kernel_file_concept.get(idea_id, file_type)
            if kernel_file:
                content[file_type] = kernel_file.content or ""
            else:
                content[file_type] = ""
        return content

    def _get_kernel_complete_count(self, idea_id: UUID) -> int:
        """Get the count of completed kernel files."""
        count = 0
        for file_type in ["summary", "challenge", "approach", "coherent_steps"]:
            kernel_file = self.kernel_file_concept.get(idea_id, file_type)
            if kernel_file and kernel_file.is_complete:
                count += 1
        return count

    def _get_existing_feedback(self, idea_id: UUID) -> str:
        """Get existing feedback-tasks.md content if it exists."""
        feedback_file = context_file_concept.get(idea_id, FEEDBACK_TASKS_FILENAME)
        if feedback_file:
            return feedback_file.content
        return "No previous feedback available."

    async def evaluate(self, idea_id: UUID) -> CoherenceEvaluationResult:
        """
        Evaluate coherence across all kernel files.

        Generates or updates the feedback-tasks.md context file with
        coherence assessment and recommended tasks.

        Args:
            idea_id: The idea to evaluate

        Returns:
            CoherenceEvaluationResult with the generated feedback
        """
        # Get all kernel file content
        kernel_content = self._get_all_kernel_content(idea_id)
        complete_count = self._get_kernel_complete_count(idea_id)
        previous_feedback = self._get_existing_feedback(idea_id)

        # Format the timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Build the evaluation prompt
        prompt = COHERENCE_AGENT_EVALUATION_PROMPT.format(
            summary_content=kernel_content.get("summary", "_Empty_"),
            challenge_content=kernel_content.get("challenge", "_Empty_"),
            approach_content=kernel_content.get("approach", "_Empty_"),
            steps_content=kernel_content.get("coherent_steps", "_Empty_"),
            previous_feedback=previous_feedback,
            timestamp=timestamp,
            complete_count=complete_count,
        )

        try:
            # Generate the feedback content
            feedback_content = await generate_content(
                prompt,
                system_instruction=COHERENCE_AGENT_SYSTEM_PROMPT,
            )

            # Clean up the response - remove markdown code blocks if present
            feedback_content = feedback_content.strip()
            if feedback_content.startswith("```markdown"):
                feedback_content = feedback_content[len("```markdown"):].strip()
            if feedback_content.startswith("```"):
                feedback_content = feedback_content[3:].strip()
            if feedback_content.endswith("```"):
                feedback_content = feedback_content[:-3].strip()

            # Create or update the feedback-tasks.md file
            context_file_concept.create_or_update(
                idea_id=idea_id,
                filename=FEEDBACK_TASKS_FILENAME,
                content=feedback_content,
                user_id=None,
                created_by_agent=True,
            )

            logger.info(
                "coherence_evaluated",
                idea_id=str(idea_id),
                kernel_complete=complete_count,
            )

            return CoherenceEvaluationResult(
                feedback_content=feedback_content,
                kernel_complete_count=complete_count,
                idea_id=idea_id,
            )

        except Exception as e:
            logger.error("coherence_evaluation_error", error=str(e), idea_id=str(idea_id))

            # Return a basic feedback file on error
            error_feedback = f"""# Idea Feedback & Tasks

*Last evaluated: {timestamp}*
*Kernel files complete: {complete_count}/4*

## Coherence Assessment

Unable to complete evaluation at this time. Please try again later.

Error: {str(e)}
"""
            return CoherenceEvaluationResult(
                feedback_content=error_feedback,
                kernel_complete_count=complete_count,
                idea_id=idea_id,
            )

    async def coach(
        self,
        idea_id: UUID,
        user_message: str,
        session_id: UUID,
    ) -> str:
        """
        Provide coaching guidance for overall idea development.

        Uses all kernel files and feedback-tasks.md for context.

        Args:
            idea_id: The idea being coached
            user_message: The user's message
            session_id: The conversation session ID

        Returns:
            The agent's response
        """
        # Get all kernel file content for context
        kernel_content = self._get_all_kernel_content(idea_id)

        # Get existing feedback file
        feedback_content = self._get_existing_feedback(idea_id)

        # Get session history
        history = session_concept.get_history(session_id)

        # Build context message
        context_message = f"""Here is the current state of the idea:

## Summary.md
```markdown
{kernel_content.get("summary", "_Empty_")}
```

## Challenge.md
```markdown
{kernel_content.get("challenge", "_Empty_")}
```

## Approach.md
```markdown
{kernel_content.get("approach", "_Empty_")}
```

## CoherentSteps.md
```markdown
{kernel_content.get("coherent_steps", "_Empty_")}
```

## Current Feedback (feedback-tasks.md)
```markdown
{feedback_content}
```

Please help the user develop a coherent, impactful idea."""

        # Build messages for the LLM
        messages = [
            {"role": "user", "content": context_message},
            {"role": "agent", "content": "I've reviewed all the kernel files and the current feedback. How can I help you develop your idea?"},
        ]

        # Add conversation history
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the new user message
        messages.append({"role": "user", "content": user_message})

        try:
            response = await chat_with_history(
                messages,
                system_instruction=COHERENCE_AGENT_SYSTEM_PROMPT,
            )

            logger.info(
                "coherence_coach_response",
                idea_id=str(idea_id),
                session_id=str(session_id),
                message_length=len(response),
            )

            return response

        except Exception as e:
            logger.error("coherence_coach_error", error=str(e), idea_id=str(idea_id))
            return "I'm having trouble responding right now. Please try again."


# Singleton instance
coherence_agent = CoherenceAgent()
