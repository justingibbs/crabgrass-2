# Slice 7: CoherenceAgent - Tasks

**Goal:** Idea Workspace has CoherenceAgent chat that checks cross-file consistency and maintains a `feedback-tasks.md` context file.

**Status:** Complete

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Coherence output | `feedback-tasks.md` context file | Persistent, human-readable, other agents can reference it |
| Evaluation trigger | Background on 2+ kernel files complete | Non-blocking, updates file automatically |
| Sessions | Idea-scoped (one coherence session per idea) | Simplifies management, continuous conversation |
| Toast notifications | Deferred | Keep UI simple for MVP |
| Suggest next file | Via `feedback-tasks.md` | No separate endpoint needed |

---

## Backend Tasks

### Database & Context Files

- [x] 1. Add `context_files` table to migrations
  - `id`, `idea_id`, `filename`, `content`, `size_bytes`
  - `created_by` (NULL if agent-created), `created_by_agent` boolean
  - `created_at`, `updated_at`
  - Constraints: valid filename (no spaces, .md extension), max 50KB

- [x] 2. Create ContextFile concept (`concepts/context_file.py`)
  - `ContextFile` dataclass
  - `ContextFileConcept` class with:
    - `create(idea_id, filename, content, user_id=None, created_by_agent=False)`
    - `get(idea_id, filename)` - Get by filename
    - `get_by_id(file_id)` - Get by ID
    - `update(idea_id, filename, content)`
    - `list(idea_id)` - List all context files for an idea
  - Write to JJ repository at `{repo}/context/{filename}`

### CoherenceAgent

- [x] 3. Update prompts in `ai/prompts.py`
  - Enhance `COHERENCE_AGENT_SYSTEM_PROMPT` for coaching conversations
  - Add `COHERENCE_AGENT_EVALUATION_PROMPT` for generating `feedback-tasks.md`
  - Prompt should guide structured output with:
    - Coherence assessment (what's working, what's not)
    - Specific inconsistencies between files
    - Task list for improving the idea
    - Suggested next steps

- [x] 4. Create CoherenceAgent (`concepts/agents/coherence_agent.py`)
  - `AGENT_TYPE = "coherence"`
  - `evaluate(idea_id)` method:
    - Fetch all 4 kernel files
    - Fetch existing `feedback-tasks.md` if present
    - Check coherence across files
    - Generate/update `feedback-tasks.md` content
    - Create or update the context file
    - Return evaluation result
  - `coach(idea_id, user_message, session_id)` method:
    - Fetch all 4 kernel files for context
    - Fetch existing `feedback-tasks.md` for context
    - Get conversation history from session
    - Generate coaching response
  - Helper: `_get_all_kernel_content(idea_id)` - Returns dict of file_type -> content

- [x] 5. Register CoherenceAgent in `concepts/agents/__init__.py`
  - Add to `AGENT_TYPE_TO_AGENT` map

### API Routes

- [x] 6. Create coherence API routes (`api/routes/coherence.py`)
  - `POST /api/ideas/{id}/coherence/chat` - Chat with CoherenceAgent
    - Request: `{message: str, session_id?: str}`
    - Response: `{response: str, session_id: str}`
  - `POST /api/ideas/{id}/coherence/evaluate` - Manually trigger evaluation
    - Response: `{feedback_file_id: str, content: str}`
  - `GET /api/ideas/{id}/context` - List context files (for frontend)
    - Response: `{files: [{id, filename, created_at, created_by_agent}]}`

- [x] 7. Register routes in `main.py`

### Synchronizations

- [x] 8. Update `on_kernel_file_marked_complete_async` in synchronizations.py
  - If `idea.kernel_completion >= 2`, trigger `CoherenceAgent.evaluate(idea_id)` in background
  - Use asyncio to run non-blocking

- [x] 9. JJ integration handled in ContextFile concept (no separate sync needed)

---

## Frontend Tasks

- [x] 10. Update API client (`api/client.js`)
  - Add `sendCoherenceChatMessage(ideaId, message, sessionId)`
  - Add `triggerCoherenceEvaluation(ideaId)`
  - Add `getContextFiles(ideaId)`
  - Add `getCoherenceSessions(ideaId)`

- [x] 11. Update Idea Workspace (`concepts/idea-workspace.js`)
  - Replace chat placeholder with real Chat component
  - Configure Chat for coherence agent (no file_type, agent_type="coherence")
  - Load and display context files in Context Files section
  - Show `feedback-tasks.md` with visual indicator (agent-generated)

- [x] 12. Update Chat component (`concepts/chat.js`)
  - Support coherence agent mode (idea-level, not file-level)
  - Add `agentType` option as alternative to `fileType`
  - Update API calls to use coherence endpoints when agentType="coherence"

---

## Tests

- [x] 13. Create `test_context_file.py`
  - Test create, get, update, list operations
  - Test validation (filename format, size limit)
  - Test JJ integration (files written to repo)

- [x] 14. Create `test_coherence_agent.py`
  - Test evaluate() generates valid feedback-tasks.md
  - Test coach() provides contextual responses
  - Test with various kernel file completion states
  - Test consistency detection (mock inconsistent files)

- [x] 15. Create `test_coherence_api.py`
  - Test chat endpoint
  - Test evaluate endpoint
  - Test context files list endpoint
  - Test authorization (user must have access to idea)

- [ ] 16. Manual testing
  - Create idea with 2+ completed kernel files
  - Verify feedback-tasks.md is created
  - Chat with CoherenceAgent
  - Verify feedback-tasks.md shows in context files

---

## Files to Create

### Backend (New)
- `backend/crabgrass/concepts/context_file.py`
- `backend/crabgrass/concepts/agents/coherence_agent.py`
- `backend/crabgrass/api/routes/coherence.py`

### Backend (Modified)
- `backend/crabgrass/db/migrations.py` - Add context_files table
- `backend/crabgrass/ai/prompts.py` - Add/enhance coherence prompts
- `backend/crabgrass/concepts/agents/__init__.py` - Register CoherenceAgent
- `backend/crabgrass/sync/synchronizations.py` - Add coherence triggers
- `backend/crabgrass/main.py` - Register coherence routes

### Frontend (Modified)
- `frontend/js/api/client.js` - Add coherence endpoints
- `frontend/js/concepts/idea-workspace.js` - Add real chat, context files display
- `frontend/js/concepts/chat.js` - Support coherence mode

### Tests (New)
- `backend/tests/test_context_file.py`
- `backend/tests/test_coherence_agent.py`
- `backend/tests/test_coherence_api.py`

---

## feedback-tasks.md Format

The generated file should follow this structure:

```markdown
# Idea Feedback & Tasks

*Last evaluated: {timestamp}*
*Kernel files complete: {count}/4*

## Coherence Assessment

### What's Working
- [Specific positive observations about how files connect]

### Areas for Improvement
- [Specific inconsistencies or gaps]

## Recommended Tasks

### High Priority
- [ ] [Specific actionable task]
- [ ] [Specific actionable task]

### Next Steps
- [ ] [Suggested next file to work on and why]
- [ ] [Other improvements]

## File-by-File Notes

### Summary.md
[Brief assessment]

### Challenge.md
[Brief assessment]

### Approach.md
[Brief assessment]

### CoherentSteps.md
[Brief assessment]
```

---

*Started: 2026-01-03*
*Completed: TBD*
