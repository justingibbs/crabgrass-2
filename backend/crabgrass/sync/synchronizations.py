"""
Synchronizations - coordination logic between concepts.

Synchronizations are declarative rules that define how concepts interact
without coupling them. They are the ONLY place concepts interact.

Each function is named `on_<event>` to match the trigger.
"""

import asyncio
import structlog

from ..concepts.idea import Idea, IdeaConcept
from ..concepts.kernel_file import KernelFileConcept
from ..concepts.version import version_concept
from ..concepts.session import session_concept
from ..concepts.objective import Objective
from ..concepts.objective_file import ObjectiveFileConcept
from ..concepts.graph import GraphConcept
from ..concepts.embedding import embedding_concept

logger = structlog.get_logger()

# Concept instances
idea_concept = IdeaConcept()
kernel_file_concept = KernelFileConcept()
objective_file_concept = ObjectiveFileConcept()
graph_concept = GraphConcept()


def on_idea_created(idea: Idea) -> None:
    """
    sync IdeaCreated:
        when Idea.create():
            → KernelFile.initializeAll(idea_id)
            → Version.initialize(idea_id)
            → if objective_id: Graph.connect(idea_id, objective_id, "SUPPORTS")  # Slice 9
            → Session.create(idea_id, user_id, "coherence")  # Slice 5
    """
    logger.info(
        "sync_idea_created",
        idea_id=str(idea.id),
        title=idea.title,
    )

    # Initialize kernel files with templates
    kernel_files = kernel_file_concept.initialize_all(idea.id, idea.creator_id)
    logger.info(
        "kernel_files_initialized",
        idea_id=str(idea.id),
        count=len(kernel_files),
    )

    # Initialize JJ repository for version control
    version_concept.initialize(idea.id)

    # Write initial kernel files to JJ repo
    kernel_content = {kf.file_type: kf.content for kf in kernel_files}
    version_concept.write_initial_files(idea.id, kernel_content)

    # If idea has an objective, create graph edge
    if idea.objective_id:
        graph_concept.link_idea_to_objective(idea.id, idea.objective_id)

    # TODO Slice 5: Session.create(idea.id, idea.creator_id, "coherence")


def on_idea_linked_to_objective(idea_id, objective_id) -> None:
    """
    sync IdeaLinkedToObjective:
        when Idea.update(idea_id, objective_id):
            → Graph.connect(idea_id, objective_id, "SUPPORTS")
    """
    logger.info(
        "sync_idea_linked_to_objective",
        idea_id=str(idea_id),
        objective_id=str(objective_id),
    )

    # Create graph edge
    graph_concept.link_idea_to_objective(idea_id, objective_id)


def on_idea_unlinked_from_objective(idea_id, objective_id) -> None:
    """
    sync IdeaUnlinkedFromObjective:
        when Idea.objective cleared:
            → Graph.disconnect(idea_id, objective_id, "SUPPORTS")
    """
    logger.info(
        "sync_idea_unlinked_from_objective",
        idea_id=str(idea_id),
        objective_id=str(objective_id),
    )

    # Remove graph edge
    graph_concept.unlink_idea_from_objective(idea_id, objective_id)


def on_objective_created(objective: Objective, user_id) -> None:
    """
    sync ObjectiveCreated:
        when Objective.create():
            → ObjectiveFile.initialize(objective_id)
    """
    logger.info(
        "sync_objective_created",
        objective_id=str(objective.id),
        title=objective.title,
    )

    # Initialize objective file with template
    objective_file_concept.initialize(objective.id, user_id)


def on_kernel_file_updated(idea_id, file_type, content) -> None:
    """
    sync KernelFileUpdated:
        when KernelFile.update():
            → Version.commit()
            → Embedding.generate() and store
            → Agent.evaluate() (async, called separately)
    """
    logger.info(
        "sync_kernel_file_updated",
        idea_id=str(idea_id),
        file_type=file_type,
    )

    # Update idea's updated_at timestamp
    idea_concept.update(idea_id)

    # Commit to JJ repository
    version_concept.commit(idea_id, file_type, content)

    # Generate and store embedding
    # Get the kernel file to get its ID
    kernel_file = kernel_file_concept.get(idea_id, file_type)
    if kernel_file:
        # Check if content has changed (avoid re-embedding same content)
        if embedding_concept.needs_update(kernel_file.id, content):
            embedding = embedding_concept.generate(content)
            content_hash = embedding_concept.content_hash(content)
            embedding_concept.store(
                kernel_file_id=kernel_file.id,
                idea_id=idea_id,
                file_type=file_type,
                embedding=embedding,
                content_hash=content_hash,
            )
            logger.info(
                "embedding_updated",
                idea_id=str(idea_id),
                file_type=file_type,
            )

    # Note: Agent evaluation is async and called separately via on_kernel_file_updated_async


