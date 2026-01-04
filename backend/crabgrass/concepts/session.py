"""Session concept - persistent conversation threads with agents."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import structlog

from ..db.connection import get_db

logger = structlog.get_logger()


@dataclass
class SessionMessage:
    """A single message in a session."""

    id: UUID
    session_id: UUID
    role: str  # 'user' or 'agent'
    content: str
    created_at: datetime


@dataclass
class Session:
    """A conversation session with an agent."""

    id: UUID
    idea_id: Optional[UUID]  # For idea-related sessions
    objective_id: Optional[UUID]  # For objective-related sessions
    user_id: UUID
    agent_type: str  # 'challenge', 'summary', 'approach', 'steps', 'coherence', 'context', 'objective'
    file_type: Optional[str]  # For kernel file agents: 'summary', 'challenge', 'approach', 'coherent_steps'
    title: Optional[str]
    created_at: datetime
    last_active: datetime


class SessionConcept:
    """Actions for the Session concept."""

    def create(
        self,
        idea_id: UUID,
        user_id: UUID,
        agent_type: str,
        file_type: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Session:
        """Create a new session for an idea."""
        session_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        with get_db() as db:
            db.execute(
                """
                INSERT INTO sessions (id, idea_id, objective_id, user_id, agent_type, file_type, title, created_at, last_active)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?)
                """,
                [
                    str(session_id),
                    str(idea_id),
                    str(user_id),
                    agent_type,
                    file_type,
                    title,
                    now.isoformat(),
                    now.isoformat(),
                ],
            )

        logger.info(
            "session_created",
            session_id=str(session_id),
            idea_id=str(idea_id),
            agent_type=agent_type,
        )

        return Session(
            id=session_id,
            idea_id=idea_id,
            objective_id=None,
            user_id=user_id,
            agent_type=agent_type,
            file_type=file_type,
            title=title,
            created_at=now,
            last_active=now,
        )

    def create_for_objective(
        self,
        objective_id: UUID,
        user_id: UUID,
        agent_type: str,
        title: Optional[str] = None,
    ) -> Session:
        """Create a new session for an objective."""
        session_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        with get_db() as db:
            db.execute(
                """
                INSERT INTO sessions (id, idea_id, objective_id, user_id, agent_type, file_type, title, created_at, last_active)
                VALUES (?, NULL, ?, ?, ?, NULL, ?, ?, ?)
                """,
                [
                    str(session_id),
                    str(objective_id),
                    str(user_id),
                    agent_type,
                    title,
                    now.isoformat(),
                    now.isoformat(),
                ],
            )

        logger.info(
            "session_created_for_objective",
            session_id=str(session_id),
            objective_id=str(objective_id),
            agent_type=agent_type,
        )

        return Session(
            id=session_id,
            idea_id=None,
            objective_id=objective_id,
            user_id=user_id,
            agent_type=agent_type,
            file_type=None,
            title=title,
            created_at=now,
            last_active=now,
        )

    def list_for_objective(
        self,
        objective_id: UUID,
        agent_type: Optional[str] = None,
    ) -> list[Session]:
        """List sessions for an objective, optionally filtered by agent type."""
        with get_db() as db:
            query = "SELECT * FROM sessions WHERE objective_id = ?"
            params = [str(objective_id)]

            if agent_type:
                query += " AND agent_type = ?"
                params.append(agent_type)

            query += " ORDER BY last_active DESC"

            results = db.execute(query, params).fetchall()

            return [self._row_to_session(row) for row in results]

    def get(self, session_id: UUID) -> Optional[Session]:
        """Get a session by ID."""
        with get_db() as db:
            result = db.execute(
                "SELECT * FROM sessions WHERE id = ?",
                [str(session_id)],
            ).fetchone()

            if not result:
                return None

            return self._row_to_session(result)

    def list_for_idea(
        self,
        idea_id: UUID,
        agent_type: Optional[str] = None,
        file_type: Optional[str] = None,
    ) -> list[Session]:
        """List sessions for an idea, optionally filtered by agent/file type."""
        with get_db() as db:
            query = "SELECT * FROM sessions WHERE idea_id = ?"
            params = [str(idea_id)]

            if agent_type:
                query += " AND agent_type = ?"
                params.append(agent_type)

            if file_type:
                query += " AND file_type = ?"
                params.append(file_type)

            query += " ORDER BY last_active DESC"

            results = db.execute(query, params).fetchall()

            return [self._row_to_session(row) for row in results]

    def get_or_create(
        self,
        idea_id: UUID,
        user_id: UUID,
        agent_type: str,
        file_type: Optional[str] = None,
    ) -> Session:
        """Get the most recent session or create a new one."""
        sessions = self.list_for_idea(idea_id, agent_type, file_type)

        if sessions:
            return sessions[0]

        return self.create(idea_id, user_id, agent_type, file_type)

    def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
    ) -> SessionMessage:
        """Add a message to a session."""
        message_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        with get_db() as db:
            # Insert the message
            db.execute(
                """
                INSERT INTO session_messages (id, session_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    str(message_id),
                    str(session_id),
                    role,
                    content,
                    now.isoformat(),
                ],
            )

            # Update session's last_active
            db.execute(
                "UPDATE sessions SET last_active = ? WHERE id = ?",
                [now.isoformat(), str(session_id)],
            )

        return SessionMessage(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            created_at=now,
        )

    def get_history(
        self,
        session_id: UUID,
        limit: int = 50,
    ) -> list[SessionMessage]:
        """Get message history for a session."""
        with get_db() as db:
            results = db.execute(
                """
                SELECT * FROM session_messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                [str(session_id), limit],
            ).fetchall()

            return [self._row_to_message(row) for row in results]

    def update_title(self, session_id: UUID, title: str) -> None:
        """Update a session's title."""
        with get_db() as db:
            db.execute(
                "UPDATE sessions SET title = ? WHERE id = ?",
                [title, str(session_id)],
            )

    def _row_to_session(self, row) -> Session:
        """Convert a database row to a Session object."""
        # Row order: id, idea_id, objective_id, user_id, agent_type, file_type, title, created_at, last_active
        return Session(
            id=UUID(str(row[0])),
            idea_id=UUID(str(row[1])) if row[1] else None,
            objective_id=UUID(str(row[2])) if row[2] else None,
            user_id=UUID(str(row[3])),
            agent_type=row[4],
            file_type=row[5],
            title=row[6],
            created_at=self._parse_timestamp(row[7]),
            last_active=self._parse_timestamp(row[8]),
        )

    def _row_to_message(self, row) -> SessionMessage:
        """Convert a database row to a SessionMessage object."""
        return SessionMessage(
            id=UUID(str(row[0])),
            session_id=UUID(str(row[1])),
            role=row[2],
            content=row[3],
            created_at=self._parse_timestamp(row[4]),
        )

    def _parse_timestamp(self, value) -> datetime:
        """Parse a timestamp from the database."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Handle both formats
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return datetime.fromisoformat(value)
        return value


# Singleton instance
session_concept = SessionConcept()
