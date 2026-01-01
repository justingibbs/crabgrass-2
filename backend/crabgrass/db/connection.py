"""DuckDB connection management."""

import duckdb
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import structlog

from ..config import settings

logger = structlog.get_logger()

# Global connection for the application
_connection: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """Get or create the global DuckDB connection."""
    global _connection
    if _connection is None:
        _connection = _create_connection()
    return _connection


def _create_connection() -> duckdb.DuckDBPyConnection:
    """Create a new DuckDB connection with extensions loaded."""
    # Ensure data directory exists
    db_path = settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("connecting_to_database", path=str(db_path))

    conn = duckdb.connect(str(db_path))

    # Load extensions
    _load_extensions(conn)

    return conn


def _load_extensions(conn: duckdb.DuckDBPyConnection) -> None:
    """Load and verify DuckDB extensions."""
    extensions = [
        ("vss", "Vector Similarity Search"),
        # Note: DuckPGQ may need to be installed separately or may not be available
        # We'll try to load it but won't fail if it's not available
    ]

    for ext_name, ext_desc in extensions:
        try:
            conn.execute(f"INSTALL {ext_name}")
            conn.execute(f"LOAD {ext_name}")
            logger.info("extension_loaded", extension=ext_name, description=ext_desc)
        except Exception as e:
            logger.warning("extension_load_failed", extension=ext_name, error=str(e))

    # Try DuckPGQ separately as it may not be available in all DuckDB versions
    try:
        conn.execute("INSTALL duckpgq FROM community")
        conn.execute("LOAD duckpgq")
        logger.info("extension_loaded", extension="duckpgq", description="Property Graph Queries")
    except Exception as e:
        logger.warning(
            "extension_load_failed",
            extension="duckpgq",
            error=str(e),
            note="DuckPGQ may not be available - graph features will be limited",
        )


@contextmanager
def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Context manager for database operations."""
    conn = get_connection()
    try:
        yield conn
    except Exception:
        # DuckDB doesn't have explicit transactions by default for reads
        # but we could add rollback logic here if needed
        raise


def close_connection() -> None:
    """Close the global connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
        logger.info("database_connection_closed")


def reset_database() -> None:
    """Reset the database (for testing)."""
    close_connection()
    if settings.database_path.exists():
        settings.database_path.unlink()
    logger.info("database_reset", path=str(settings.database_path))