async def on_kernel_file_updated_async(idea_id, file_type, content) -> None:
    """
    Async portion of KernelFileUpdated sync.
    Triggers agent evaluation which may mark the file complete.
    """
    from ..concepts.agents import get_agent_for_file_type

    try:
        agent = get_agent_for_file_type(file_type)
        evaluation = await agent.evaluate(idea_id, content)

        logger.info(
            "agent_evaluation_complete",
            idea_id=str(idea_id),
            file_type=file_type,
            is_complete=evaluation.is_complete,
        )

        # If newly complete, trigger the completion sync
        if evaluation.is_complete:
            await on_kernel_file_marked_complete_async(idea_id, file_type)

    except ValueError:
        # No agent for this file type (should not happen for kernel files)
        logger.warning(
            "no_agent_for_file_type",
            idea_id=str(idea_id),
            file_type=file_type,
        )


def on_kernel_file_marked_complete(idea_id, file_type) -> None:
    """
    sync KernelFileMarkedComplete:
        when KernelFile.markComplete():
            → Idea.updateKernelCompletion()
            → if count >= 2: CoherenceAgent.evaluate()
    """
    logger.info(
        "sync_kernel_file_marked_complete",
        idea_id=str(idea_id),
        file_type=file_type,
    )

    # Update the idea's kernel completion count
    count = idea_concept.update_kernel_completion(idea_id)
    logger.info(
        "kernel_completion_updated",
        idea_id=str(idea_id),
        count=count,
    )

    # Note: CoherenceAgent.evaluate() is triggered in the async version


async def on_kernel_file_marked_complete_async(idea_id, file_type) -> None:
    """
    Async portion of KernelFileMarkedComplete sync.
    Emits SSE event for completion change.
    Triggers CoherenceAgent evaluation when 2+ files are complete.
    """
    from ..api.sse import emit_completion_changed
    from ..concepts.agents.coherence_agent import coherence_agent

    # Run the sync version first
    on_kernel_file_marked_complete(idea_id, file_type)

    # Get the updated completion count
    idea = idea_concept.get(idea_id)
    if idea:
        # Emit SSE event
        await emit_completion_changed(
            idea_id=idea_id,
            file_type=file_type,
            is_complete=True,
            total_complete=idea.kernel_completion,
        )

        # Slice 7: Trigger CoherenceAgent evaluation when 2+ files complete
        if idea.kernel_completion >= 2:
            logger.info(
                "triggering_coherence_evaluation",
                idea_id=str(idea_id),
                kernel_completion=idea.kernel_completion,
            )
            try:
                # Run evaluation in background (fire-and-forget style)
                await coherence_agent.evaluate(idea_id)
            except Exception as e:
                logger.error(
                    "coherence_evaluation_failed",
                    idea_id=str(idea_id),
                    error=str(e),
                )


async def on_context_file_created_async(idea_id, context_file_id, user_id) -> None:
    """
    sync ContextFileAdded:
        when ContextFile.create(idea_id, content, filename):
            → insights = ContextAgent.extract(idea_id, context_file_id)
            → for insight in insights:
                → Session.addMessage(idea_id, "agent", insight.suggestion)

    Extracts insights from new context files and adds them to the
    CoherenceAgent chat session so users see the insights at workspace level.
    """
    from ..concepts.agents.context_agent import context_agent
    from ..concepts.context_file import context_file_concept

    logger.info(
        "sync_context_file_created",
        idea_id=str(idea_id),
        context_file_id=str(context_file_id),
        user_id=str(user_id),
    )

    try:
        # Get the context file
        context_file = context_file_concept.get_by_id(context_file_id)
        if not context_file:
            logger.warning(
                "context_file_not_found_for_extraction",
                context_file_id=str(context_file_id),
            )
            return

        # Skip extraction for very small files (likely just created with placeholder)
        if len(context_file.content.strip()) < 50:
            logger.info(
                "skipping_extraction_for_small_file",
                idea_id=str(idea_id),
                context_file_id=str(context_file_id),
                content_length=len(context_file.content),
            )
            return

        # Extract insights
        extraction_result = await context_agent.extract(idea_id, context_file_id)

        if extraction_result.insights:
            # Format insights as a message for the CoherenceAgent chat
            message = context_agent.format_insights_for_coherence_chat(
                context_file.filename,
                extraction_result,
            )

            # Get or create coherence session for this user
            coherence_session = session_concept.get_or_create(
                idea_id=idea_id,
                user_id=user_id,
                agent_type="coherence",
                file_type=None,
            )

            # Add the insights as an agent message
            session_concept.add_message(coherence_session.id, "agent", message)

            logger.info(
                "context_insights_added_to_coherence_chat",
                idea_id=str(idea_id),
                context_file_id=str(context_file_id),
                insight_count=len(extraction_result.insights),
                session_id=str(coherence_session.id),
            )

    except Exception as e:
        logger.error(
            "context_file_extraction_failed",
            idea_id=str(idea_id),
            context_file_id=str(context_file_id),
            error=str(e),
        )
