"""ApproachAgent - coaches users to design a feasible, differentiated approach that addresses the challenge."""

from dataclasses import dataclass
from uuid import UUID

import structlog

from ...ai.gemini import generate_json, chat_with_history
from ...ai.prompts import APPROACH_AGENT_SYSTEM_PROMPT, APPROACH_AGENT_EVALUATION_PROMPT
from ..kernel_file import KernelFileConcept
from ..session import session_concept

logger = structlog.get_logger()


@dataclass
class EvaluationResult:
    """Result of evaluating content against completion criteria."""

    is_complete: bool
    feasible: bool
    differentiated: bool
    addresses_challenge: bool
    feasible_feedback: str
    differentiated_feedback: str
    addresses_challenge_feedback: str
    overall_feedback: str


class ApproachAgent:
    """Coaches users to design a feasible, differentiated approach that addresses the challenge."""

    AGENT_TYPE = "approach"
    FILE_TYPE = "approach"
    COMPLETION_CRITERIA = ["feasible", "differentiated", "addresses_challenge"]

    def __init__(self):
        self.kernel_file_concept = KernelFileConcept()

    def _get_challenge_content(self, idea_id: UUID) -> str:
        """Fetch the Challenge.md content for context."""
        challenge_file = self.kernel_file_concept.get(idea_id, "challenge")
        if challenge_file:
            return challenge_file.content
        return ""

    async def evaluate(self, idea_id: UUID, content: str) -> EvaluationResult:
        """
        Evaluate content against completion criteria.

        Returns an EvaluationResult indicating whether the approach meets
        the feasible, differentiated, and addresses_challenge criteria.
        """
        # Skip evaluation if content is essentially empty (just the template)
        if not content or len(content.strip()) < 100:
            return EvaluationResult(
                is_complete=False,
                feasible=False,
                differentiated=False,
                addresses_challenge=False,
                feasible_feedback="The approach needs more detail.",
                differentiated_feedback="Explain what makes this approach unique.",
                addresses_challenge_feedback="Show how this addresses the challenge.",
                overall_feedback="The approach is still in its early stages. Add more detail about how you'll solve the problem.",
            )

        # Get challenge content for context
        challenge_content = self._get_challenge_content(idea_id)

        prompt = APPROACH_AGENT_EVALUATION_PROMPT.format(
            content=content,
            challenge_content=challenge_content or "(Challenge not yet defined)",
        )

        try:
            result = await generate_json(prompt, system_instruction=APPROACH_AGENT_SYSTEM_PROMPT)

            is_complete = all(result.get(c, False) for c in self.COMPLETION_CRITERIA)

            logger.info(
                "approach_evaluated",
                idea_id=str(idea_id),
                is_complete=is_complete,
                feasible=result.get("feasible"),
                differentiated=result.get("differentiated"),
                addresses_challenge=result.get("addresses_challenge"),
            )

            # If complete, mark the kernel file as complete
            if is_complete:
                self.kernel_file_concept.mark_complete(idea_id, self.FILE_TYPE)
                logger.info(
                    "approach_marked_complete",
                    idea_id=str(idea_id),
                )

            return EvaluationResult(
                is_complete=is_complete,
                feasible=result.get("feasible", False),
                differentiated=result.get("differentiated", False),
                addresses_challenge=result.get("addresses_challenge", False),
                feasible_feedback=result.get("feasible_feedback", ""),
                differentiated_feedback=result.get("differentiated_feedback", ""),
                addresses_challenge_feedback=result.get("addresses_challenge_feedback", ""),
                overall_feedback=result.get("overall_feedback", ""),
            )

        except Exception as e:
            logger.error("approach_evaluation_error", error=str(e), idea_id=str(idea_id))
            # Return a safe default on error
            return EvaluationResult(
                is_complete=False,
                feasible=False,
                differentiated=False,
                addresses_challenge=False,
                feasible_feedback="",
                differentiated_feedback="",
                addresses_challenge_feedback="",
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
        Includes Challenge.md content for reference.
        """
        # Get session history
        history = session_concept.get_history(session_id)

        # Get challenge content for context
        challenge_content = self._get_challenge_content(idea_id)

        # Build messages for the LLM
        messages = []

        # Add context about the current file content and challenge
        context_message = f"""Here is the current content of Approach.md:

```markdown
{content}
```

For reference, here is the Challenge.md content that this approach should address:

```markdown
{challenge_content or "(Challenge not yet defined)"}
```

Please help the user improve this approach."""

        messages.append({"role": "user", "content": context_message})
        messages.append({"role": "agent", "content": "I've reviewed both the Approach.md and Challenge.md content. How can I help you improve your approach?"})

        # Add conversation history
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the new user message
        messages.append({"role": "user", "content": user_message})

        try:
            response = await chat_with_history(
                messages,
                system_instruction=APPROACH_AGENT_SYSTEM_PROMPT,
            )

            logger.info(
                "approach_coach_response",
                idea_id=str(idea_id),
                session_id=str(session_id),
                message_length=len(response),
            )

            return response

        except Exception as e:
            logger.error("approach_coach_error", error=str(e), idea_id=str(idea_id))
            return "I'm having trouble responding right now. Please try again."


# Singleton instance
approach_agent = ApproachAgent()
