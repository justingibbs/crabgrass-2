"""StepsAgent - coaches users to break down their approach into concrete, sequenced, assignable steps."""

from dataclasses import dataclass
from uuid import UUID

import structlog

from ...ai.gemini import generate_json, chat_with_history
from ...ai.prompts import STEPS_AGENT_SYSTEM_PROMPT, STEPS_AGENT_EVALUATION_PROMPT
from ..kernel_file import KernelFileConcept
from ..session import session_concept

logger = structlog.get_logger()


@dataclass
class EvaluationResult:
    """Result of evaluating content against completion criteria."""

    is_complete: bool
    concrete: bool
    sequenced: bool
    assignable: bool
    concrete_feedback: str
    sequenced_feedback: str
    assignable_feedback: str
    overall_feedback: str


class StepsAgent:
    """Coaches users to break down their approach into concrete, sequenced, assignable steps."""

    AGENT_TYPE = "steps"
    FILE_TYPE = "coherent_steps"
    COMPLETION_CRITERIA = ["concrete", "sequenced", "assignable"]

    def __init__(self):
        self.kernel_file_concept = KernelFileConcept()

    def _get_approach_content(self, idea_id: UUID) -> str:
        """Fetch the Approach.md content for context."""
        approach_file = self.kernel_file_concept.get(idea_id, "approach")
        if approach_file:
            return approach_file.content
        return ""

    async def evaluate(self, idea_id: UUID, content: str) -> EvaluationResult:
        """
        Evaluate content against completion criteria.

        Returns an EvaluationResult indicating whether the steps meet
        the concrete, sequenced, and assignable criteria.
        """
        # Skip evaluation if content is essentially empty (just the template)
        if not content or len(content.strip()) < 100:
            return EvaluationResult(
                is_complete=False,
                concrete=False,
                sequenced=False,
                assignable=False,
                concrete_feedback="The steps need more detail.",
                sequenced_feedback="Define the order of operations.",
                assignable_feedback="Identify who will do each step.",
                overall_feedback="The steps are still in their early stages. Add specific, actionable tasks.",
            )

        # Get approach content for context
        approach_content = self._get_approach_content(idea_id)

        prompt = STEPS_AGENT_EVALUATION_PROMPT.format(
            content=content,
            approach_content=approach_content or "(Approach not yet defined)",
        )

        try:
            result = await generate_json(prompt, system_instruction=STEPS_AGENT_SYSTEM_PROMPT)

            is_complete = all(result.get(c, False) for c in self.COMPLETION_CRITERIA)

            logger.info(
                "steps_evaluated",
                idea_id=str(idea_id),
                is_complete=is_complete,
                concrete=result.get("concrete"),
                sequenced=result.get("sequenced"),
                assignable=result.get("assignable"),
            )

            # If complete, mark the kernel file as complete
            if is_complete:
                self.kernel_file_concept.mark_complete(idea_id, self.FILE_TYPE)
                logger.info(
                    "steps_marked_complete",
                    idea_id=str(idea_id),
                )

            return EvaluationResult(
                is_complete=is_complete,
                concrete=result.get("concrete", False),
                sequenced=result.get("sequenced", False),
                assignable=result.get("assignable", False),
                concrete_feedback=result.get("concrete_feedback", ""),
                sequenced_feedback=result.get("sequenced_feedback", ""),
                assignable_feedback=result.get("assignable_feedback", ""),
                overall_feedback=result.get("overall_feedback", ""),
            )

        except Exception as e:
            logger.error("steps_evaluation_error", error=str(e), idea_id=str(idea_id))
            # Return a safe default on error
            return EvaluationResult(
                is_complete=False,
                concrete=False,
                sequenced=False,
                assignable=False,
                concrete_feedback="",
                sequenced_feedback="",
                assignable_feedback="",
                overall_feedback="I had trouble evaluating this. Please try again.",
            )

    async def coach(
        self,
        idea_id: UUID,
        content: str,
        user_message: str,
        session_id: UUID,
    ) -> str:
        """
        Provide coaching guidance in response to a user message.

        Uses conversation history from the session for context.
        Includes Approach.md content for reference.
        """
        # Get session history
        history = session_concept.get_history(session_id)

        # Get approach content for context
        approach_content = self._get_approach_content(idea_id)

        # Build messages for the LLM
        messages = []

        # Add context about the current file content and approach
        context_message = f"""Here is the current content of CoherentSteps.md:

```markdown
{content}
```

For reference, here is the Approach.md content that these steps should implement:

```markdown
{approach_content or "(Approach not yet defined)"}
```

Please help the user improve these steps."""

        messages.append({"role": "user", "content": context_message})
        messages.append({"role": "agent", "content": "I've reviewed both the CoherentSteps.md and Approach.md content. How can I help you improve your next steps?"})

        # Add conversation history
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the new user message
        messages.append({"role": "user", "content": user_message})

        try:
            response = await chat_with_history(
                messages,
                system_instruction=STEPS_AGENT_SYSTEM_PROMPT,
            )

            logger.info(
                "steps_coach_response",
                idea_id=str(idea_id),
                session_id=str(session_id),
                message_length=len(response),
            )

            return response

        except Exception as e:
            logger.error("steps_coach_error", error=str(e), idea_id=str(idea_id))
            return "I'm having trouble responding right now. Please try again."


# Singleton instance
steps_agent = StepsAgent()
