"""Agent concepts - AI coaches for different aspects of idea development."""

from .challenge_agent import ChallengeAgent, challenge_agent
from .summary_agent import SummaryAgent, summary_agent
from .approach_agent import ApproachAgent, approach_agent
from .steps_agent import StepsAgent, steps_agent
from .coherence_agent import CoherenceAgent, coherence_agent

# Map file types to their agents
FILE_TYPE_TO_AGENT = {
    "summary": summary_agent,
    "challenge": challenge_agent,
    "approach": approach_agent,
    "coherent_steps": steps_agent,
}

# Map agent types to their agents
AGENT_TYPE_TO_AGENT = {
    "summary": summary_agent,
    "challenge": challenge_agent,
    "approach": approach_agent,
    "steps": steps_agent,
    "coherence": coherence_agent,
    # Slice 8 will add:
    # "context": context_agent,
    # Slice 9 will add:
    # "objective": objective_agent,
}


def get_agent_for_file_type(file_type: str):
    """Get the agent for a specific kernel file type."""
    agent = FILE_TYPE_TO_AGENT.get(file_type)
    if agent is None:
        raise ValueError(f"No agent found for file type: {file_type}")
    return agent


def get_agent_by_type(agent_type: str):
    """Get an agent by its type name."""
    agent = AGENT_TYPE_TO_AGENT.get(agent_type)
    if agent is None:
        raise ValueError(f"No agent found for type: {agent_type}")
    return agent


__all__ = [
    "ChallengeAgent",
    "challenge_agent",
    "SummaryAgent",
    "summary_agent",
    "ApproachAgent",
    "approach_agent",
    "StepsAgent",
    "steps_agent",
    "CoherenceAgent",
    "coherence_agent",
    "get_agent_for_file_type",
    "get_agent_by_type",
]
