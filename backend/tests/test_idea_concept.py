"""Tests for Idea and KernelFile concepts."""

import pytest
from pathlib import Path
import tempfile
import os
from uuid import UUID

# Override settings before importing modules
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / "test_crabgrass_ideas.duckdb")

from crabgrass.db.connection import get_connection, close_connection, reset_database
from crabgrass.db.migrations import run_migrations, SALLY_USER_ID, ACME_ORG_ID, KERNEL_FILE_TYPES
from crabgrass.concepts.idea import IdeaConcept
from crabgrass.concepts.kernel_file import KernelFileConcept
from crabgrass.sync.synchronizations import on_idea_created


@pytest.fixture(autouse=True)
def clean_db():
    """Reset database before each test."""
    reset_database()
    get_connection()
    run_migrations()
    yield
    close_connection()


@pytest.fixture
def idea_concept():
    """Create an IdeaConcept instance."""
    return IdeaConcept()


@pytest.fixture
def kernel_file_concept():
    """Create a KernelFileConcept instance."""
    return KernelFileConcept()


class TestIdeaConcept:
    """Tests for IdeaConcept."""

    def test_create_idea(self, idea_concept):
        """Test creating a new idea."""
        idea = idea_concept.create(
            org_id=ACME_ORG_ID,
            user_id=SALLY_USER_ID,
            title="Test Idea",
        )

        assert idea.title == "Test Idea"
        assert idea.status == "draft"
        assert idea.kernel_completion == 0
        assert idea.objective_id is None
        assert idea.org_id == ACME_ORG_ID
        assert idea.creator_id == SALLY_USER_ID

    def test_create_idea_with_objective(self, idea_concept):
        """Test creating an idea with an objective."""
        # First create an objective
        conn = get_connection()
        objective_id = UUID("00000000-0000-0000-0000-000000000100")
        conn.execute(
            """
            INSERT INTO objectives (id, org_id, title, created_by)
            VALUES (?, ?, ?, ?)
            """,
            [str(objective_id), str(ACME_ORG_ID), "Test Objective", str(SALLY_USER_ID)],
        )

        idea = idea_concept.create(
            org_id=ACME_ORG_ID,
            user_id=SALLY_USER_ID,
            title="Idea with Objective",
            objective_id=objective_id,
        )

        assert idea.objective_id == objective_id

    def test_get_idea(self, idea_concept):
        """Test getting an idea by ID."""
        created = idea_concept.create(
            org_id=ACME_ORG_ID,
            user_id=SALLY_USER_ID,
            title="Get Test",
        )

        fetched = idea_concept.get(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == "Get Test"

    def test_get_nonexistent_idea(self, idea_concept):
        """Test getting a non-existent idea returns None."""
        fake_id = UUID("99999999-9999-9999-9999-999999999999")
        result = idea_concept.get(fake_id)
        assert result is None

    def test_list_for_user(self, idea_concept):
        """Test listing ideas for a user."""
        # Create some ideas
        idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "Idea 1")
        idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "Idea 2")

        ideas = idea_concept.list_for_user(ACME_ORG_ID, SALLY_USER_ID)

        assert len(ideas) == 2
        titles = {i.title for i in ideas}
        assert "Idea 1" in titles
        assert "Idea 2" in titles

    def test_update_idea_title(self, idea_concept):
        """Test updating an idea's title."""
        idea = idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "Original Title")

        updated = idea_concept.update(idea.id, title="New Title")

        assert updated.title == "New Title"

    def test_archive_idea(self, idea_concept):
        """Test archiving an idea."""
        idea = idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "To Archive")

        idea_concept.archive(idea.id)

        fetched = idea_concept.get(idea.id)
        assert fetched.status == "archived"

    def test_archived_ideas_not_in_list(self, idea_concept):
        """Test that archived ideas don't appear in list."""
        idea = idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "To Archive")
        idea_concept.archive(idea.id)

        ideas = idea_concept.list_for_user(ACME_ORG_ID, SALLY_USER_ID)
        assert len(ideas) == 0


