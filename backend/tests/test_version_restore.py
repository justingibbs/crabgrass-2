"""Tests for version restore API endpoint."""

import pytest
from pathlib import Path
import tempfile
import os
from unittest.mock import patch, AsyncMock

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_restore.duckdb")

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


@pytest.fixture(autouse=True)
def mock_async_sync():
    """Mock the async synchronization to avoid event loop issues in tests."""
    with patch(
        "crabgrass.api.routes.ideas.on_kernel_file_updated_async",
        new_callable=AsyncMock
    ):
        yield


@pytest.fixture(autouse=True)
def mock_embedding():
    """Mock the embedding concept to avoid foreign key issues in tests."""
    with patch("crabgrass.sync.synchronizations.embedding_concept") as mock:
        mock.needs_update.return_value = False  # Skip embedding updates
        yield


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


class TestRestoreKernelFileVersion:
    """Tests for POST /api/ideas/{id}/kernel/{type}/restore/{change_id}."""

    def test_restore_version_replaces_content(self, sally_client):
        """Test that restoring a version replaces the current content."""
        # Create an idea
        create_response = sally_client.post("/api/ideas", json={"title": "Restore Test"})
        idea_id = create_response.json()["id"]

        # Make first update
        first_content = "# Summary\n\nFirst version content."
        sally_client.put(
            f"/api/ideas/{idea_id}/kernel/summary",
            json={"content": first_content}
        )

        # Make second update
        second_content = "# Summary\n\nSecond version content (latest)."
        sally_client.put(
            f"/api/ideas/{idea_id}/kernel/summary",
            json={"content": second_content}
        )

        # Get history after both updates - first update is now versions[1]
        history_response = sally_client.get(f"/api/ideas/{idea_id}/kernel/summary/history")
        versions = history_response.json()["versions"]
        # versions[0] = second update, versions[1] = first update, versions[2] = initialize
        first_version_change_id = versions[1]["change_id"]

        # Verify current content is second version
        get_response = sally_client.get(f"/api/ideas/{idea_id}/kernel/summary")
        assert get_response.json()["content"] == second_content

        # Restore to first version
        restore_response = sally_client.post(
            f"/api/ideas/{idea_id}/kernel/summary/restore/{first_version_change_id}"
        )

        assert restore_response.status_code == 200
        data = restore_response.json()
        assert data["content"] == first_content
        assert data["restored_from"] == first_version_change_id
        assert data["file_type"] == "summary"
        assert data["idea_id"] == idea_id

    def test_restore_version_persists(self, sally_client):
        """Test that restored content persists when retrieved again."""
        # Create an idea
        create_response = sally_client.post("/api/ideas", json={"title": "Persist Test"})
        idea_id = create_response.json()["id"]

        # Make first update
        original_content = "# Challenge\n\nOriginal challenge."
        sally_client.put(
            f"/api/ideas/{idea_id}/kernel/challenge",
            json={"content": original_content}
        )

        # Make another update
        sally_client.put(
            f"/api/ideas/{idea_id}/kernel/challenge",
            json={"content": "# Challenge\n\nModified challenge."}
        )

        # Get history after both updates - original is now versions[1]
        history_response = sally_client.get(f"/api/ideas/{idea_id}/kernel/challenge/history")
        versions = history_response.json()["versions"]
        original_change_id = versions[1]["change_id"]

        # Restore to original
        sally_client.post(
            f"/api/ideas/{idea_id}/kernel/challenge/restore/{original_change_id}"
        )

        # Verify the content persists
        get_response = sally_client.get(f"/api/ideas/{idea_id}/kernel/challenge")
        assert get_response.json()["content"] == original_content

    def test_restore_version_invalid_file_type(self, sally_client):
        """Test restoring with invalid file type returns 400."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        response = sally_client.post(
            f"/api/ideas/{idea_id}/kernel/invalid_type/restore/abc123"
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_restore_version_nonexistent_idea(self, sally_client):
        """Test restoring for non-existent idea returns 404."""
        response = sally_client.post(
            "/api/ideas/99999999-9999-9999-9999-999999999999/kernel/summary/restore/abc123"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_restore_version_invalid_change_id(self, sally_client):
        """Test restoring with invalid change_id returns 404."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        response = sally_client.post(
            f"/api/ideas/{idea_id}/kernel/summary/restore/invalid_change_id"
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_restore_version_same_org_allowed(self, sally_client, sam_client):
        """Test that users in the same org can restore each other's ideas."""
        # Sally creates an idea
        create_response = sally_client.post("/api/ideas", json={"title": "Sally's Idea"})
        idea_id = create_response.json()["id"]

        # Sally makes an update
        sally_client.put(
            f"/api/ideas/{idea_id}/kernel/summary",
            json={"content": "# Summary\n\nSally's content."}
        )

        # Sally makes second update
        sally_client.put(
            f"/api/ideas/{idea_id}/kernel/summary",
            json={"content": "# Summary\n\nSally's updated content."}
        )

        # Get history - first update is versions[1]
        history_response = sally_client.get(f"/api/ideas/{idea_id}/kernel/summary/history")
        versions = history_response.json()["versions"]
        change_id = versions[1]["change_id"]

        # Sam (same org) should be able to restore
        response = sam_client.post(
            f"/api/ideas/{idea_id}/kernel/summary/restore/{change_id}"
        )

        assert response.status_code == 200
        assert response.json()["content"] == "# Summary\n\nSally's content."

    def test_restore_version_all_file_types(self, sally_client):
        """Test restoring works for all kernel file types."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        for file_type in ["summary", "challenge", "approach", "coherent_steps"]:
            # Make first update
            original = f"# {file_type.title()}\n\nOriginal content for {file_type}."
            sally_client.put(
                f"/api/ideas/{idea_id}/kernel/{file_type}",
                json={"content": original}
            )

            # Update again
            sally_client.put(
                f"/api/ideas/{idea_id}/kernel/{file_type}",
                json={"content": f"Modified {file_type}"}
            )

            # Get history after both updates - original is versions[1]
            history = sally_client.get(f"/api/ideas/{idea_id}/kernel/{file_type}/history")
            versions = history.json()["versions"]
            change_id = versions[1]["change_id"]

            # Restore
            response = sally_client.post(
                f"/api/ideas/{idea_id}/kernel/{file_type}/restore/{change_id}"
            )

            assert response.status_code == 200
            assert response.json()["content"] == original

    def test_restore_version_response_format(self, sally_client):
        """Test that restore response has correct format."""
        create_response = sally_client.post("/api/ideas", json={"title": "Test"})
        idea_id = create_response.json()["id"]

        # Make first update
        sally_client.put(
            f"/api/ideas/{idea_id}/kernel/approach",
            json={"content": "# Approach\n\nTest content."}
        )

        # Update again
        sally_client.put(
            f"/api/ideas/{idea_id}/kernel/approach",
            json={"content": "# Approach\n\nModified."}
        )

        # Get history after both updates - first update is versions[1]
        history = sally_client.get(f"/api/ideas/{idea_id}/kernel/approach/history")
        change_id = history.json()["versions"][1]["change_id"]

        # Restore
        response = sally_client.post(
            f"/api/ideas/{idea_id}/kernel/approach/restore/{change_id}"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert "id" in data
        assert "idea_id" in data
        assert "file_type" in data
        assert "content" in data
        assert "is_complete" in data
        assert "updated_at" in data
        assert "restored_from" in data

        # Verify types
        assert isinstance(data["id"], str)
        assert isinstance(data["is_complete"], bool)
        assert isinstance(data["restored_from"], str)
