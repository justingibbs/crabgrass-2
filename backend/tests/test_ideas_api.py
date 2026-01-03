"""Tests for Ideas API endpoints."""

import pytest
from pathlib import Path
import tempfile
import os

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_api.duckdb")

from fastapi.testclient import TestClient
from crabgrass.main import app
from crabgrass.db.connection import get_connection, close_connection, reset_database
from crabgrass.db.migrations import run_migrations, SALLY_USER_ID, SAM_USER_ID


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test."""
    reset_database()
    get_connection()
    run_migrations()
    yield
    close_connection()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sally_client():
    """Create a test client authenticated as Sally."""
    c = TestClient(app)
    c.cookies.set("crabgrass_dev_user", str(SALLY_USER_ID))
    return c


@pytest.fixture
def sam_client():
    """Create a test client authenticated as Sam."""
    c = TestClient(app)
    c.cookies.set("crabgrass_dev_user", str(SAM_USER_ID))
    return c


class TestListIdeas:
    """Tests for GET /api/ideas."""

    def test_list_ideas_empty(self, sally_client):
        """Test listing ideas when none exist."""
        response = sally_client.get("/api/ideas")

        assert response.status_code == 200
        data = response.json()
        assert "ideas" in data
        assert len(data["ideas"]) == 0

    def test_list_ideas_returns_user_ideas(self, sally_client):
        """Test that list returns ideas created by user."""
        # Create an idea
        sally_client.post("/api/ideas", json={"title": "Sally's Idea"})

        response = sally_client.get("/api/ideas")

        assert response.status_code == 200
        data = response.json()
        assert len(data["ideas"]) == 1
        assert data["ideas"][0]["title"] == "Sally's Idea"


class TestCreateIdea:
    """Tests for POST /api/ideas."""

    def test_create_idea_with_title(self, sally_client):
        """Test creating an idea with a custom title."""
        response = sally_client.post("/api/ideas", json={"title": "My Great Idea"})

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "My Great Idea"
        assert data["status"] == "draft"
        assert data["kernel_completion"] == 0
        assert "id" in data

    def test_create_idea_default_title(self, sally_client):
        """Test creating an idea with default title."""
        response = sally_client.post("/api/ideas", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Untitled Idea"

    def test_create_idea_initializes_kernel_files(self, sally_client):
        """Test that creating an idea initializes kernel files."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        # Get the idea with kernel files
        response = sally_client.get(f"/api/ideas/{idea_id}")

        assert response.status_code == 200
        data = response.json()
        assert "kernel_files" in data
        assert len(data["kernel_files"]) == 4

        file_types = {kf["file_type"] for kf in data["kernel_files"]}
        assert file_types == {"summary", "challenge", "approach", "coherent_steps"}


