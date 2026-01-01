"""Tests for database connection and extensions."""

import pytest
from pathlib import Path
import tempfile
import os

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass.duckdb")

from crabgrass.db.connection import get_connection, close_connection, reset_database
from crabgrass.db.migrations import run_migrations


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test."""
    reset_database()
    yield
    close_connection()


def test_database_connects():
    """Test that DuckDB connects successfully."""
    conn = get_connection()
    assert conn is not None

    # Simple query to verify connection works
    result = conn.execute("SELECT 1 as value").fetchone()
    assert result[0] == 1


def test_extensions_load():
    """Test that VSS extension loads (DuckPGQ may not be available)."""
    conn = get_connection()

    # Check if VSS is loaded
    extensions = conn.execute(
        "SELECT extension_name, loaded FROM duckdb_extensions() WHERE loaded = true"
    ).fetchall()

    extension_names = [e[0] for e in extensions]

    # VSS should be loaded
    assert "vss" in extension_names, f"VSS not loaded. Loaded extensions: {extension_names}"


def test_migrations_create_tables():
    """Test that migrations create required tables."""
    conn = get_connection()
    run_migrations()

    # Check tables exist
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()
    table_names = {t[0] for t in tables}

    assert "organizations" in table_names
    assert "users" in table_names
    assert "objectives" in table_names


def test_migrations_seed_dev_data():
    """Test that migrations seed dev users."""
    conn = get_connection()
    run_migrations()

    # Check Acme Corp exists
    org = conn.execute("SELECT name FROM organizations LIMIT 1").fetchone()
    assert org[0] == "Acme Corp"

    # Check users exist
    users = conn.execute("SELECT name, role FROM users ORDER BY name").fetchall()
    assert len(users) == 2

    user_names = [u[0] for u in users]
    assert "Sally Chen" in user_names
    assert "Sam White" in user_names


def test_migrations_idempotent():
    """Test that migrations can be run multiple times."""
    conn = get_connection()

    # Run migrations twice
    run_migrations()
    run_migrations()

    # Should still have exactly 2 users
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    assert count == 2
