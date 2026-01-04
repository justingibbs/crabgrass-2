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

# Objective file template
OBJECTIVE_FILE_TEMPLATE = """# Objective

_Define what success looks like for this objective._

## Why This Matters

_What's the strategic importance? What happens if we don't achieve this?_

## Success Criteria

_How will we know when this objective is achieved? Be specific and measurable._

-
-
-
"""


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
        # Run incremental migrations for new tables
        _run_incremental_migrations(conn, table_names)
        return

    logger.info("running_migrations")

    # Create schema
    _create_schema(conn)

    # Seed dev data
    _seed_dev_data(conn)

    logger.info("migrations_complete")


def _run_incremental_migrations(conn, existing_tables: set) -> None:
    """Run incremental migrations for tables added after initial setup."""

    # Slice 7: Add context_files table
    if "context_files" not in existing_tables:
        logger.info("adding_context_files_table")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS context_files (
                id UUID PRIMARY KEY,
                idea_id UUID REFERENCES ideas(id),
                filename VARCHAR NOT NULL,
                content TEXT,
                size_bytes INTEGER DEFAULT 0,
                created_by UUID REFERENCES users(id),
                created_by_agent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(idea_id, filename)
            )
        """)

    # Slice 9: Add objective_files table
    if "objective_files" not in existing_tables:
        logger.info("adding_objective_files_table")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS objective_files (
                id UUID PRIMARY KEY,
                objective_id UUID REFERENCES objectives(id) NOT NULL,
                content TEXT,
                content_hash VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by UUID REFERENCES users(id),
                UNIQUE(objective_id)
            )
        """)

    # Slice 9: Add objective_id to context_files for objective context files
    # Check if column exists
    try:
        conn.execute("SELECT objective_id FROM context_files LIMIT 1")
    except Exception:
        logger.info("adding_objective_id_to_context_files")
        # Note: DuckDB doesn't support ALTER TABLE with REFERENCES constraints
        conn.execute("ALTER TABLE context_files ADD COLUMN objective_id UUID")

    # Slice 9: Add objective_id to sessions for objective agent sessions
    try:
        conn.execute("SELECT objective_id FROM sessions LIMIT 1")
    except Exception:
        logger.info("adding_objective_id_to_sessions")
        # Note: DuckDB doesn't support ALTER TABLE with REFERENCES constraints
        conn.execute("ALTER TABLE sessions ADD COLUMN objective_id UUID")

    # Slice 9: Add idea_objective_links table for graph edges
    if "idea_objective_links" not in existing_tables:
        logger.info("adding_idea_objective_links_table")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS idea_objective_links (
                idea_id UUID REFERENCES ideas(id) NOT NULL,
                objective_id UUID REFERENCES objectives(id) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (idea_id, objective_id)
            )
        """)

    # Slice 9: Create DuckPGQ property graph
    _create_property_graph(conn)

    # Slice 10: Add kernel_embeddings table for vector storage
    if "kernel_embeddings" not in existing_tables:
        logger.info("adding_kernel_embeddings_table")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kernel_embeddings (
                id UUID PRIMARY KEY,
                kernel_file_id UUID REFERENCES kernel_files(id),
                idea_id UUID REFERENCES ideas(id),
                file_type VARCHAR NOT NULL,
                embedding FLOAT[768],
                content_hash VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Create VSS index for similarity search
        try:
            conn.execute("""
                CREATE INDEX IF NOT EXISTS kernel_embedding_idx
                ON kernel_embeddings USING HNSW (embedding)
                WITH (metric = 'cosine')
            """)
            logger.info("vss_index_created", index="kernel_embedding_idx")
        except Exception as e:
            logger.warning(
                "vss_index_creation_failed",
                error=str(e),
                note="VSS extension may not be available - vector search will use fallback",
            )


def _create_property_graph(conn) -> None:
    """Create the DuckPGQ property graph for idea-objective relationships."""
    try:
        # Check if graph already exists
        result = conn.execute(
            "SELECT * FROM duckpgq_tables() WHERE table_name = 'idea_graph'"
        ).fetchone()
        if result:
            logger.info("property_graph_exists", graph="idea_graph")
            return
    except Exception:
        # duckpgq_tables() may not exist if extension isn't loaded
        pass

    try:
        # Drop existing graph if any (for clean recreation)
        try:
            conn.execute("DROP PROPERTY GRAPH IF EXISTS idea_graph")
        except Exception:
            pass

        # Create the property graph
        conn.execute("""
            CREATE PROPERTY GRAPH idea_graph
            VERTEX TABLES (
                ideas,
                objectives,
                users,
                organizations
            )
            EDGE TABLES (
                idea_objective_links
                    SOURCE KEY (idea_id) REFERENCES ideas (id)
                    DESTINATION KEY (objective_id) REFERENCES objectives (id)
                    LABEL supports,
                idea_collaborators
                    SOURCE KEY (idea_id) REFERENCES ideas (id)
                    DESTINATION KEY (user_id) REFERENCES users (id)
                    LABEL collaborates_on
            )
        """)
        logger.info("property_graph_created", graph="idea_graph")
    except Exception as e:
        logger.warning(
            "property_graph_creation_failed",
            error=str(e),
            note="DuckPGQ may not be available - graph features will use fallback SQL",
        )


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

    # Sessions (conversation threads with agents)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id UUID PRIMARY KEY,
            idea_id UUID REFERENCES ideas(id),
            objective_id UUID REFERENCES objectives(id),
            user_id UUID REFERENCES users(id),
            agent_type VARCHAR NOT NULL,
            file_type VARCHAR,
            title VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Session messages
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_messages (
            id UUID PRIMARY KEY,
            session_id UUID REFERENCES sessions(id),
            role VARCHAR NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Context files (supporting materials for ideas or objectives)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS context_files (
            id UUID PRIMARY KEY,
            idea_id UUID REFERENCES ideas(id),
            objective_id UUID REFERENCES objectives(id),
            filename VARCHAR NOT NULL,
            content TEXT,
            size_bytes INTEGER DEFAULT 0,
            created_by UUID REFERENCES users(id),
            created_by_agent BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Objective files (single markdown file per objective)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS objective_files (
            id UUID PRIMARY KEY,
            objective_id UUID REFERENCES objectives(id) NOT NULL,
            content TEXT,
            content_hash VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by UUID REFERENCES users(id),
            UNIQUE(objective_id)
        )
    """)

    # Idea-Objective links (for graph edges)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS idea_objective_links (
            idea_id UUID REFERENCES ideas(id) NOT NULL,
            objective_id UUID REFERENCES objectives(id) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (idea_id, objective_id)
        )
    """)

    # Kernel embeddings for vector similarity search
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kernel_embeddings (
            id UUID PRIMARY KEY,
            kernel_file_id UUID REFERENCES kernel_files(id),
            idea_id UUID REFERENCES ideas(id),
            file_type VARCHAR NOT NULL,
            embedding FLOAT[768],
            content_hash VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create VSS index for similarity search
    try:
        conn.execute("""
            CREATE INDEX IF NOT EXISTS kernel_embedding_idx
            ON kernel_embeddings USING HNSW (embedding)
            WITH (metric = 'cosine')
        """)
        logger.info("vss_index_created", index="kernel_embedding_idx")
    except Exception as e:
        logger.warning(
            "vss_index_creation_failed",
            error=str(e),
            note="VSS extension may not be available - vector search will use fallback",
        )

    logger.info("schema_created")

    # Create property graph after all tables exist
    _create_property_graph(conn)


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
