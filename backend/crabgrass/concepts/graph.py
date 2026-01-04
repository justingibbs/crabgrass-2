"""Graph concept - DuckPGQ wrapper for idea-objective relationships."""

from dataclasses import dataclass
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, Literal
import structlog

from ..db.connection import get_db

logger = structlog.get_logger()


@dataclass
class Edge:
    """Represents a graph edge."""

    from_id: UUID
    to_id: UUID
    relationship: str
    created_at: datetime


class GraphConcept:
    """
    Actions for the Graph concept.

    Uses DuckPGQ for graph queries when available, falls back to SQL otherwise.
    """

    def connect(
        self,
        from_id: UUID,
        to_id: UUID,
        relationship: Literal["supports"],
    ) -> Edge:
        """
        Create an edge between two nodes.

        Currently supports:
        - supports: Idea -> Objective
        """
        now = datetime.now(timezone.utc)

        with get_db() as db:
            if relationship == "supports":
                # Insert into idea_objective_links
                db.execute(
                    """
                    INSERT INTO idea_objective_links (idea_id, objective_id, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT (idea_id, objective_id) DO NOTHING
                    """,
                    [str(from_id), str(to_id), now.isoformat()],
                )

                # Also update the ideas.objective_id for backward compatibility
                db.execute(
                    """
                    UPDATE ideas SET objective_id = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    [str(to_id), now.isoformat(), str(from_id)],
                )

                logger.info(
                    "graph_edge_created",
                    relationship=relationship,
                    from_id=str(from_id),
                    to_id=str(to_id),
                )
            else:
                raise ValueError(f"Unknown relationship type: {relationship}")

        return Edge(
            from_id=from_id,
            to_id=to_id,
            relationship=relationship,
            created_at=now,
        )

    def disconnect(
        self,
        from_id: UUID,
        to_id: UUID,
        relationship: Literal["supports"],
    ) -> bool:
        """
        Remove an edge between two nodes.

        Returns True if an edge was removed, False otherwise.
        """
        now = datetime.now(timezone.utc)

        with get_db() as db:
            if relationship == "supports":
                # Remove from idea_objective_links
                result = db.execute(
                    """
                    DELETE FROM idea_objective_links
                    WHERE idea_id = ? AND objective_id = ?
                    RETURNING idea_id
                    """,
                    [str(from_id), str(to_id)],
                ).fetchone()

                # Also clear the ideas.objective_id for backward compatibility
                db.execute(
                    """
                    UPDATE ideas SET objective_id = NULL, updated_at = ?
                    WHERE id = ? AND objective_id = ?
                    """,
                    [now.isoformat(), str(from_id), str(to_id)],
                )

                if result:
                    logger.info(
                        "graph_edge_removed",
                        relationship=relationship,
                        from_id=str(from_id),
                        to_id=str(to_id),
                    )
                    return True
                return False
            else:
                raise ValueError(f"Unknown relationship type: {relationship}")

    def get_connected(
        self,
        node_id: UUID,
        relationship: Literal["supports"],
        direction: Literal["outgoing", "incoming"] = "outgoing",
    ) -> list[UUID]:
        """
        Get nodes connected to the given node by a relationship.

        Args:
            node_id: The node to query from
            relationship: The type of relationship
            direction: 'outgoing' = from this node, 'incoming' = to this node
        """
        with get_db() as db:
            if relationship == "supports":
                if direction == "outgoing":
                    # Ideas that support this objective (node_id is objective)
                    # Wait, this is backwards for supports...
                    # Actually: Idea --supports--> Objective
                    # So outgoing from idea = objectives it supports
                    # outgoing from objective makes no sense for supports
                    #
                    # Let's clarify:
                    # If node_id is an idea, outgoing = objectives it supports
                    # If node_id is an objective, incoming = ideas that support it
                    result = db.execute(
                        """
                        SELECT objective_id FROM idea_objective_links
                        WHERE idea_id = ?
                        """,
                        [str(node_id)],
                    ).fetchall()
                else:  # incoming
                    result = db.execute(
                        """
                        SELECT idea_id FROM idea_objective_links
                        WHERE objective_id = ?
                        """,
                        [str(node_id)],
                    ).fetchall()

                return [
                    UUID(row[0]) if isinstance(row[0], str) else row[0]
                    for row in result
                ]
            else:
                raise ValueError(f"Unknown relationship type: {relationship}")

    def get_ideas_for_objective(self, objective_id: UUID) -> list[UUID]:
        """
        Convenience method: Get all idea IDs that support an objective.

        This is equivalent to get_connected(objective_id, "supports", "incoming").
        """
        return self.get_connected(objective_id, "supports", "incoming")

    def get_objective_for_idea(self, idea_id: UUID) -> Optional[UUID]:
        """
        Convenience method: Get the objective an idea supports (if any).

        Returns None if the idea has no objective linked.
        """
        result = self.get_connected(idea_id, "supports", "outgoing")
        return result[0] if result else None

    def link_idea_to_objective(self, idea_id: UUID, objective_id: UUID) -> Edge:
        """
        Convenience method: Link an idea to an objective.

        Alias for connect(idea_id, objective_id, "supports").
        """
        return self.connect(idea_id, objective_id, "supports")

    def unlink_idea_from_objective(self, idea_id: UUID, objective_id: UUID) -> bool:
        """
        Convenience method: Unlink an idea from an objective.

        Alias for disconnect(idea_id, objective_id, "supports").
        """
        return self.disconnect(idea_id, objective_id, "supports")

    def unlink_idea(self, idea_id: UUID) -> bool:
        """
        Remove any objective link from an idea.

        Finds the current objective (if any) and unlinks it.
        """
        current_objective = self.get_objective_for_idea(idea_id)
        if current_objective:
            return self.unlink_idea_from_objective(idea_id, current_objective)
        return False