class TestGetIdea:
    """Tests for GET /api/ideas/{id}."""

    def test_get_idea(self, sally_client):
        """Test getting an idea by ID."""
        create_response = sally_client.post("/api/ideas", json={"title": "Get Test"})
        idea_id = create_response.json()["id"]

        response = sally_client.get(f"/api/ideas/{idea_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == idea_id
        assert data["title"] == "Get Test"

    def test_get_idea_includes_kernel_files(self, sally_client):
        """Test that getting an idea includes kernel file metadata."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        response = sally_client.get(f"/api/ideas/{idea_id}")

        assert response.status_code == 200
        data = response.json()
        assert "kernel_files" in data
        for kf in data["kernel_files"]:
            assert "file_type" in kf
            assert "is_complete" in kf
            assert kf["is_complete"] is False

    def test_get_nonexistent_idea(self, sally_client):
        """Test getting a non-existent idea returns 404."""
        response = sally_client.get("/api/ideas/99999999-9999-9999-9999-999999999999")

        assert response.status_code == 404


class TestUpdateIdea:
    """Tests for PATCH /api/ideas/{id}."""

    def test_update_idea_title(self, sally_client):
        """Test updating an idea's title."""
        create_response = sally_client.post("/api/ideas", json={"title": "Original"})
        idea_id = create_response.json()["id"]

        response = sally_client.patch(f"/api/ideas/{idea_id}", json={"title": "Updated"})

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated"

    def test_update_nonexistent_idea(self, sally_client):
        """Test updating a non-existent idea returns 404."""
        response = sally_client.patch(
            "/api/ideas/99999999-9999-9999-9999-999999999999", json={"title": "Test"}
        )

        assert response.status_code == 404


class TestDeleteIdea:
    """Tests for DELETE /api/ideas/{id}."""

    def test_delete_idea_archives(self, sally_client):
        """Test deleting an idea archives it."""
        create_response = sally_client.post("/api/ideas", json={"title": "To Delete"})
        idea_id = create_response.json()["id"]

        response = sally_client.delete(f"/api/ideas/{idea_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"

        # Verify idea is no longer in list
        list_response = sally_client.get("/api/ideas")
        assert len(list_response.json()["ideas"]) == 0

    def test_delete_nonexistent_idea(self, sally_client):
        """Test deleting a non-existent idea returns 404."""
        response = sally_client.delete("/api/ideas/99999999-9999-9999-9999-999999999999")

        assert response.status_code == 404


class TestUserIsolation:
    """Tests for user-based data isolation."""

    def test_users_see_own_ideas(self, sally_client, sam_client):
        """Test that users only see their own ideas."""
        # Sally creates an idea
        sally_client.post("/api/ideas", json={"title": "Sally's Private Idea"})

        # Sally should see it
        sally_response = sally_client.get("/api/ideas")
        assert len(sally_response.json()["ideas"]) == 1

        # Sam should not see it
        sam_response = sam_client.get("/api/ideas")
        assert len(sam_response.json()["ideas"]) == 0


class TestGetKernelFile:
    """Tests for GET /api/ideas/{id}/kernel/{type}."""

    def test_get_kernel_file(self, sally_client):
        """Test getting a kernel file's content."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        response = sally_client.get(f"/api/ideas/{idea_id}/kernel/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "summary"
        assert data["idea_id"] == idea_id
        assert "content" in data
        assert data["is_complete"] is False

    def test_get_kernel_file_all_types(self, sally_client):
        """Test getting all kernel file types."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        for file_type in ["summary", "challenge", "approach", "coherent_steps"]:
            response = sally_client.get(f"/api/ideas/{idea_id}/kernel/{file_type}")
            assert response.status_code == 200
            assert response.json()["file_type"] == file_type

    def test_get_kernel_file_invalid_type(self, sally_client):
        """Test getting an invalid kernel file type returns 400."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        response = sally_client.get(f"/api/ideas/{idea_id}/kernel/invalid_type")

        assert response.status_code == 400

    def test_get_kernel_file_nonexistent_idea(self, sally_client):
        """Test getting kernel file for non-existent idea returns 404."""
        response = sally_client.get(
            "/api/ideas/99999999-9999-9999-9999-999999999999/kernel/summary"
        )

        assert response.status_code == 404

    def test_get_kernel_file_has_template_content(self, sally_client):
        """Test that kernel files are initialized with template content."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        response = sally_client.get(f"/api/ideas/{idea_id}/kernel/challenge")

        assert response.status_code == 200
        data = response.json()
        assert "# Challenge" in data["content"]
        assert "problem" in data["content"].lower()


class TestUpdateKernelFile:
    """Tests for PUT /api/ideas/{id}/kernel/{type}."""

    def test_update_kernel_file(self, sally_client):
        """Test updating a kernel file's content."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        new_content = "# Summary\n\nThis is my updated summary content."
        response = sally_client.put(
            f"/api/ideas/{idea_id}/kernel/summary",
            json={"content": new_content}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["file_type"] == "summary"
        assert data["content"] == new_content

    def test_update_kernel_file_with_commit_message(self, sally_client):
        """Test updating a kernel file with a custom commit message."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        new_content = "# Challenge\n\nUpdated challenge."
        response = sally_client.put(
            f"/api/ideas/{idea_id}/kernel/challenge",
            json={
                "content": new_content,
                "commit_message": "Added specific challenge details"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == new_content

    def test_update_kernel_file_invalid_type(self, sally_client):
        """Test updating an invalid kernel file type returns 400."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        response = sally_client.put(
            f"/api/ideas/{idea_id}/kernel/invalid_type",
            json={"content": "Some content"}
        )

        assert response.status_code == 400

    def test_update_kernel_file_nonexistent_idea(self, sally_client):
        """Test updating kernel file for non-existent idea returns 404."""
        response = sally_client.put(
            "/api/ideas/99999999-9999-9999-9999-999999999999/kernel/summary",
            json={"content": "Some content"}
        )

        assert response.status_code == 404

    def test_update_kernel_file_persists(self, sally_client):
        """Test that updated content persists when retrieved."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        new_content = "# Approach\n\nMy detailed approach."
        sally_client.put(
            f"/api/ideas/{idea_id}/kernel/approach",
            json={"content": new_content}
        )

        # Get the file again
        get_response = sally_client.get(f"/api/ideas/{idea_id}/kernel/approach")
        assert get_response.json()["content"] == new_content


class TestKernelFileHistory:
    """Tests for GET /api/ideas/{id}/kernel/{type}/history."""

    def test_get_history_after_update(self, sally_client):
        """Test getting history shows commits after updates."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        # Update the file
        sally_client.put(
            f"/api/ideas/{idea_id}/kernel/summary",
            json={
                "content": "# Summary\n\nFirst update.",
                "commit_message": "First update"
            }
        )

        response = sally_client.get(f"/api/ideas/{idea_id}/kernel/summary/history")

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        # Should have at least the initial commit and the update
        assert len(data["versions"]) >= 1

    def test_get_history_invalid_type(self, sally_client):
        """Test getting history for invalid file type returns 400."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        response = sally_client.get(
            f"/api/ideas/{idea_id}/kernel/invalid_type/history"
        )

        assert response.status_code == 400

    def test_get_history_nonexistent_idea(self, sally_client):
        """Test getting history for non-existent idea returns 404."""
        response = sally_client.get(
            "/api/ideas/99999999-9999-9999-9999-999999999999/kernel/summary/history"
        )

        assert response.status_code == 404

    def test_get_history_multiple_updates(self, sally_client):
        """Test that multiple updates create multiple history entries."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        # Make several updates
        for i in range(3):
            sally_client.put(
                f"/api/ideas/{idea_id}/kernel/summary",
                json={
                    "content": f"# Summary\n\nUpdate number {i + 1}.",
                    "commit_message": f"Update {i + 1}"
                }
            )

        response = sally_client.get(f"/api/ideas/{idea_id}/kernel/summary/history")

        assert response.status_code == 200
        data = response.json()
        # Should have initial commit plus 3 updates
        assert len(data["versions"]) >= 3
