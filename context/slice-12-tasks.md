# Slice 12: Canvas-Agent Integration & Selection Actions

**Status:** In Progress
**Started:** 2026-01-04

## Decisions

| Decision | Choice | Notes |
|----------|--------|-------|
| Selection Popup | Minimal (A), design for presets (B) | Text input only for MVP, architecture supports preset buttons |
| Range Format | Markdown-based offsets | Agents work with markdown positions; convert when applying to Quill |
| Agent Edit Autonomy | Full (C) | Agents can push edits during normal conversation |
| Visual Feedback | Working indicator + highlight | Localized "working" state during streaming; brief highlight on completion |
| Scope | All file editors | Kernel, context, and objective files |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
├─────────────────────────────────────────────────────────────────┤
│  Canvas                                                          │
│  ├── Selection Popup (user selects → asks AI)                   │
│  ├── Agent Edit Handler (SSE → apply to editor)                 │
│  ├── Working Indicator (localized spinner during edit)          │
│  └── Change Highlight (brief flash on completion)               │
│                                                                  │
│  SSE Client                                                      │
│  └── New events: agent_edit, agent_edit_stream_*                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ SSE / REST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Backend                                  │
├─────────────────────────────────────────────────────────────────┤
│  API Routes                                                      │
│  ├── POST /api/ideas/{id}/kernel/{type}/selection-action        │
│  ├── POST /api/ideas/{id}/context/{file_id}/selection-action    │
│  └── POST /api/objectives/{id}/selection-action                 │
│                                                                  │
│  SSE Events                                                      │
│  ├── agent_edit (single edit operation)                         │
│  ├── agent_edit_stream_start (begin streaming edit)             │
│  ├── agent_edit_stream_chunk (content chunk)                    │
│  └── agent_edit_stream_end (streaming complete)                 │
│                                                                  │
│  Agents                                                          │
│  └── All agents gain emit_edit() capability                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Task Breakdown

### Phase 1: Backend - SSE Events & Data Models

#### 1.1 Define Edit Event Models
- [ ] Create `AgentEdit` dataclass in `api/sse.py`
  - `file_path`: str (e.g., "kernel/challenge" or "context/{id}")
  - `operation`: Literal["insert", "replace", "delete"]
  - `range`: tuple[int, int] | None (start, end in markdown chars)
  - `content`: str (new content for insert/replace)
  - `edit_id`: str (unique ID for tracking)

#### 1.2 Add SSE Emit Functions
- [ ] `emit_agent_edit()` - Single complete edit
- [ ] `emit_agent_edit_stream_start()` - Begin streaming
- [ ] `emit_agent_edit_stream_chunk()` - Content chunk
- [ ] `emit_agent_edit_stream_end()` - End streaming

#### 1.3 Update SSE Event Stream
- [ ] Register new event types in `idea_events()` endpoint
- [ ] Add similar events for objectives (`/api/objectives/{id}/events`)

---

### Phase 2: Backend - Selection Action Endpoint

#### 2.1 Create Selection Action Models
- [ ] `SelectionRequest` Pydantic model
  - `selection`: { start: int, end: int, text: str }
  - `instruction`: str
  - `session_id`: Optional[str]

- [ ] `SelectionResponse` Pydantic model
  - `edit_id`: str
  - `session_id`: str

#### 2.2 Implement Selection Action Routes
- [ ] `POST /api/ideas/{id}/kernel/{type}/selection-action`
- [ ] `POST /api/ideas/{id}/context/{file_id}/selection-action`
- [ ] `POST /api/objectives/{id}/selection-action`
- [ ] `POST /api/objectives/{id}/context/{file_id}/selection-action`

#### 2.3 Agent Selection Handler
- [ ] Add `handle_selection_action()` method to base agent pattern
- [ ] Agent receives: full content, selection range, selection text, instruction
- [ ] Agent returns: edit operation (insert/replace/delete) + new content
- [ ] Emit SSE event with result

---

### Phase 3: Backend - Agent Edit Capability

#### 3.1 Agent Edit Emission
- [ ] Create `AgentEditEmitter` helper class
- [ ] Add `emit_edit()` method available to all agents
- [ ] Support both immediate and streaming edits

#### 3.2 Update Agent Coach Methods
- [ ] Modify agent response format to optionally include edits
- [ ] Agents can suggest edits alongside chat responses
- [ ] Parse agent output for edit instructions

#### 3.3 Prompt Updates
- [ ] Add edit instruction format to agent system prompts
- [ ] Define when agents should suggest edits vs just respond
- [ ] Include markdown range calculation guidance

---

### Phase 4: Frontend - SSE Event Handling

#### 4.1 Update SSE Client
- [ ] Add listeners for `agent_edit` event
- [ ] Add listeners for `agent_edit_stream_*` events
- [ ] Emit custom DOM events for canvas to consume

#### 4.2 Edit Application Logic
- [ ] Create `applyAgentEdit()` function in canvas
- [ ] Convert markdown ranges to Quill positions
- [ ] Handle insert, replace, delete operations
- [ ] Preserve cursor position when possible

#### 4.3 Streaming Edit Buffer
- [ ] Buffer streaming chunks
- [ ] Apply complete edit on stream end
- [ ] Handle stream cancellation/error

---

### Phase 5: Frontend - Selection Popup

