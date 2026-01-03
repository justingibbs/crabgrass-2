"""ContextAgent - extracts insights from context files to strengthen kernel files."""

from dataclasses import dataclass
from uuid import UUID
from typing import Optional

import structlog

from ...ai.gemini import generate_json, generate_content, chat_with_history
from ...ai.prompts import (
    CONTEXT_AGENT_SYSTEM_PROMPT,
    CONTEXT_AGENT_EXTRACTION_PROMPT,
    CONTEXT_AGENT_SUMMARY_PROMPT,
)
from ..kernel_file import KernelFileConcept
from ..context_file import context_file_concept
from ..session import session_concept

logger = structlog.get_logger()


@dataclass
class Insight:
    """A single insight extracted from a context file."""

    quote: str
    relevance: str  # Which kernel file(s) this relates to
    suggestion: str  # How to use this insight


@dataclass
class ExtractionResult:
    """Result of extracting insights from a context file."""

    summary: str
    insights: list[Insight]


class ContextAgent:
    """
    Extracts insights from context files to strengthen kernel files.

    The ContextAgent helps users:
    - Understand what's in their context files
    - Extract key insights relevant to their idea
    - Map insights to specific kernel files
    - Incorporate insights into their kernel files
    """

    AGENT_TYPE = "context"

    def __init__(self):
        self.kernel_file_concept = KernelFileConcept()

    async def extract(self, idea_id: UUID, context_file_id: UUID) -> ExtractionResult:
        """
        Extract insights from a context file.

        Analyzes the file content and identifies key points that could
        strengthen the idea's kernel files.

        Args:
            idea_id: The idea UUID
            context_file_id: The context file UUID

        Returns:
            ExtractionResult with summary and list of insights
        """
        # Get the context file
        context_file = context_file_concept.get_by_id(context_file_id)
        if not context_file:
            return ExtractionResult(
                summary="File not found",
                insights=[],
            )

        # Get kernel file completion status
        kernel_files = self.kernel_file_concept.get_all(idea_id)
        completion_status = {kf.file_type: kf.is_complete for kf in kernel_files}

        # Build the extraction prompt
        prompt = CONTEXT_AGENT_EXTRACTION_PROMPT.format(
            filename=context_file.filename,
            content=context_file.content,
            summary_complete=completion_status.get("summary", False),
            challenge_complete=completion_status.get("challenge", False),
            approach_complete=completion_status.get("approach", False),
            steps_complete=completion_status.get("coherent_steps", False),
        )

        try:
            result = await generate_json(
                prompt,
                system_instruction=CONTEXT_AGENT_SYSTEM_PROMPT,
            )

            insights = [
                Insight(
                    quote=i.get("quote", ""),
                    relevance=i.get("relevance", ""),
                    suggestion=i.get("suggestion", ""),
                )
                for i in result.get("insights", [])
            ]

            logger.info(
                "context_file_insights_extracted",
                idea_id=str(idea_id),
                context_file_id=str(context_file_id),
                filename=context_file.filename,
                insight_count=len(insights),
            )

            return ExtractionResult(
                summary=result.get("summary", ""),
                insights=insights,
            )

        except Exception as e:
            logger.error(
                "context_extraction_error",
                error=str(e),
                idea_id=str(idea_id),
                context_file_id=str(context_file_id),
            )
            return ExtractionResult(
                summary="Error extracting insights",
                insights=[],
            )

    async def summarize(self, idea_id: UUID, context_file_id: UUID) -> str:
        """
        Generate a brief summary of a context file.

        Args:
            idea_id: The idea UUID
            context_file_id: The context file UUID

        Returns:
            A 2-3 sentence summary of the file
        """
        # Get the context file
        context_file = context_file_concept.get_by_id(context_file_id)
        if not context_file:
            return "File not found."

        prompt = CONTEXT_AGENT_SUMMARY_PROMPT.format(
            filename=context_file.filename,
            content=context_file.content,
        )

        try:
            summary = await generate_content(
                prompt,
                system_instruction=CONTEXT_AGENT_SYSTEM_PROMPT,
            )

            logger.info(
                "context_file_summarized",
                idea_id=str(idea_id),
                context_file_id=str(context_file_id),
                filename=context_file.filename,
            )

            return summary

        except Exception as e:
            logger.error(
                "context_summarize_error",
                error=str(e),
                idea_id=str(idea_id),
                context_file_id=str(context_file_id),
            )
            return "Error generating summary."

    def map_to_kernel(self, insight: Insight) -> list[str]:
        """
        Map an insight to kernel file types.

        Args:
            insight: The insight to map

        Returns:
            List of kernel file types this insight relates to
        """
        relevance = insight.relevance.lower()
        kernel_types = []

        if "summary" in relevance:
            kernel_types.append("summary")
        if "challenge" in relevance:
            kernel_types.append("challenge")
        if "approach" in relevance:
            kernel_types.append("approach")
        if "steps" in relevance or "coherent" in relevance:
            kernel_types.append("coherent_steps")

        # If nothing specific mentioned, default to challenge (most common)
        if not kernel_types:
            kernel_types.append("challenge")

        return kernel_types

    async def coach(
        self,
        idea_id: UUID,
        context_file_id: UUID,
        user_message: str,
        session_id: UUID,
    ) -> str:
        """
        Provide coaching guidance about a context file.

        Uses conversation history from the session for context.

        Args:
            idea_id: The idea UUID
            context_file_id: The context file UUID
            user_message: The user's message
            session_id: The session UUID

        Returns:
            Agent response text
        """
        # Get the context file
        context_file = context_file_concept.get_by_id(context_file_id)
        if not context_file:
            return "I couldn't find that context file. It may have been deleted."

        # Get session history
        history = session_concept.get_history(session_id)

        # Build messages for the LLM
        messages = []

        # Add context about the current file content
        context_message = f"""Here is the content of the context file "{context_file.filename}":

```markdown
{context_file.content}
```

This is a context file for an idea. Help the user understand how they can use the information in this file to strengthen their idea's kernel files (Summary, Challenge, Approach, CoherentSteps)."""

        messages.append({"role": "user", "content": context_message})
        messages.append({
            "role": "agent",
            "content": f"I've reviewed '{context_file.filename}'. What would you like to know about it or how would you like to use this information?"
        })

        # Add conversation history
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the new user message
        messages.append({"role": "user", "content": user_message})

        try:
            response = await chat_with_history(
                messages,
                system_instruction=CONTEXT_AGENT_SYSTEM_PROMPT,
            )

            logger.info(
                "context_coach_response",
                idea_id=str(idea_id),
                context_file_id=str(context_file_id),
                session_id=str(session_id),
                message_length=len(response),
            )

            return response

        except Exception as e:
            logger.error(
                "context_coach_error",
                error=str(e),
                idea_id=str(idea_id),
                context_file_id=str(context_file_id),
            )
            return "I'm having trouble responding right now. Please try again."

    def format_insights_for_coherence_chat(
        self,
        filename: str,
        extraction_result: ExtractionResult,
    ) -> str:
        """
        Format extracted insights as a message for the CoherenceAgent chat.

        Args:
            filename: The context file name
            extraction_result: The extraction result

        Returns:
            Formatted message string
        """
        if not extraction_result.insights:
            return f"I analyzed the new context file '{filename}' but didn't find specific insights that connect to your kernel files. Feel free to ask me about it!"

        lines = [
            f"I found some insights in your new context file '{filename}' that could help strengthen your idea:",
            "",
        ]

        for i, insight in enumerate(extraction_result.insights, 1):
            lines.append(f"**{i}. {insight.relevance}**")
            if insight.quote:
                lines.append(f"> {insight.quote[:200]}{'...' if len(insight.quote) > 200 else ''}")
            lines.append(f"*Suggestion:* {insight.suggestion}")
            lines.append("")

        lines.append("Would you like me to help you incorporate any of these insights?")

        return "\n".join(lines)


# Singleton instance
context_agent = ContextAgent()
