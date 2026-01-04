"""ObjectiveAgent - helps define objectives and shows how ideas align with them."""

from dataclasses import dataclass
from uuid import UUID
import json
import structlog

from ...ai.gemini import generate_content, chat_with_history
from ...ai.prompts import (
    OBJECTIVE_AGENT_SYSTEM_PROMPT,
    OBJECTIVE_AGENT_ALIGNMENT_PROMPT,
    OBJECTIVE_AGENT_EVALUATION_PROMPT,
)
from ..objective import ObjectiveConcept
from ..objective_file import ObjectiveFileConcept
from ..session import session_concept

logger = structlog.get_logger()


@dataclass
class ObjectiveEvaluationResult:
    """Result of evaluating an objective."""

    is_clear: bool
    clear_feedback: str
    is_measurable: bool
    measurable_feedback: str
    is_time_bound: bool
    time_bound_feedback: str
    overall_feedback: str


class ObjectiveAgent:
    """
    Helps define organizational objectives and shows how ideas align with them.

    Unlike kernel file agents that focus on completing individual documents,
    ObjectiveAgent helps with strategic clarity and alignment analysis.
    """

    AGENT_TYPE = "objective"

    def __init__(self):
        self.objective_concept = ObjectiveConcept()
        self.objective_file_concept = ObjectiveFileConcept()

    async def evaluate(
        self, objective_id: UUID, content: str
    ) -> ObjectiveEvaluationResult:
        """
        Evaluate the objective content for clarity and completeness.

        Args:
            objective_id: The objective being evaluated
            content: The objective file content

        Returns:
            ObjectiveEvaluationResult with criterion assessments
        """
        prompt = OBJECTIVE_AGENT_EVALUATION_PROMPT.format(content=content)

        try:
            response = await generate_content(
                prompt,
                system_instruction=OBJECTIVE_AGENT_SYSTEM_PROMPT,
            )

            # Parse JSON response
            response = response.strip()
            if response.startswith("```"):
                # Remove code block markers
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            evaluation = json.loads(response)

            logger.info(
                "objective_evaluated",
                objective_id=str(objective_id),
                is_clear=evaluation.get("clear", False),
                is_measurable=evaluation.get("measurable", False),
                is_time_bound=evaluation.get("time_bound", False),
            )

            return ObjectiveEvaluationResult(
                is_clear=evaluation.get("clear", False),
                clear_feedback=evaluation.get("clear_feedback", ""),
                is_measurable=evaluation.get("measurable", False),
                measurable_feedback=evaluation.get("measurable_feedback", ""),
                is_time_bound=evaluation.get("time_bound", False),
                time_bound_feedback=evaluation.get("time_bound_feedback", ""),
                overall_feedback=evaluation.get("overall_feedback", ""),
            )

        except Exception as e:
            logger.error("objective_evaluation_error", error=str(e), objective_id=str(objective_id))
            return ObjectiveEvaluationResult(
                is_clear=False,
                clear_feedback="Unable to evaluate",
                is_measurable=False,
                measurable_feedback="Unable to evaluate",
                is_time_bound=False,
                time_bound_feedback="Unable to evaluate",
                overall_feedback=f"Evaluation failed: {str(e)}",
            )

    async def summarize_alignment(self, objective_id: UUID) -> str:
        """
        Summarize how linked ideas support this objective.

        Args:
            objective_id: The objective to analyze

        Returns:
            Analysis of idea alignment with the objective
        """
        # Get objective details
        objective = self.objective_concept.get(objective_id)
        if not objective:
            return "Objective not found."

        # Get objective file content
        objective_file = self.objective_file_concept.get(objective_id)
        objective_content = objective_file.content if objective_file else "_No objective description yet_"

        # Get linked ideas
        ideas = self.objective_concept.get_ideas(objective_id)

        if not ideas:
            return f"""## Alignment Summary for "{objective.title}"

No ideas are currently linked to this objective.

**Recommendation**: Start linking ideas that could contribute to achieving this objective. Consider:
- What initiatives are already underway that address this goal?
- What new ideas could be proposed to tackle this objective?
- What departments or teams should be encouraged to contribute?
"""

        # Format ideas for the prompt
        ideas_text = []
        for i, idea in enumerate(ideas, 1):
            completion = idea.get("kernel_completion", 0)
            ideas_text.append(f"""### Idea {i}: {idea.get("title", "Untitled")}
- Status: {idea.get("status", "unknown")}
- Kernel completion: {completion}/4
""")

        ideas_formatted = "\n".join(ideas_text)

        prompt = OBJECTIVE_AGENT_ALIGNMENT_PROMPT.format(
            objective_title=objective.title,
            timeframe=objective.timeframe or "Not specified",
            objective_content=objective_content,
            linked_ideas=ideas_formatted,
        )

        try:
            response = await generate_content(
                prompt,
                system_instruction=OBJECTIVE_AGENT_SYSTEM_PROMPT,
            )

            logger.info(
                "objective_alignment_summarized",
                objective_id=str(objective_id),
                linked_ideas_count=len(ideas),
            )

            return response

        except Exception as e:
            logger.error("alignment_summary_error", error=str(e), objective_id=str(objective_id))
            return f"Unable to generate alignment summary: {str(e)}"

    async def coach(
        self,
        objective_id: UUID,
        user_message: str,
        session_id: UUID,
    ) -> str:
        """
        Provide coaching guidance for objective development.

        Args:
            objective_id: The objective being coached
            user_message: The user's message
            session_id: The conversation session ID

        Returns:
            The agent's response
        """
        # Get objective details
        objective = self.objective_concept.get(objective_id)
        if not objective:
            return "I couldn't find this objective. It may have been deleted."

        # Get objective file content
        objective_file = self.objective_file_concept.get(objective_id)
        objective_content = objective_file.content if objective_file else "_Empty_"

        # Get linked ideas count
        ideas = self.objective_concept.get_ideas(objective_id)
        ideas_count = len(ideas)

        # Get session history
        history = session_concept.get_history(session_id)

        # Build context message
        context_message = f"""Here is the current state of the objective:

## Objective: {objective.title}
**Timeframe**: {objective.timeframe or "Not set"}
**Status**: {objective.status}
**Linked Ideas**: {ideas_count} idea(s) currently linked

## Objective.md Content
```markdown
{objective_content}
```

Please help define a clear, measurable, time-bound objective."""

        # Build messages for the LLM
        messages = [
            {"role": "user", "content": context_message},
            {"role": "agent", "content": "I've reviewed the objective. How can I help you refine it?"},
        ]

        # Add conversation history
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the new user message
        messages.append({"role": "user", "content": user_message})

        try:
            response = await chat_with_history(
                messages,
                system_instruction=OBJECTIVE_AGENT_SYSTEM_PROMPT,
            )

            logger.info(
                "objective_coach_response",
                objective_id=str(objective_id),
                session_id=str(session_id),
                message_length=len(response),
            )

            return response

        except Exception as e:
            logger.error("objective_coach_error", error=str(e), objective_id=str(objective_id))
            return "I'm having trouble responding right now. Please try again."


# Singleton instance
objective_agent = ObjectiveAgent()
