"""
Synchronizations - coordination logic between concepts.

Synchronizations are declarative rules that define how concepts interact
without coupling them. They are the ONLY place concepts interact.

Each function is named `on_<event>` to match the trigger.
"""

import structlog

from ..concepts.idea import Idea, IdeaConcept
from ..concepts.kernel_file import KernelFileConcept

logger = structlog.get_logger()

# Concept instances
idea_concept = IdeaConcept()
kernel_file_concept = KernelFileConcept()


def on_idea_created(idea: Idea) -> None:
    """
    sync IdeaCreated:
        when Idea.create():
            → KernelFile.initializeAll(idea_id)
            → Version.initialize(idea_id)  # Slice 4
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

    # TODO Slice 4: Version.initialize(idea.id)
    # TODO Slice 9: if idea.objective_id: Graph.connect(idea.id, idea.objective_id, "SUPPORTS")
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

    # TODO Slice 9: Graph.connect(idea_id, objective_id, "SUPPORTS")


def on_kernel_file_updated(idea_id, file_type, content) -> None:
    """
    sync KernelFileUpdated:
        when KernelFile.update():
            → Version.commit()
            → Embedding.generate()
            → Agent.evaluate()
    """
    logger.info(
        "sync_kernel_file_updated",
        idea_id=str(idea_id),
        file_type=file_type,
    )

    # Update idea's updated_at timestamp
    idea_concept.update(idea_id)

    # TODO Slice 4: Version.commit(idea_id, file_type, content)
    # TODO Slice 10: embedding = Embedding.generate(content)
    # TODO Slice 10: kernel_file_concept.set_embedding(idea_id, file_type, embedding)
    # TODO Slice 5: agent = get_agent_for_file_type(file_type)
    # TODO Slice 5: agent.evaluate(idea_id, content)


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

    # TODO Slice 7: if count >= 2: CoherenceAgent.evaluate(idea_id)
