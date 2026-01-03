# Slice 8: Context Files - Tasks

**Goal:** Complete context file functionality with user-facing CRUD and ContextAgent insights.

**Status:** Complete

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Context file editing | File Editor page | Consistent with kernel files |
| ContextAgent behavior | Wait for user to ask | Non-intrusive, user-driven |
| Insight delivery | CoherenceAgent chat | Centralized at workspace level |
| Route organization | New files.py | Clean separation per spec |
| URL identifiers | file_id for PUT/DELETE | RESTful, avoids filename encoding issues |

---

## Backend Tasks

### ContextFile Concept

- [x] 1. Add `delete()` method to `concepts/context_file.py`
  - Remove from database
  - Remove from JJ repository
  - Log deletion

### ContextAgent

- [x] 2. Create `concepts/agents/context_agent.py`
  - `AGENT_TYPE = "context"`
  - `extract(idea_id, content)` - Find insights relevant to kernel files
  - `summarize(content)` - Generate brief summary
  - `map_to_kernel(insight)` - Which kernel file does this relate to?
  - `coach(idea_id, context_file_id, user_message, session_id)` - Chat about the file

- [x] 3. Add ContextAgent prompts to `ai/prompts.py`
  - `CONTEXT_AGENT_SYSTEM_PROMPT` - Role, capabilities
  - `CONTEXT_AGENT_EXTRACTION_PROMPT` - For extracting insights

- [x] 4. Register ContextAgent in `concepts/agents/__init__.py`
  - Add to AGENT_TYPE_TO_AGENT map
  - Export in __all__

### API Routes

- [x] 5. Create `api/routes/files.py` with context file routes
  - `GET /api/ideas/{id}/context` - List context files (move from coherence.py)
  - `POST /api/ideas/{id}/context` - Create context file
  - `GET /api/ideas/{id}/context/{file_id}` - Get context file by ID
  - `PUT /api/ideas/{id}/context/{file_id}` - Update context file
  - `DELETE /api/ideas/{id}/context/{file_id}` - Delete context file
  - `POST /api/ideas/{id}/context/{file_id}/chat` - Chat with ContextAgent

- [x] 6. Remove context file routes from `api/routes/coherence.py`
  - Remove GET /context and GET /context/{filename}

- [x] 7. Register new routes in `main.py`

### Synchronizations

- [x] 8. Add `on_context_file_created()` to `sync/synchronizations.py`
  - Trigger ContextAgent.extract()
  - Add insights to CoherenceAgent session as agent messages

---

## Frontend Tasks

### API Client

- [x] 9. Update `api/client.js` with context file methods
  - `createContextFile(ideaId, filename, content)`
  - `updateContextFile(ideaId, fileId, content)`
  - `deleteContextFile(ideaId, fileId)`
  - `getContextFileById(ideaId, fileId)` - Updated to use ID
  - `sendContextChatMessage(ideaId, fileId, message, sessionId)`

### Idea Workspace

- [x] 10. Enable "+ New File" button in `concepts/idea-workspace.js`
  - Show creation modal on click
  - Create file via API
  - Reload context files list
  - Navigate to File Editor for new file

- [x] 11. Create context file creation modal
  - Input for filename (auto-adds .md)
  - Validation feedback (no spaces, alphanumeric + hyphen/underscore)
  - Create and Cancel buttons

- [x] 12. Update context file card click behavior
  - Navigate to File Editor instead of showing modal
  - Remove modal view code (or keep for quick preview option)

### File Editor

- [x] 13. Update `pages/file-editor.js` to support context files
  - Detect if editing kernel file or context file
  - Show ContextAgent in chat for context files
  - Add Delete button for context files (not kernel files)
  - Handle delete with confirmation

### Router

- [x] 14. Add route for context file editor
  - `#/ideas/:id/context/:fileId` → File Editor with context mode

---

## Tests

- [x] 15. Create/update `test_context_file.py`
  - Test delete() method
  - Test JJ integration on delete

- [x] 16. Create `test_context_agent.py`
  - Test extract() with sample content
  - Test map_to_kernel() logic
  - Test coach() responses

- [x] 17. Create `test_context_files_api.py`
  - Test all CRUD endpoints
  - Test authorization
  - Test validation (filename, size)

- [ ] 18. Manual testing
  - Create context file from UI
  - Edit context file in File Editor
  - Chat with ContextAgent
  - Delete context file
  - Verify insights appear in CoherenceAgent chat

---

## Files to Create

### Backend (New)
- `backend/crabgrass/concepts/agents/context_agent.py`
- `backend/crabgrass/api/routes/files.py`

### Backend (Modified)
- `backend/crabgrass/concepts/context_file.py` - Add delete()
- `backend/crabgrass/ai/prompts.py` - Add context agent prompts
- `backend/crabgrass/concepts/agents/__init__.py` - Register ContextAgent
- `backend/crabgrass/api/routes/coherence.py` - Remove context routes
- `backend/crabgrass/sync/synchronizations.py` - Add on_context_file_created
- `backend/crabgrass/main.py` - Register files routes

### Frontend (Modified)
- `frontend/js/api/client.js` - Add context CRUD methods
- `frontend/js/concepts/idea-workspace.js` - Enable creation, update navigation
- `frontend/js/pages/file-editor.js` - Support context files
- `frontend/js/main.js` - Add context file route

### Tests (New)
- `backend/tests/test_context_agent.py`
- `backend/tests/test_context_files_api.py`

---

*Started: 2026-01-03*
*Completed: TBD*
