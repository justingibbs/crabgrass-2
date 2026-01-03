"""SummaryAgent - coaches users to write a clear, concise, compelling summary."""

from dataclasses import dataclass
from uuid import UUID

import structlog

from ...ai.gemini import generate_json, chat_with_history
from ...ai.prompts import SUMMARY_AGENT_SYSTEM_PROMPT, SUMMARY_AGENT_EVALUATION_PROMPT
from ..kernel_file import KernelFileConcept
from ..session import session_concept

logger = structlog.get_logger()


@dataclass
class EvaluationResult:
    """Result of evaluating content against completion criteria."""

    is_complete: bool
    clear: bool
    concise: bool
    compelling: bool
    clear_feedback: str
    concise_feedback: str
    compelling_feedback: str
    overall_feedback: str


class SummaryAgent:
    """Coaches users to write a clear, concise, compelling summary."""

    AGENT_TYPE = "summary"
    FILE_TYPE = "summary"
    COMPLETION_CRITERIA = ["clear", "concise", "compelling"]

    def __init__(self):
        self.kernel_file_concept = KernelFileConcept()

    async def evaluate(self, idea_id: UUID, content: str) -> EvaluationResult:
        """
        Evaluate content against completion criteria.

        Returns an EvaluationResult indicating whether the summary meets
        the clear, concise, and compelling criteria.
        """
        # Skip evaluation if content is essentially empty (just the template)
        if not content or len(content.strip()) < 100:
            return EvaluationResult(
                is_complete=False,
                clear=False,
                concise=False,
                compelling=False,
                clear_feedback="The summary needs more detail.",
                concise_feedback="Add the core idea first.",
                compelling_feedback="Explain why this idea matters.",
                overall_feedback="The summary is still in its early stages. Add more detail about what your idea is.",
            )

        prompt = SUMMARY_AGENT_EVALUATION_PROMPT.format(content=content)

        try:
            result = await generate_json(prompt, system_instruction=SUMMARY_AGENT_SYSTEM_PROMPT)

            is_complete = all(result.get(c, False) for c in self.COMPLETION_CRITERIA)

            logger.info(
                "summary_evaluated",
                idea_id=str(idea_id),
                is_complete=is_complete,
                clear=result.get("clear"),
                concise=result.get("concise"),
                compelling=result.get("compelling"),
            )

            # If complete, mark the kernel file as complete
            if is_complete:
                self.kernel_file_concept.mark_complete(idea_id, self.FILE_TYPE)
                logger.info(
                    "summary_marked_complete",
                    idea_id=str(idea_id),
                )

            return EvaluationResult(
                is_complete=is_complete,
                clear=result.get("clear", False),
                concise=result.get("concise", False),
                compelling=result.get("compelling", False),
                clear_feedback=result.get("clear_feedback", ""),
                concise_feedback=result.get("concise_feedback", ""),
                compelling_feedback=result.get("compelling_feedback", ""),
                overall_feedback=result.get("overall_feedback", ""),
            )

        except Exception as e:
            logger.error("summary_evaluation_error", error=str(e), idea_id=str(idea_id))
            # Return a safe default on error
            return EvaluationResult(
                is_complete=False,
                clear=False,
                concise=False,
                compelling=False,
                clear_feedback="",
                concise_feedback="",
                compelling_feedback="",
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
        context_message = f"""Here is the current content of Summary.md:

```markdown
{content}
```

Please help the user improve this summary."""

        messages.append({"role": "user", "content": context_message})
        messages.append({"role": "agent", "content": "I've reviewed the Summary.md content. How can I help you improve it?"})

        # Add conversation history
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the new user message
        messages.append({"role": "user", "content": user_message})

        try:
            response = await chat_with_history(
                messages,
                system_instruction=SUMMARY_AGENT_SYSTEM_PROMPT,
            )

            logger.info(
                "summary_coach_response",
                idea_id=str(idea_id),
                session_id=str(session_id),
                message_length=len(response),
            )

            return response

        except Exception as e:
            logger.error("summary_coach_error", error=str(e), idea_id=str(idea_id))
            return "I'm having trouble responding right now. Please try again."


# Singleton instance
summary_agent = SummaryAgent()
