"""Database schema migrations and seeding."""

import uuid
from datetime import datetime, timezone
import structlog

from .connection import get_connection

logger = structlog.get_logger()

# Pre-defined UUIDs for dev users (stable across resets)
ACME_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SALLY_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
SAM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")

# Kernel file types
KERNEL_FILE_TYPES = ["summary", "challenge", "approach", "coherent_steps"]

# Kernel file templates
KERNEL_FILE_TEMPLATES = {
    "summary": """# Summary

_Describe your idea in 2-3 sentences. What is it? What does it do?_
""",
    "challenge": """# Challenge

_What problem are you solving? Who experiences this problem? Why does it matter?_
""",
    "approach": """# Approach

_How will you solve this challenge? What makes your approach unique or effective?_
""",
    "coherent_steps": """# Coherent Steps

_What are the concrete next actions? List 3-5 specific steps to move forward._

1.
2.
3.
""",
}


def run_migrations() -> None:
    """Run all database migrations."""
    conn = get_connection()

    # Check if migrations have already run
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()
    table_names = {t[0] for t in tables}

    if "organizations" in table_names:
        logger.info("migrations_already_run", tables=list(table_names))
        return

    logger.info("running_migrations")

    # Create schema
    _create_schema(conn)

    # Seed dev data
    _seed_dev_data(conn)

    logger.info("migrations_complete")


def _create_schema(conn) -> None:
    """Create the database schema."""

    # Organizations
    conn.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id UUID PRIMARY KEY,
            name VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            settings JSON
        )
    """)

    # Users
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            org_id UUID REFERENCES organizations(id),
            email VARCHAR UNIQUE NOT NULL,
            name VARCHAR NOT NULL,
            role VARCHAR DEFAULT 'member',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            preferences JSON
        )
    """)

    # Objectives (stub for now - will be expanded in later slices)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS objectives (
            id UUID PRIMARY KEY,
            org_id UUID REFERENCES organizations(id),
            title VARCHAR NOT NULL,
            description TEXT,
            owner_id UUID REFERENCES users(id),
            timeframe VARCHAR,
            status VARCHAR DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by UUID REFERENCES users(id)
        )
    """)

    # Ideas
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ideas (
            id UUID PRIMARY KEY,
            org_id UUID REFERENCES organizations(id),
            creator_id UUID REFERENCES users(id),
            objective_id UUID REFERENCES objectives(id),
            title VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'draft',
            kernel_completion INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Kernel Files
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kernel_files (
            id UUID PRIMARY KEY,
            idea_id UUID REFERENCES ideas(id),
            file_type VARCHAR NOT NULL,
            content TEXT,
            content_hash VARCHAR,
            is_complete BOOLEAN DEFAULT FALSE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by UUID REFERENCES users(id),
            UNIQUE(idea_id, file_type)
        )
    """)

    # Idea collaborators
    conn.execute("""
        CREATE TABLE IF NOT EXISTS idea_collaborators (
            idea_id UUID REFERENCES ideas(id),
            user_id UUID REFERENCES users(id),
            role VARCHAR DEFAULT 'contributor',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (idea_id, user_id)
        )
    """)

    logger.info("schema_created")


def _seed_dev_data(conn) -> None:
    """Seed development data."""
    now = datetime.now(timezone.utc).isoformat()

    # Create Acme Corp organization
    conn.execute(
        """
        INSERT INTO organizations (id, name, created_at, settings)
        VALUES (?, ?, ?, ?)
        """,
        [
            str(ACME_ORG_ID),
            "Acme Corp",
            now,
            "{}",
        ],
    )

    # Create Sally Chen (Frontline Worker, member)
    conn.execute(
        """
        INSERT INTO users (id, org_id, email, name, role, created_at, preferences)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            str(SALLY_USER_ID),
            str(ACME_ORG_ID),
            "sally.chen@acme.example",
            "Sally Chen",
            "member",
            now,
            '{"title": "Frontline Worker"}',
        ],
    )

    # Create Sam White (VP, org_admin)
    conn.execute(
        """
        INSERT INTO users (id, org_id, email, name, role, created_at, preferences)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            str(SAM_USER_ID),
            str(ACME_ORG_ID),
            "sam.white@acme.example",
            "Sam White",
            "org_admin",
            now,
            '{"title": "VP"}',
        ],
    )

    logger.info("dev_data_seeded", org="Acme Corp", users=["Sally Chen", "Sam White"])


def get_dev_users() -> list[dict]:
    """Get the pre-seeded dev users."""
    return [
        {
            "id": str(SALLY_USER_ID),
            "name": "Sally Chen",
            "email": "sally.chen@acme.example",
            "role": "member",
            "title": "Frontline Worker",
        },
        {
            "id": str(SAM_USER_ID),
            "name": "Sam White",
            "email": "sam.white@acme.example",
            "role": "org_admin",
            "title": "VP",
        },
    ]
