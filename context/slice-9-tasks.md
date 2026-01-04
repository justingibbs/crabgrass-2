# Slice 9: Objectives - Tasks

**Goal:** Objectives CRUD, ObjectiveAgent, Graph (DuckPGQ), link ideas to objectives.

**Status:** Complete

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Graph database | DuckPGQ from the start | Will be building out graph relationships extensively later |
| Objective file storage | `objective_files` table | Same pattern as kernel files, single file per objective |
| Objective context files | Shared `context_files` with `objective_id` | Consistent with idea context files |
| Non-admin behavior | Can view & link ideas, can't edit objective | Members need to see objectives to link their ideas |
| Pre-seeded objectives | Skip | User will add data manually |

---

## Backend Tasks

### Database Schema

- [x] 1. Update `db/migrations.py` with incremental migrations
  - Add `objective_files` table (id, objective_id, content, content_hash, updated_at, updated_by)
  - Add `objective_id` column to `context_files` table (nullable)
  - Add `objective_id` column to `sessions` table (nullable)
  - Create DuckPGQ graph schema for `idea_graph`

### Objective Concept

- [x] 2. Create `concepts/objective.py`
  - `Objective` dataclass with all fields
  - `ObjectiveConcept` class with:
    - `create(org_id, title, description, owner_id, timeframe)` - Admin only
    - `get(objective_id)`
    - `list(org_id)` - All org members
    - `update(objective_id, **fields)` - Admin only
    - `archive(objective_id)` - Admin only
    - `get_ideas(objective_id)` - Get linked ideas

### ObjectiveFile Concept

- [x] 3. Create `concepts/objective_file.py`
  - `ObjectiveFile` dataclass
  - `ObjectiveFileConcept` class with:
    - `initialize(objective_id)` - Create empty file on objective creation
    - `get(objective_id)`
    - `update(objective_id, content, user_id)`

### Graph Concept (DuckPGQ)

- [x] 4. Create `concepts/graph.py`
  - `GraphConcept` class with:
    - `link_idea_to_objective(idea_id, objective_id)` - Create SUPPORTS edge
    - `unlink_idea_from_objective(idea_id, objective_id)` - Remove SUPPORTS edge
    - `get_ideas_for_objective(objective_id)` - Get linked ideas
    - `get_objective_for_idea(idea_id)` - Get linked objective
    - `unlink_idea(idea_id)` - Remove all edges for an idea

### ObjectiveAgent

- [x] 5. Create `concepts/agents/objective_agent.py`
  - `AGENT_TYPE = "objective"`
  - `coach(objective_id, content, user_message, session_id)` - Help define objective
  - `summarize_alignment(objective_id)` - Summarize how linked ideas support objective
  - `evaluate(objective_id, content)` - Provide feedback on objective quality

- [x] 6. Add ObjectiveAgent prompts to `ai/prompts.py`
  - `OBJECTIVE_AGENT_SYSTEM_PROMPT` - Role, coaching approach
  - `OBJECTIVE_AGENT_ALIGNMENT_PROMPT` - For summarizing idea alignment
  - `OBJECTIVE_AGENT_EVALUATION_PROMPT` - For evaluating objective quality

- [x] 7. Register ObjectiveAgent in `concepts/agents/__init__.py`

### API Routes

- [x] 8. Create `api/routes/objectives.py`
  - `GET /api/objectives` - List org objectives
  - `POST /api/objectives` - Create objective (admin only)
  - `GET /api/objectives/{id}` - Get objective details with linked ideas count
  - `PATCH /api/objectives/{id}` - Update objective (admin only)
  - `DELETE /api/objectives/{id}` - Archive objective (admin only)
  - `GET /api/objectives/{id}/ideas` - Get ideas linked to objective
  - `GET /api/objectives/{id}/file` - Get objective file content
  - `PUT /api/objectives/{id}/file` - Update objective file content
  - `POST /api/objectives/{id}/chat` - Chat with ObjectiveAgent
  - `POST /api/objectives/{id}/alignment/{idea_id}` - Check idea alignment
  - `GET /api/objectives/{id}/sessions` - List objective sessions
  - `GET /api/objectives/{id}/context` - List objective context files
  - `POST /api/objectives/{id}/context` - Create objective context file
  - `GET /api/objectives/{id}/context/{file_id}` - Get context file
  - `PUT /api/objectives/{id}/context/{file_id}` - Update context file
  - `DELETE /api/objectives/{id}/context/{file_id}` - Delete context file

- [x] 9. Add route to link idea to objective
  - `POST /api/ideas/{id}/objective` - Link idea to objective (body: {objective_id})
  - `DELETE /api/ideas/{id}/objective` - Unlink idea from objective

- [x] 10. Register routes in `main.py`

### Synchronizations

- [x] 11. Add to `sync/synchronizations.py`
  - `on_objective_created(objective)` - Initialize objective file
  - `on_idea_linked_to_objective(idea_id, objective_id)` - Create SUPPORTS edge in graph
  - `on_idea_unlinked_from_objective(idea_id, objective_id)` - Remove SUPPORTS edge

### Update Existing Code

- [x] 12. Update `concepts/context_file.py`
  - Add `objective_id` parameter to `create()`
  - Update queries to filter by `idea_id` OR `objective_id`
  - Add `list_for_objective(objective_id)` method