class TestKernelFileConcept:
    """Tests for KernelFileConcept."""

    def test_initialize_all_creates_four_files(self, idea_concept, kernel_file_concept):
        """Test that initialize_all creates 4 kernel files."""
        idea = idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "Test")

        files = kernel_file_concept.initialize_all(idea.id, SALLY_USER_ID)

        assert len(files) == 4
        file_types = {f.file_type for f in files}
        assert file_types == set(KERNEL_FILE_TYPES)

    def test_kernel_files_have_template_content(self, idea_concept, kernel_file_concept):
        """Test that kernel files are created with template content."""
        idea = idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "Test")
        kernel_file_concept.initialize_all(idea.id, SALLY_USER_ID)

        summary = kernel_file_concept.get(idea.id, "summary")
        assert summary is not None
        assert "# Summary" in summary.content
        assert "Describe your idea" in summary.content

        challenge = kernel_file_concept.get(idea.id, "challenge")
        assert challenge is not None
        assert "# Challenge" in challenge.content

    def test_kernel_files_start_incomplete(self, idea_concept, kernel_file_concept):
        """Test that kernel files start as incomplete."""
        idea = idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "Test")
        kernel_file_concept.initialize_all(idea.id, SALLY_USER_ID)

        files = kernel_file_concept.get_all(idea.id)
        for f in files:
            assert f.is_complete is False

    def test_get_all_returns_ordered(self, idea_concept, kernel_file_concept):
        """Test that get_all returns files in order."""
        idea = idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "Test")
        kernel_file_concept.initialize_all(idea.id, SALLY_USER_ID)

        files = kernel_file_concept.get_all(idea.id)

        # Should be in order: summary, challenge, approach, coherent_steps
        assert files[0].file_type == "summary"
        assert files[1].file_type == "challenge"
        assert files[2].file_type == "approach"
        assert files[3].file_type == "coherent_steps"

    def test_update_kernel_file(self, idea_concept, kernel_file_concept):
        """Test updating kernel file content."""
        idea = idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "Test")
        kernel_file_concept.initialize_all(idea.id, SALLY_USER_ID)

        updated = kernel_file_concept.update(
            idea.id, "summary", "# New Content\n\nThis is updated.", SALLY_USER_ID
        )

        assert updated.content == "# New Content\n\nThis is updated."

    def test_mark_complete(self, idea_concept, kernel_file_concept):
        """Test marking a kernel file as complete."""
        idea = idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "Test")
        kernel_file_concept.initialize_all(idea.id, SALLY_USER_ID)

        kernel_file_concept.mark_complete(idea.id, "summary")

        file = kernel_file_concept.get(idea.id, "summary")
        assert file.is_complete is True

    def test_get_completion_count(self, idea_concept, kernel_file_concept):
        """Test getting completion count."""
        idea = idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "Test")
        kernel_file_concept.initialize_all(idea.id, SALLY_USER_ID)

        assert kernel_file_concept.get_completion_count(idea.id) == 0

        kernel_file_concept.mark_complete(idea.id, "summary")
        assert kernel_file_concept.get_completion_count(idea.id) == 1

        kernel_file_concept.mark_complete(idea.id, "challenge")
        assert kernel_file_concept.get_completion_count(idea.id) == 2


class TestSynchronizations:
    """Tests for synchronizations."""

    def test_on_idea_created_initializes_kernel_files(self, idea_concept, kernel_file_concept):
        """Test that on_idea_created initializes kernel files."""
        idea = idea_concept.create(ACME_ORG_ID, SALLY_USER_ID, "Sync Test")

        # Trigger synchronization
        on_idea_created(idea)

        # Verify kernel files were created
        files = kernel_file_concept.get_all(idea.id)
        assert len(files) == 4
