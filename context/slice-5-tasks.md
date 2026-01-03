# Slice 5: First Agent (ChallengeAgent) - Tasks

**Goal:** ChallengeAgent coaches in file editor, can mark file complete on save.

**Status:** ✅ Complete

---

## Design Decisions

| Decision | Choice |
|----------|--------|
| Agent model | `gemini-2.0-flash` |
| Response style | Simple REST (not SSE streaming for chat) |
| Auto-evaluate | On file save (triggers agent evaluation) |
| Sessions | Persistent (saved to DB, can resume later) |
| SSE usage | For `completion_changed` events only (not chat streaming) |

---

## Backend Tasks

- [x] 1. Create Gemini client (`ai/gemini.py`)
  - Initialize google-generativeai client
  - Wrapper for `generate_content()` with async support
  - Load API key from config

- [x] 2. Create agent prompts (`ai/prompts.py`)
  - `CHALLENGE_AGENT_SYSTEM_PROMPT`
  - Include role, criteria (Specific, Measurable, Significant), tone

- [x] 3. Create Session concept (`concepts/session.py`)
  - `Session` dataclass
  - `SessionConcept`: `create()`, `get()`, `list()`, `add_message()`, `get_history()`

- [x] 4. Add database schema for sessions
  - `sessions` table
  - `session_messages` table
  - Run migration on startup

- [x] 5. Create ChallengeAgent (`concepts/agents/challenge_agent.py`)
  - `evaluate(idea_id, content)` → EvaluationResult
  - `coach(idea_id, content, user_message, session_id)` → response string
  - Mark file complete when all criteria met

- [x] 6. Create agent API routes (`api/routes/agent.py`)
  - `POST /api/ideas/{id}/kernel/{type}/chat` - Send message, get response
  - `GET /api/ideas/{id}/kernel/{type}/sessions` - List sessions
  - `GET /api/ideas/{id}/sessions/{session_id}` - Get session with messages
  - Request: `{message: string, session_id?: string}`
  - Response: `{response: string, session_id: string, agent_type: string}`

- [x] 7. Create SSE endpoint (`api/sse.py`)
  - `GET /api/ideas/{id}/events` - SSE stream
  - Events: `completion_changed`, `file_saved`

- [x] 8. Update synchronizations
  - `on_kernel_file_updated_async()`: Trigger agent evaluation
  - `on_kernel_file_marked_complete_async()`: Emit SSE event

- [x] 9. Add agent factory (`concepts/agents/__init__.py`)
  - `get_agent_for_file_type(file_type)` → returns appropriate agent
  - `get_agent_by_type(agent_type)` → returns agent by type name

## Frontend Tasks

- [x] 10. Create SSE client (`api/events.js`)
  - EventSource wrapper
  - Connect to idea events stream
  - Emit custom events for SSE event types

- [x] 11. Create Chat concept (`concepts/chat.js`)
  - State: messages, isLoading, sessionId
  - Actions: `send()`, `receive()`, `loadSession()`
  - Render: Message list + input box

- [x] 12. Add API client methods for chat
  - `sendChatMessage(ideaId, fileType, message, sessionId)`
  - `getSessions(ideaId, fileType)`
  - `getSessionWithMessages(ideaId, sessionId)`

- [x] 13. Update File Editor page
  - Replace chat placeholder with Chat component
  - Wire up chat:send → API call
  - Display completion status updates

- [x] 14. Add chat styles to components.css

## Tests

- [x] 15. Add session concept tests (`test_session.py`) - 10 tests
- [x] 16. Add agent API tests (`test_agent_api.py`) - 10 tests
- [ ] 17. Manual testing of chat flow (pending)

---

## Files Created

### Backend (New)
- `backend/crabgrass/ai/gemini.py` - Gemini client wrapper
- `backend/crabgrass/ai/prompts.py` - System prompts
- `backend/crabgrass/concepts/session.py` - Session concept
- `backend/crabgrass/concepts/agents/challenge_agent.py` - ChallengeAgent
- `backend/crabgrass/api/routes/agent.py` - Agent chat endpoints
- `backend/crabgrass/api/sse.py` - SSE event stream

### Frontend (New)
- `frontend/js/api/events.js` - SSE client
- `frontend/js/concepts/chat.js` - Chat component

### Modified
- `backend/crabgrass/db/migrations.py` - Add sessions tables
- `backend/crabgrass/sync/synchronizations.py` - Add agent evaluation
- `backend/crabgrass/concepts/agents/__init__.py` - Agent factory
- `backend/crabgrass/main.py` - Mount agent routes
- `backend/crabgrass/api/routes/ideas.py` - Call async evaluation on save
- `frontend/js/api/client.js` - Add chat methods
- `frontend/js/pages/file-editor.js` - Integrate Chat component
- `frontend/styles/components.css` - Chat styles

### Tests (New)
- `backend/tests/test_session.py` - 10 tests for Session concept
- `backend/tests/test_agent_api.py` - 10 tests for Agent API

---

## ChallengeAgent Completion Criteria

The ChallengeAgent evaluates content against these criteria:
- **Specific**: Not vague or overly broad
- **Measurable**: Can determine if it's solved
- **Significant**: Worth solving

When all three criteria are met, the agent marks the file complete.

---

*Started: 2026-01-02*
*Completed: 2026-01-02*