---

## Frontend Tasks

### API Client

- [x] 13. Update `api/client.js` with objective methods
  - `getObjectives()` - List all objectives
  - `createObjective(data)` - Create objective (admin)
  - `getObjective(objectiveId)` - Get objective with details
  - `updateObjective(objectiveId, data)` - Update objective (admin)
  - `archiveObjective(objectiveId)` - Archive objective (admin)
  - `getObjectiveIdeas(objectiveId)` - Get linked ideas
  - `getObjectiveFile(objectiveId)` - Get file content
  - `updateObjectiveFile(objectiveId, content)` - Update file
  - `sendObjectiveChatMessage(objectiveId, message, sessionId)` - Chat with agent
  - `checkObjectiveAlignment(objectiveId, ideaId)` - Check alignment
  - `getObjectiveSessions(objectiveId)` - List sessions
  - `linkIdeaToObjective(ideaId, objectiveId)` - Link idea
  - `unlinkIdeaFromObjective(ideaId)` - Unlink idea
  - Objective context file methods (create, get, update, delete)

### Home Page

- [x] 14. Update home page with objectives section
  - Created `concepts/objective-list.js`
  - Updated `concepts/idea-list.js` to include ObjectiveList
  - Render objective cards (title, timeframe, status, linked ideas count)
  - Click navigates to `#/objectives/:id`
  - Show "+ New Objective" button for admins only

### Objective Workspace

- [x] 15. Create `concepts/objective-workspace.js`
  - Similar structure to `idea-workspace.js`
  - State: objective, objectiveFile, contextFiles, linkedIdeas, isAdmin
  - Sections:
    - Header: Title (editable for admin), timeframe, status
    - Chat with ObjectiveAgent
    - OBJECTIVE section (single file card)
    - LINKED IDEAS section (clickable cards)
    - CONTEXT FILES section (for admins)
  - Non-admins see read-only view

### File Editor for Objectives

- [x] 16. Update `pages/file-editor.js`
  - Support objective file type and objective_context mode
  - Route: `#/objectives/:id/file`
  - Route: `#/objectives/:id/context/:fileId`
  - Show ObjectiveAgent in chat panel
  - Admin-only editing for objective files

### Router

- [x] 17. Update `main.js` routes
  - `#/objectives/:id` → Objective Workspace
  - `#/objectives/:id/file` → File Editor for objective file
  - `#/objectives/:id/context/:fileId` → File Editor for objective context file

### Idea Workspace Updates

- [x] 18. Update `concepts/idea-workspace.js`
  - Enable objective selector dropdown
  - Display linked objective name with link to workspace and "Unlink" button
  - Display dropdown selector if no objective is linked

### Chat Component Updates

- [x] 19. Update `concepts/chat.js`
  - Support objectiveId for objective-based chats
  - Handle objective sessions loading and sending

---

## Tests

- [x] 20. Existing tests updated
  - Fixed `test_context_file.py` to use keyword arguments
  - All 157 tests passing

- [ ] 21. Create `test_objective_concept.py` (future enhancement)
- [ ] 22. Create `test_graph_concept.py` (future enhancement)
- [ ] 23. Create `test_objective_agent.py` (future enhancement)
- [ ] 24. Create `test_objectives_api.py` (future enhancement)

- [ ] 25. Manual testing
  - Create objective as Sam (admin)
  - View objectives as Sally (member)
  - Link idea to objective
  - Edit objective file with ObjectiveAgent coaching
  - View linked ideas in Objective Workspace

---

## Files Created/Modified

### Backend (New)
- `backend/crabgrass/concepts/objective.py`
- `backend/crabgrass/concepts/objective_file.py`
- `backend/crabgrass/concepts/graph.py`
- `backend/crabgrass/concepts/agents/objective_agent.py`
- `backend/crabgrass/api/routes/objectives.py`

### Backend (Modified)
- `backend/crabgrass/db/migrations.py` - Add tables, graph schema
- `backend/crabgrass/ai/prompts.py` - Add objective agent prompts
- `backend/crabgrass/concepts/agents/__init__.py` - Register ObjectiveAgent
- `backend/crabgrass/concepts/context_file.py` - Add objective_id support
- `backend/crabgrass/concepts/session.py` - Add objective_id support
- `backend/crabgrass/sync/synchronizations.py` - Add objective syncs
- `backend/crabgrass/main.py` - Register routes
- `backend/crabgrass/api/routes/ideas.py` - Add link/unlink endpoints

### Frontend (New)
- `frontend/js/concepts/objective-list.js`
- `frontend/js/concepts/objective-workspace.js`

### Frontend (Modified)
- `frontend/js/api/client.js` - Add objective methods
- `frontend/js/concepts/idea-list.js` - Add objectives section
- `frontend/js/concepts/idea-workspace.js` - Enable objective selector
- `frontend/js/concepts/chat.js` - Support objective chats
- `frontend/js/pages/file-editor.js` - Support objective files
- `frontend/js/main.js` - Add objective routes
- `frontend/styles/components.css` - Add objective styles

### Tests (Modified)
- `backend/tests/test_context_file.py` - Fix keyword arguments

---

*Started: 2026-01-03*
*Completed: 2026-01-03*
