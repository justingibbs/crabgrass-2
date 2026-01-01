"""Tests for authentication routes."""

import pytest
from pathlib import Path
import tempfile
import os

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_auth.duckdb")

from fastapi.testclient import TestClient
from crabgrass.main import app
from crabgrass.db.connection import close_connection, reset_database
from crabgrass.db.migrations import SALLY_USER_ID, SAM_USER_ID, run_migrations


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test."""
    reset_database()
    yield
    close_connection()


@pytest.fixture
def client():
    """Create test client with lifespan handling."""
    # Use context manager to properly trigger lifespan events
    with TestClient(app) as client:
        yield client


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_users(client):
    """Test listing available dev users."""
    response = client.get("/api/auth/users")
    assert response.status_code == 200

    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 2

    names = [u["name"] for u in data["users"]]
    assert "Sally Chen" in names
    assert "Sam White" in names


def test_get_current_user_defaults_to_sally(client):
    """Test that /me defaults to Sally when no cookie set."""
    response = client.get("/api/auth/me")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Sally Chen"
    assert data["id"] == str(SALLY_USER_ID)


def test_switch_user_to_sam(client):
    """Test switching to Sam."""
    response = client.post(f"/api/auth/switch/{SAM_USER_ID}")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Sam White"
    assert data["role"] == "org_admin"

    # Check cookie was set
    assert "crabgrass_dev_user" in response.cookies


def test_switch_user_persists(client):
    """Test that user switch persists via cookie."""
    # Switch to Sam
    client.post(f"/api/auth/switch/{SAM_USER_ID}")

    # Get current user should return Sam
    response = client.get("/api/auth/me")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Sam White"


def test_switch_to_invalid_user(client):
    """Test switching to non-existent user returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000099"
    response = client.post(f"/api/auth/switch/{fake_id}")
    assert response.status_code == 404


def test_user_has_title(client):
    """Test that user response includes title from preferences."""
    response = client.get("/api/auth/me")
    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Frontline Worker"

    # Switch to Sam and check his title
    client.post(f"/api/auth/switch/{SAM_USER_ID}")
    response = client.get("/api/auth/me")
    assert response.json()["title"] == "VP"