#### 5.1 Selection Detection
- [ ] Listen for `selectionchange` events in canvas
- [ ] Detect non-empty text selections
- [ ] Calculate popup position near selection

#### 5.2 Selection Popup Component
- [ ] Create `SelectionPopup` class
- [ ] Floating UI positioned near selection
- [ ] Text input for instruction
- [ ] Submit button (or Enter key)
- [ ] Dismiss on click outside or Escape

#### 5.3 Selection Action Integration
- [ ] On submit: call selection-action API
- [ ] Show "working" state in popup while waiting
- [ ] Close popup on success
- [ ] Show error state on failure

---

### Phase 6: Frontend - Visual Feedback

#### 6.1 Working Indicator
- [ ] Create `EditWorkingIndicator` component
- [ ] Localized overlay/spinner at edit region
- [ ] Show during streaming or pending edit
- [ ] CSS animation for subtle pulse/spinner

#### 6.2 Change Highlight
- [ ] Highlight changed region on edit completion
- [ ] Brief fade animation (e.g., yellow background → transparent)
- [ ] Duration: ~1 second

#### 6.3 Integrate with Canvas
- [ ] Show working indicator when edit starts
- [ ] Apply edit content
- [ ] Transition to highlight
- [ ] Clean up highlight after animation

---

### Phase 7: Frontend - User Edit Events (Deferred Context)

#### 7.1 Debounced Edit Emission
- [ ] Track user edits to canvas
- [ ] Debounce (500ms after typing stops)
- [ ] Emit `user_edit` event via synchronizations

#### 7.2 Agent Context Integration
- [ ] Optionally send user edits to agent for context
- [ ] API endpoint to receive user edit notifications
- [ ] Agents can reference recent user changes

*Note: This phase is lower priority - agents work fine without it for MVP*

---

### Phase 8: Testing & Polish

#### 8.1 Backend Tests
- [ ] `test_selection_action.py` - Selection context passed correctly
- [ ] `test_agent_edit_events.py` - Edit events emit correct format
- [ ] Test all file types (kernel, context, objective)

#### 8.2 Manual Testing
- [ ] Select text → popup appears → submit instruction → edit applied
- [ ] Agent suggests edit in chat → appears in canvas
- [ ] Working indicator shows during edit
- [ ] Change highlight on completion
- [ ] Rapid edits don't cause conflicts (last wins)

#### 8.3 Edge Cases
- [ ] Empty selection (should not show popup)
- [ ] Selection across formatting boundaries
- [ ] Edit while user is typing
- [ ] Network error during streaming edit
- [ ] Very large edits

---

## File Changes Summary

### Backend (New/Modified)

| File | Action | Purpose |
|------|--------|---------|
| `api/sse.py` | Modified | Add agent_edit event types and emit functions |
| `api/routes/agent.py` | Modified | Add selection-action endpoint for kernel files |
| `api/routes/files.py` | Modified | Add selection-action endpoint for context files |
| `api/routes/objectives.py` | Modified | Add selection-action endpoints for objective files |
| `concepts/agents/base_edit.py` | New | Agent edit capability mixin |
| `ai/prompts.py` | Modified | Add edit instruction format to prompts |

### Frontend (New/Modified)

| File | Action | Purpose |
|------|--------|---------|
| `js/api/events.js` | Modified | Add agent_edit event listeners |
| `js/concepts/canvas.js` | Modified | Add edit application, working indicator, highlight |
| `js/components/selection-popup.js` | New | Selection popup UI |
| `js/components/edit-indicator.js` | New | Working indicator and change highlight |
| `js/lib/range-converter.js` | New | Markdown ↔ Quill position conversion |
| `styles/canvas.css` | Modified | Add selection popup and indicator styles |

---

## API Contracts

### Selection Action Request
```json
POST /api/ideas/{id}/kernel/{type}/selection-action
{
  "selection": {
    "start": 45,
    "end": 78,
    "text": "the selected text"
  },
  "instruction": "make this more specific",
  "session_id": "optional-existing-session"
}
```

### Selection Action Response
```json
{
  "edit_id": "edit-uuid",
  "session_id": "session-uuid"
}
```

### Agent Edit SSE Event
```json
event: agent_edit
data: {
  "edit_id": "edit-uuid",
  "file_path": "kernel/challenge",
  "operation": "replace",
  "range": [45, 78],
  "content": "a more specific description of the problem"
}
```

### Streaming Edit Events
```json
event: agent_edit_stream_start
data: { "edit_id": "edit-uuid", "file_path": "kernel/challenge", "operation": "replace", "range": [45, 78] }

event: agent_edit_stream_chunk
data: { "edit_id": "edit-uuid", "content": "a more " }

event: agent_edit_stream_chunk
data: { "edit_id": "edit-uuid", "content": "specific description" }

event: agent_edit_stream_end
data: { "edit_id": "edit-uuid", "final_content": "a more specific description of the problem" }
```

---

## Notes

- **Last-write-wins**: No complex conflict resolution. If user and agent edit simultaneously, later edit wins.
- **Markdown ranges**: All ranges are in markdown character positions, converted to Quill positions on frontend.
- **Session continuity**: Selection actions use existing session or create new one, maintaining conversation context.
- **Agent autonomy**: Agents can emit edits during normal chat (option C), not just via selection action.

---

*Created: 2026-01-04*
