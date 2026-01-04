# Slice 10: Sessions, Embeddings & Polish - Tasks

**Goal:** Session management UI, embeddings for kernel files, version restore, UI polish, demo data.

**Status:** Complete

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sessions dropdown location | Chat header, next to agent name | Contextual, easy access |
| New Session behavior | Clear chat, start fresh session | Simple, intuitive |
| Version history trigger | "History" button in file editor header | Discoverable |
| Version restore | Modal with confirmation (Cancel/Restore) | Prevent accidental overwrites |
| Demo data | CLI command (`uv run python -m crabgrass.seed`) | Repeatable, optional |
| Mobile responsive | Deferred | Not needed for MVP |
| Home page search | Title search only | Simple, covers main use case |

---

## Backend Tasks

### Embedding Concept

- [x] 1. Create `concepts/embedding.py`
  - `EmbeddingConcept` class
  - `generate(content: str) -> list[float]` - Generate 768-dim embedding via Gemini
  - `store(idea_id, file_type, embedding, content_hash)` - Store in kernel_embeddings
  - `get(idea_id, file_type)` - Retrieve embedding
  - Uses `text-embedding-004` model

### Database Schema

- [x] 2. Add migration for `kernel_embeddings` table
  - `id`, `kernel_file_id`, `idea_id`, `file_type`
  - `embedding FLOAT[768]` - Vector column
  - `content_hash` - For change detection
  - `created_at`
  - VSS index on embedding column

### Synchronizations

- [x] 3. Update `sync/synchronizations.py`
  - Import EmbeddingConcept
  - In `on_kernel_file_updated()`: Generate and store embedding
  - Add content hash check to avoid re-embedding unchanged content

### Version Restore API

- [x] 4. Add restore endpoint to `api/routes/ideas.py`
  - `POST /api/ideas/{id}/kernel/{type}/restore/{change_id}`
  - Get content from JJ history
  - Update kernel file with restored content
  - Trigger synchronizations (commit, embedding)
  - Return updated file

- [x] 5. Update `jj/repository.py`
  - Add `get_file_at_revision(idea_id, file_type, change_id)` method
  - Shell out to `jj file show` or similar

### Demo Data Seeding

- [x] 6. Create `crabgrass/seed.py` CLI module
  - Create 2-3 ideas at various completion stages
  - Add sample context files
  - Add conversation history to sessions
  - Use Sally as creator for ideas
  - Link one idea to an objective
  - Make runnable via `uv run python -m crabgrass.seed`

---

## Frontend Tasks

### Sessions Dropdown

- [x] 7. Update `concepts/chat.js`
  - Add sessions dropdown in chat header (next to agent name)
  - Load available sessions on mount
  - "New Session" option at top
  - Click session loads that session's history
  - New Session clears messages, sets sessionId to null

### Version History Modal

- [x] 8. Create `components/version-history-modal.js`
  - Modal component with version list
  - Each version shows: timestamp, description (commit message)
  - "Restore" button per version
  - Confirmation dialog: "Restore this version? This will replace current content."
  - Cancel / Restore buttons

- [x] 9. Update `pages/file-editor.js`
  - Add "History" button in header
  - On click: fetch history, show modal
  - On restore: call API, update canvas content

### API Client

- [x] 10. Update `api/client.js`
  - Add `restoreKernelFileVersion(ideaId, fileType, changeId)`

### Home Page Search

- [x] 11. Update `concepts/idea-list.js`
  - Add search input above ideas grid
  - Filter ideas by title (case-insensitive)
  - Client-side filtering (no API changes)
  - Debounce input for performance

### UI Polish

- [x] 12. Add loading states
  - Chat: already has loading indicator
  - File editor: show loading when fetching content
  - Home page: show loading when fetching ideas
  - Version history: show loading when fetching versions

- [x] 13. Add empty states
  - Home page: "No ideas yet. Create your first idea!"
  - Search results: "No ideas match your search"
  - Version history: "No version history available"

- [x] 14. Add keyboard shortcuts
  - File editor: Cmd+S / Ctrl+S to save
  - Prevent default browser save dialog

- [x] 15. Error handling improvements
  - Show user-friendly error messages
  - Add retry buttons where appropriate

---

## Tests

- [x] 16. Create `test_embedding_concept.py`
  - Test generate() returns 768-dim vector
  - Test store() and get() round-trip
  - Mock Gemini API calls

- [x] 17. Create `test_version_restore.py`
  - Test restore endpoint
  - Verify content is replaced
  - Verify sync is triggered

- [ ] 18. Manual testing
  - Switch between sessions in chat
  - Create new session, verify fresh start
  - View version history
  - Restore old version, verify content replaced
  - Search ideas by title
  - Run demo seed, verify data created

---

## Files Created/Modified

### Backend (New)
- `backend/crabgrass/concepts/embedding.py`
- `backend/crabgrass/seed.py`
- `backend/crabgrass/__main__.py`
- `backend/tests/test_embedding_concept.py`
- `backend/tests/test_version_restore.py`

### Backend (Modified)
- `backend/crabgrass/db/migrations.py` - Add kernel_embeddings table
- `backend/crabgrass/sync/synchronizations.py` - Add embedding generation
- `backend/crabgrass/api/routes/ideas.py` - Add restore endpoint
- `backend/crabgrass/jj/repository.py` - Add get_file_at_revision
- `backend/crabgrass/concepts/version.py` - Update get_file_content_at_version

### Frontend (New)
- `frontend/js/components/version-history-modal.js`

### Frontend (Modified)
- `frontend/js/concepts/chat.js` - Add sessions dropdown
- `frontend/js/pages/file-editor.js` - Add history button
- `frontend/js/concepts/idea-list.js` - Add search
- `frontend/js/api/client.js` - Add restore method
- `frontend/styles/components.css` - Add modal and version history styles
- `frontend/styles/main.css` - Add search input styles

---

*Started: 2026-01-03*
*Completed: 2026-01-03*
