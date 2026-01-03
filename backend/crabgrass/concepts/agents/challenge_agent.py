"""ChallengeAgent - coaches users to articulate a specific, measurable, significant challenge."""

from dataclasses import dataclass
from uuid import UUID

import structlog

from ...ai.gemini import generate_json, chat_with_history
from ...ai.prompts import CHALLENGE_AGENT_SYSTEM_PROMPT, CHALLENGE_AGENT_EVALUATION_PROMPT
from ..kernel_file import KernelFileConcept
from ..session import session_concept

logger = structlog.get_logger()


@dataclass
class EvaluationResult:
    """Result of evaluating content against completion criteria."""

    is_complete: bool
    specific: bool
    measurable: bool
    significant: bool
    specific_feedback: str
    measurable_feedback: str
    significant_feedback: str
    overall_feedback: str


class ChallengeAgent:
    """Coaches users to articulate a specific, measurable, significant challenge."""

    AGENT_TYPE = "challenge"
    FILE_TYPE = "challenge"
    COMPLETION_CRITERIA = ["specific", "measurable", "significant"]

    def __init__(self):
        self.kernel_file_concept = KernelFileConcept()

    async def evaluate(self, idea_id: UUID, content: str) -> EvaluationResult:
        """
        Evaluate content against completion criteria.

        Returns an EvaluationResult indicating whether the challenge meets
        the specific, measurable, and significant criteria.
        """
        # Skip evaluation if content is essentially empty (just the template)
        if not content or len(content.strip()) < 100:
            return EvaluationResult(
                is_complete=False,
                specific=False,
                measurable=False,
                significant=False,
                specific_feedback="The challenge needs more detail.",
                measurable_feedback="Add measurable success criteria.",
                significant_feedback="Explain why this problem matters.",
                overall_feedback="The challenge is still in its early stages. Add more detail about the problem you're solving.",
            )

        prompt = CHALLENGE_AGENT_EVALUATION_PROMPT.format(content=content)

        try:
            result = await generate_json(prompt, system_instruction=CHALLENGE_AGENT_SYSTEM_PROMPT)

            is_complete = all(result.get(c, False) for c in self.COMPLETION_CRITERIA)

            logger.info(
                "challenge_evaluated",
                idea_id=str(idea_id),
                is_complete=is_complete,
                specific=result.get("specific"),
                measurable=result.get("measurable"),
                significant=result.get("significant"),
            )

            # If complete, mark the kernel file as complete
            if is_complete:
                self.kernel_file_concept.mark_complete(idea_id, self.FILE_TYPE)
                logger.info(
                    "challenge_marked_complete",
                    idea_id=str(idea_id),
                )

            return EvaluationResult(
                is_complete=is_complete,
                specific=result.get("specific", False),
                measurable=result.get("measurable", False),
                significant=result.get("significant", False),
                specific_feedback=result.get("specific_feedback", ""),
                measurable_feedback=result.get("measurable_feedback", ""),
                significant_feedback=result.get("significant_feedback", ""),
                overall_feedback=result.get("overall_feedback", ""),
            )

        except Exception as e:
            logger.error("challenge_evaluation_error", error=str(e), idea_id=str(idea_id))
            # Return a safe default on error
            return EvaluationResult(
                is_complete=False,
                specific=False,
                measurable=False,
                significant=False,
                specific_feedback="",
                measurable_feedback="",
                significant_feedback="",
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
        """
        # Get session history
        history = session_concept.get_history(session_id)

        # Build messages for the LLM
        messages = []

        # Add context about the current file content
        context_message = f"""Here is the current content of Challenge.md:

```markdown
{content}
```

Please help the user improve this challenge statement."""

        messages.append({"role": "user", "content": context_message})
        messages.append({"role": "agent", "content": "I've reviewed the Challenge.md content. How can I help you improve it?"})

        # Add conversation history
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the new user message
        messages.append({"role": "user", "content": user_message})

        try:
            response = await chat_with_history(
                messages,
                system_instruction=CHALLENGE_AGENT_SYSTEM_PROMPT,
            )

            logger.info(
                "challenge_coach_response",
                idea_id=str(idea_id),
                session_id=str(session_id),
                message_length=len(response),
            )

            return response

        except Exception as e:
            logger.error("challenge_coach_error", error=str(e), idea_id=str(idea_id))
            return "I'm having trouble responding right now. Please try again."


# Singleton instance
challenge_agent = ChallengeAgent()
