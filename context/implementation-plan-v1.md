# Crabgrass: Implementation Plan

**Version:** 1.0.0
**Date:** 2026-01-01
**Approach:** Vertical Slices (feature-complete increments)

---

## Overview

This plan delivers Crabgrass MVP through 10 vertical slices. Each slice produces working, testable functionality. The approach prioritizes end-to-end features over layer-by-layer construction.

### Key Decisions

| Decision | Choice |
|----------|--------|
| Development | Local server (no Docker for MVP) |
| Authentication | Dev User Switcher (Sally/Sam pre-seeded) |
| Version Control | JJ included in MVP |
| AI Framework | Google ADK from day one |
| DuckDB Extensions | VSS + DuckPGQ included, embeddings stored |
| Build Order | Vertical slices |
| Testing | Minimal - verify functionality works |

---

## Slice 1: Project Foundation

**Goal:** Runnable backend and frontend with database, dev user switching, and basic navigation.

### Backend Tasks

1. **Project structure**
   ```
   backend/
   ├── crabgrass/
   │   ├── __init__.py
   │   ├── main.py
   │   ├── config.py
   │   ├── concepts/
   │   ├── sync/
   │   ├── db/
   │   ├── ai/
   │   ├── api/routes/
   │   └── jj/
   ├── tests/
   └── pyproject.toml
   ```

2. **pyproject.toml** with dependencies:
   - fastapi, uvicorn, duckdb, google-adk, google-generativeai
   - pydantic, sse-starlette, httpx, structlog
   - pytest, pytest-asyncio (dev)

3. **DuckDB setup** (`db/connection.py`, `db/migrations.py`)
   - Connection manager with context manager pattern
   - Load VSS and DuckPGQ extensions
   - Initial schema: organizations, users tables
   - Pre-seed org "Acme Corp" with two users:
     - Sally Chen (Frontline Worker, member)
     - Sam White (VP, org_admin)

4. **Config** (`config.py`)
   - Environment variables: DATABASE_PATH, GEMINI_API_KEY, STORAGE_ROOT
   - Settings class with sensible defaults

5. **FastAPI app** (`main.py`)
   - CORS middleware
   - Health check endpoint
   - Mount API routes

6. **Dev auth** (`api/routes/auth.py`)
   - `GET /api/auth/users` - List available dev users
   - `POST /api/auth/switch/{user_id}` - Switch current user (sets cookie/header)
   - `GET /api/auth/me` - Get current user
   - Middleware to inject current user from cookie/header

### Frontend Tasks

1. **Project structure**
   ```
   frontend/
   ├── index.html
   ├── styles/
   │   ├── main.css
   │   └── components.css
   ├── js/
   │   ├── main.js
   │   ├── concepts/
   │   ├── sync/
   │   ├── api/
   │   └── lib/
   └── assets/
   ```

2. **index.html** - Shell with:
   - Header with logo, user switcher dropdown
   - Main content area
   - Basic CSS variables for theming

3. **API client** (`api/client.js`)
   - Fetch wrapper with base URL, error handling
   - Auth header injection

4. **User switcher component**
   - Dropdown showing Sally/Sam
   - On change: call switch endpoint, reload page

5. **Router** (`main.js`)
   - Simple hash-based routing
   - Routes: #/ (home), #/ideas/:id, #/objectives/:id

### Tests

- `test_db_connection.py` - Verify DuckDB connects, extensions load
- `test_auth.py` - Verify user switching works
- Manual: Navigate frontend, switch users

### Deliverable

- `uv run uvicorn crabgrass.main:app --reload` serves backend
- `npx serve frontend` serves frontend
- User switcher functional in header

---

## Slice 2: Ideas List & Creation

**Goal:** Home page shows ideas, can create new ideas with kernel file initialization.

### Backend Tasks

1. **Idea concept** (`concepts/idea.py`)
   - `Idea` dataclass with all fields
   - `IdeaConcept` class with: `create()`, `get()`, `list_for_user()`, `update()`, `archive()`

2. **KernelFile concept** (`concepts/kernel_file.py`)
   - `KernelFile` dataclass
   - `KernelFileConcept` with: `initialize_all()`, `get()`, `update()`, `mark_complete()`, `get_completion_count()`

3. **Database schema** - Add to migrations:
   - `ideas` table
   - `kernel_files` table
   - `objectives` table (stub for now)

4. **Synchronization** (`sync/synchronizations.py`)
   - `on_idea_created()`: Initialize 4 kernel files

5. **API routes** (`api/routes/ideas.py`)
   - `GET /api/ideas` - List user's ideas
   - `POST /api/ideas` - Create idea (title only, no objective yet)
   - `GET /api/ideas/{id}` - Get idea with kernel file metadata

### Frontend Tasks

1. **IdeaList concept** (`concepts/idea-list.js`)
   - State: ideas array, loading state
   - Actions: `load()`, `filter()`
   - Render: Grid of idea cards

2. **Home page** (`pages/home.js`)
   - Two sections: "Contributing To" (owned + contributor), "Shared With Me" (viewer)
   - Each idea card shows: title, kernel progress (●●○○), status, updated time
   - "+ New Idea" card/button

3. **Create idea flow**
   - Click "+ New Idea" → POST to API → navigate to #/ideas/:id

4. **Styling** - Idea cards per wireframe

### Tests

- `test_idea_concept.py` - Create idea, verify 4 kernel files initialized
- `test_ideas_api.py` - CRUD operations
- Manual: Create idea from UI, see it in list

### Deliverable

- Home page shows idea cards
- Create new idea, see it appear in list
- Kernel progress indicator shows 0/4

---

## Slice 3: Idea Workspace & File Viewing

**Goal:** Click idea → see Idea Workspace with kernel files and basic layout.

### Backend Tasks

1. **API routes**
   - `GET /api/ideas/{id}/kernel/{type}` - Get kernel file content
   - Enhance `GET /api/ideas/{id}` to include kernel file summaries

### Frontend Tasks

1. **IdeaWorkspace concept** (`concepts/idea-workspace.js`)
   - State: idea, kernelFiles, contextFiles, currentFile
   - Actions: `load()`, `selectFile()`, `updateTitle()`
   - Render: Header + chat area + file list

2. **Idea Workspace page** (`pages/idea-workspace.js`)
   - Layout per wireframe:
     - Header: Title (editable), kernel progress, objective (placeholder), share button (placeholder)
     - CoherenceAgent chat area (placeholder for now)
     - Kernel files grid (4 cards with completion status)
     - Context files section (empty for now)

3. **FileList concept** (`concepts/file-list.js`)
   - Render kernel file cards with ○/● completion indicator
   - Click handler to open file editor

4. **KernelStatus concept** (`concepts/kernel-status.js`)
   - Render ●●○○ progress indicator

5. **Routing**
   - #/ideas/:id → Idea Workspace page

### Tests

- Manual: Click idea → see workspace with 4 kernel file cards
- Manual: Title displays correctly

### Deliverable

- Clicking idea card navigates to workspace
- Workspace shows idea header and 4 kernel file cards
- Back navigation to home works

---

## Slice 4: File Editor with Canvas

**Goal:** Click kernel file → 50/50 editor with canvas (no agent chat yet).

### Backend Tasks

1. **JJ integration** (`jj/repository.py`)
   - `JJRepository` class
   - `initialize(idea_id)` - Create repo at `{STORAGE_ROOT}/ideas/{idea_id}/`
   - `commit(idea_id, message)` - Commit current state
   - `history(idea_id, file_path)` - Get commit log
   - Shell out to `jj` CLI (ensure jj is in PATH)

2. **Version concept** (`concepts/version.py`)
   - Wrapper around JJRepository
   - `initialize()`, `commit()`, `history()`, `restore()`

3. **Update synchronizations**
   - `on_idea_created()`: Also call `Version.initialize(idea_id)`
   - `on_kernel_file_updated()`: Call `Version.commit()`

4. **API routes**
   - `PUT /api/ideas/{id}/kernel/{type}` - Update kernel file content
   - `GET /api/ideas/{id}/kernel/{type}/history` - Get version history

5. **File system sync**
   - On kernel file update: write to `{repo}/kernel/{Type}.md`
   - JJ tracks the file automatically

### Frontend Tasks

1. **Canvas concept** (`concepts/canvas.js`)
   - State: content, isDirty, isEditing
   - Actions: `load()`, `edit()`, `save()`, `updateContent()`
   - Render: Textarea (edit mode) or rendered markdown (preview)
   - Emit `canvas:save` event on save

2. **File Editor page** (`pages/file-editor.js`)
   - 50/50 split layout
   - Left: Chat panel (placeholder "Agent chat coming soon")
   - Right: Canvas with content
   - Header: File name, completion status, History button (placeholder)
   - Footer: Cancel, Save & Close buttons

3. **Markdown rendering** (`lib/markdown.js`)
   - Use marked.js or similar (CDN import)
   - Basic styling for rendered markdown

4. **Synchronizations** (`sync/synchronizations.js`)
   - Listen for `canvas:save` → call API to update file

5. **Routing**
   - #/ideas/:id/kernel/:type → File Editor

### Tests

- `test_version_concept.py` - JJ init, commit, history
- `test_kernel_file_api.py` - Update file, verify persisted
- Manual: Edit file, save, reload page, content persists

### Deliverable

- Click kernel file → opens editor
- Edit markdown, save, content persists
- Navigate back to workspace, file shows updated

---

## Slice 5: First Agent (ChallengeAgent)

**Goal:** ChallengeAgent coaches in file editor, can mark file complete.

### Backend Tasks

1. **Gemini client** (`ai/gemini.py`)
   - Initialize google-generativeai client
   - Wrapper for `generate_content()` with async support

2. **Agent prompts** (`ai/prompts.py`)
   - `CHALLENGE_AGENT_SYSTEM_PROMPT` - Includes:
     - Role: Coach for Challenge.md
     - Criteria: Specific, Measurable, Significant
     - Tone: Socratic, encouraging
     - Output format for evaluation

3. **ChallengeAgent** (`concepts/agents/challenge_agent.py`)
   - `evaluate(idea_id, content)` → EvaluationResult
   - `coach(idea_id, content, user_message)` → response string
   - Uses structured output for evaluation (JSON)

4. **Session concept** (`concepts/session.py`)
   - `Session` dataclass
   - `SessionConcept`: `create()`, `get()`, `list()`, `add_message()`, `get_history()`

5. **Database schema**
   - `sessions` table
   - `session_messages` table

6. **API routes** (`api/routes/agent.py`)
   - `POST /api/ideas/{id}/kernel/{type}/chat` - Send message, get response
     - Request: `{message: string, session_id?: string}`
     - Response: `{response: string, session_id: string, is_complete: bool}`

7. **SSE setup** (`api/sse.py`)
   - `GET /api/ideas/{id}/events` - SSE stream
   - Events: `agent_message`, `completion_changed`

8. **Synchronizations**
   - `on_kernel_file_updated()`: Trigger agent evaluation
   - `on_kernel_marked_complete()`: Emit SSE event

### Frontend Tasks

1. **Chat concept** (`concepts/chat.js`)
   - State: messages, isStreaming, pendingMessage, sessionId
   - Actions: `send()`, `receive()`, `loadSession()`
   - Render: Message list + input box
   - Emit `chat:send` event

2. **SSE client** (`api/events.js`)
   - EventSource wrapper
   - Connect to idea events stream
   - Emit custom events for each SSE event type

3. **Update File Editor**
   - Left panel: Chat component (functional now)
   - Wire up chat:send → API call
   - Display agent responses
   - Show completion status update when agent marks complete

4. **Synchronizations**
   - `chat:send` → POST to agent chat endpoint
   - SSE `completion_changed` → update KernelStatus

### Tests

- `test_challenge_agent.py` - Mock Gemini, verify evaluation logic
- `test_session_concept.py` - Create session, add messages
- `test_agent_api.py` - Send message, get response
- Manual: Chat with ChallengeAgent, see responses

### Deliverable

- Open Challenge.md editor, chat with agent
- Agent provides coaching feedback
- When criteria met, agent marks file complete
- ● indicator updates

---

## Slice 6: Remaining Kernel Agents

**Goal:** All 4 kernel file agents functional.

### Backend Tasks

1. **Agent prompts** - Add to `ai/prompts.py`:
   - `SUMMARY_AGENT_SYSTEM_PROMPT` (Clear, Concise, Compelling)
   - `APPROACH_AGENT_SYSTEM_PROMPT` (Feasible, Differentiated, Addresses Challenge)
   - `STEPS_AGENT_SYSTEM_PROMPT` (Concrete, Sequenced, Assignable)

2. **SummaryAgent** (`concepts/agents/summary_agent.py`)
   - Same pattern as ChallengeAgent
   - Different criteria

3. **ApproachAgent** (`concepts/agents/approach_agent.py`)
   - Same pattern
   - Needs to reference Challenge.md content for "Addresses Challenge" criterion

4. **StepsAgent** (`concepts/agents/steps_agent.py`)
   - Same pattern
   - Needs to reference Approach.md for coherence

5. **Agent factory** (`concepts/agents/__init__.py`)
   - `get_agent_for_file_type(file_type)` → returns appropriate agent

6. **Update API**
   - Agent chat endpoint now routes to correct agent based on file type

### Frontend Tasks

1. **Update File Editor**
   - Show correct agent name in chat header based on file type
   - Same chat UI works for all agents

### Tests

- `test_summary_agent.py`, `test_approach_agent.py`, `test_steps_agent.py`
- Manual: Edit each kernel file, chat with respective agent

### Deliverable

- All 4 kernel files have working agent chat
- Each agent evaluates against its specific criteria
- Agents can mark their respective files complete

---

## Slice 7: CoherenceAgent

**Goal:** Idea Workspace has CoherenceAgent chat that checks cross-file consistency and maintains a `feedback-tasks.md` context file.

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Coherence output | `feedback-tasks.md` context file | Persistent, human-readable, other agents can reference it |
| Evaluation trigger | Background on 2+ kernel files complete | Non-blocking, updates file automatically |
| Sessions | Idea-scoped (one coherence session per idea) | Simplifies management, continuous conversation |
| Toast notifications | Deferred | Keep UI simple for MVP |
| Suggest next file | Via `feedback-tasks.md` | No separate endpoint needed |

### Backend Tasks

1. **Minimal ContextFile concept** (`concepts/context_file.py`)
   - `ContextFile` dataclass
   - `ContextFileConcept`: `create()`, `get()`, `update()`, `list()`
   - Note: Delete and full API routes deferred to Slice 8
   - Validation: .md extension, no spaces, max 50KB

2. **Database schema**
   - `context_files` table (pulled forward from Slice 8)

3. **CoherenceAgent** (`concepts/agents/coherence_agent.py`)
   - `evaluate(idea_id)` - Check all kernel files, create/update `feedback-tasks.md`
   - `coach(idea_id, user_message, session_id)` - Guide overall idea development
   - Reads existing `feedback-tasks.md` for context
   - Checks:
     - Does Approach address Challenge?
     - Are Steps implementing Approach?
     - Does Summary capture essence?
     - Will completing Steps solve the Challenge?
   - Outputs structured feedback with actionable tasks

4. **Agent prompts**
   - Enhanced `COHERENCE_AGENT_SYSTEM_PROMPT`
   - `COHERENCE_AGENT_EVALUATION_PROMPT` - For generating `feedback-tasks.md`
   - Include all 4 kernel file contents + existing `feedback-tasks.md` in context

5. **API routes** (`api/routes/coherence.py`)
   - `POST /api/ideas/{id}/coherence/chat` - Chat with CoherenceAgent
   - `POST /api/ideas/{id}/coherence/evaluate` - Manually trigger evaluation (creates/updates feedback-tasks.md)

6. **Synchronizations**
   - `on_kernel_marked_complete()`: If 2+ complete, trigger CoherenceAgent.evaluate() in background

### Frontend Tasks

1. **Update Idea Workspace**
   - CoherenceAgent chat section now functional (replace placeholder)
   - Shows `feedback-tasks.md` in context files section
   - Sessions dropdown for conversation history

2. **Update API client**
   - Add coherence chat and evaluate endpoints
   - Add context file list endpoint

### Tests

- `test_context_file.py` - CRUD operations for context files
- `test_coherence_agent.py` - Evaluation generates valid feedback-tasks.md
- `test_coherence_api.py` - Chat and evaluate endpoints
- Manual: Complete 2 kernel files, see feedback-tasks.md created

### Deliverable

- Idea Workspace chat works with CoherenceAgent
- `feedback-tasks.md` automatically created/updated when 2+ kernel files complete
- Agent provides coherence feedback and task suggestions via the file
- Other agents can reference `feedback-tasks.md` for context

---

## Slice 8: Context Files

**Goal:** Complete context file functionality with user-facing CRUD and ContextAgent insights.

**Note:** Minimal ContextFile concept and `context_files` table were implemented in Slice 7 to support `feedback-tasks.md`.

### Backend Tasks

1. **Complete ContextFile concept** (`concepts/context_file.py`)
   - Add `delete()` method
   - Add full validation and error handling

3. **ContextAgent** (`concepts/agents/context_agent.py`)
   - `extract(idea_id, content)` - Find insights relevant to kernel files
   - `summarize(content)` - Generate summary
   - `map_to_kernel(insight)` - Which kernel file does this relate to?

4. **API routes** (`api/routes/files.py`)
   - `GET /api/ideas/{id}/context` - List context files
   - `POST /api/ideas/{id}/context` - Create (filename, content)
   - `GET /api/ideas/{id}/context/{file_id}` - Get content
   - `PUT /api/ideas/{id}/context/{file_id}` - Update
   - `DELETE /api/ideas/{id}/context/{file_id}` - Delete

5. **Synchronizations**
   - `on_context_file_created()`: Trigger ContextAgent extraction

### Frontend Tasks

1. **Update Idea Workspace**
   - Context files section shows file cards
   - "+ New File" button → modal for filename
   - Click file → opens File Editor (with ContextAgent)

2. **Update File Editor**
   - Context files show ContextAgent in chat
   - Delete button in footer (not for kernel files)

3. **Context file creation modal**
   - Input for filename (auto-adds .md)
   - Validation feedback

### Tests

- `test_context_file_concept.py` - CRUD operations
- `test_context_agent.py` - Insight extraction
- Manual: Create context file, see agent suggestions

### Deliverable

- Create/edit/delete context files
- ContextAgent analyzes and suggests connections to kernel files
- Files persist in JJ repository

---

## Slice 9: Objectives

**Goal:** Objectives CRUD, ObjectiveAgent, link ideas to objectives.

### Backend Tasks

1. **Objective concept** (`concepts/objective.py`)
   - `Objective` dataclass
   - `ObjectiveConcept`: `create()`, `get()`, `list()`, `update()`, `archive()`, `get_ideas()`

2. **Database schema**
   - Update `objectives` table (already stubbed)
   - Pre-seed 3-4 objectives for demo

3. **ObjectiveAgent** (`concepts/agents/objective_agent.py`)
   - `coach(objective_id, content, message)` - Help define objective
   - `summarize_alignment(objective_id)` - How do linked ideas support this?

4. **Graph concept** (`concepts/graph.py`)
   - DuckPGQ wrapper
   - `connect(from_id, to_id, relationship)` - Create edge
   - `get_connected(node_id, relationship)` - Query edges

5. **API routes** (`api/routes/objectives.py`)
   - `GET /api/objectives` - List org objectives
   - `POST /api/objectives` - Create (admin only)
   - `GET /api/objectives/{id}` - Get with linked ideas
   - `PATCH /api/objectives/{id}` - Update (admin only)
   - `POST /api/ideas/{id}/objective` - Link idea to objective

6. **Synchronizations**
   - `on_idea_linked_to_objective()`: Create graph edge

### Frontend Tasks

1. **Update Home page**
   - Objectives section at bottom
   - Objective cards show: title, timeframe, owner, linked idea count

2. **Objective selector** (modal/dropdown)
   - Search/filter objectives
   - Select to link to current idea
   - Triggered from Idea Workspace header

3. **ObjectiveWorkspace page** (`pages/objective-workspace.js`)
   - Similar layout to Idea Workspace
   - ObjectiveAgent chat
   - Single Objective.md file
   - Context files section
   - Linked ideas list

4. **Objective File Editor**
   - Same pattern as kernel files
   - ObjectiveAgent in chat

5. **Routing**
   - #/objectives/:id → Objective Workspace

### Tests

- `test_objective_concept.py` - CRUD operations
- `test_graph_concept.py` - Edge creation and queries
- Manual: Create objective (as Sam), link idea to it

### Deliverable

- Objectives appear on home page
- Link ideas to objectives
- Objective workspace with ObjectiveAgent
- Graph relationships created

---

## Slice 10: Sessions, Embeddings & Polish

**Goal:** Session management, embeddings for all kernel files, UI polish, demo data.

### Backend Tasks

1. **Session management**
   - Sessions dropdown shows history
   - Can create new session, switch between sessions
   - Session titles auto-generated or editable

2. **Embedding concept** (`concepts/embedding.py`)
   - `generate(content)` → float[768] vector
   - Uses Gemini embedding model

3. **Vector storage**
   - `kernel_embeddings` table with VSS index
   - Store embedding on every kernel file save

4. **Update synchronizations**
   - `on_kernel_file_updated()`: Generate and store embedding

5. **Version history API**
   - `GET /api/ideas/{id}/kernel/{type}/history` - Returns commit list
   - `POST /api/ideas/{id}/kernel/{type}/restore/{commit_id}` - Restore version

6. **Demo data seeding**
   - 2-3 ideas at various completion stages
   - Sample context files
   - Conversation history

### Frontend Tasks

1. **Sessions dropdown**
   - List previous sessions
   - "+ New Session" option
   - Switch loads conversation history

2. **Version history modal**
   - List versions with timestamps
   - "Restore" button per version

3. **UI Polish**
   - Loading states
   - Error handling and display
   - Empty states
   - Responsive layout adjustments
   - Keyboard shortcuts (Cmd+S to save)

4. **Home page enhancements**
   - Search/filter (client-side for MVP)
   - Sort by updated date

### Tests

- `test_embedding_concept.py` - Vector generation
- `test_session_management.py` - Switch sessions, load history
- End-to-end walkthrough as both users

### Deliverable

- Complete MVP functionality
- Demo-ready with sample data
- All agents functional
- Sessions persist across page loads

---

## Slice 11: WYSIWYG Canvas & AST Foundation

**Goal:** Upgrade textarea editor to WYSIWYG with AST-based markdown handling.

**Note:** This is a post-MVP enhancement. MVP (Slices 1-10) uses simple textarea + preview.

### Backend Tasks

1. **No backend changes required**
   - File storage and JJ integration unchanged
   - API endpoints remain the same

### Frontend Tasks

1. **WYSIWYG editor integration** (`lib/editor.js`)
   - Evaluate and integrate Vanilla JS editor (options below)
   - Options: Quill.js, Editor.js, or ProseMirror (direct, no React wrapper)
   - Must support: bold, italic, headings, lists, blockquotes, links, inline code
   - Markdown shortcuts (e.g., `# ` for heading, `- ` for list)

2. **AST parsing layer** (`lib/markdown-ast.js`)
   - Integrate unified/remark ecosystem (works without React)
   - `parseMarkdown(string)` → mdast (Markdown AST)
   - `serializeAst(mdast)` → markdown string
   - Position tracking for each node (line/column offsets)

3. **Editor ↔ AST sync** (`concepts/canvas.js` upgrade)
   - Editor content changes → re-parse to AST
   - AST modifications → update editor content
   - Maintain cursor position across syncs

4. **Upgrade Canvas concept**
   - Replace textarea with WYSIWYG editor
   - State additions: `ast: MdastRoot`, `editorInstance`
   - Bidirectional sync between editor and AST

5. **Formatting toolbar** (`components/canvas-toolbar.js`)
   - Buttons: Bold, Italic, H1-H3, Bullet List, Numbered List, Quote, Code, Link
   - Keyboard shortcuts (Cmd+B, Cmd+I, etc.)
   - Toolbar state reflects current selection formatting

### Tests

- Manual: Edit with WYSIWYG, verify markdown output matches
- Manual: Markdown shortcuts work (type `## ` → becomes H2)
- Manual: Formatting toolbar applies styles correctly
- Unit: AST parse → serialize roundtrip preserves content

### Deliverable

- WYSIWYG editing replaces textarea
- Formatting toolbar functional
- AST representation available for agent integration
- Markdown serialization preserves formatting

---

## Slice 12: Canvas-Agent Integration & Selection Actions

**Goal:** Agents can make targeted edits to canvas; users can select text and request AI actions.

### Backend Tasks

1. **ag-ui canvas events** (`api/events.py` extension)
   - New SSE event types:
     - `agent_edit` - Agent's targeted edit to canvas
     - `agent_edit_stream_start/chunk/end` - Streaming edits
   - Event payload includes: `file_path`, `operation`, `range`, `content`

2. **Agent edit capability** (update all agents)
   - Agents can emit `agent_edit` events (not just chat responses)
   - Edit operations: `insert`, `replace`, `delete`
   - Range specified as character offsets

3. **Selection action endpoint** (`api/routes/agent.py`)
   - `POST /api/ideas/{id}/kernel/{type}/selection-action`
   - Request: `{selection: {start, end, text}, instruction: string}`
   - Agent receives selection context, returns targeted edit

### Frontend Tasks

1. **Selection popup** (`components/selection-popup.js`)
   - Appears when user selects text in canvas
   - Text input for instruction (e.g., "make this more urgent")
   - Submit sends to selection action endpoint
   - Positioned near selection

2. **ag-ui event handling** (`concepts/canvas.js` extension)
   - Listen for `agent_edit` SSE events
   - Apply edits to AST at specified range
   - Sync AST changes to editor
   - Visual indicator when agent is editing

3. **Streaming edit support**
   - Handle `agent_edit_stream_*` events
   - Show typing indicator in canvas during stream
   - Buffer chunks, apply on stream end

4. **User edit events** (`sync/synchronizations.js`)
   - Emit `user_edit` events when user modifies canvas
   - Debounce to avoid flooding (e.g., 500ms after typing stops)
   - Agent receives user edits for context

5. **Conflict handling (simple)**
   - Last-write-wins strategy
   - If user and agent edit simultaneously, later edit applies
   - Visual flash/highlight when agent edit arrives

### Tests

- `test_selection_action.py` - Selection context passed to agent correctly
- `test_agent_edit_events.py` - Edit events emitted with correct format
- Manual: Select text → "Ask AI" → agent edits selection
- Manual: Agent suggests edit in chat → appears in canvas
- Manual: Simultaneous edits don't crash (last wins)

### Deliverable

- Select text in canvas, type instruction, agent edits selection
- Agents can push edits directly to canvas (not just chat suggestions)
- User and agent edits flow bidirectionally via ag-ui
- Streaming agent edits show live in canvas

---

## Dependency Installation

### System Dependencies

```bash
# JJ (Jujutsu) - version control
# macOS
brew install jj

# Or from source
cargo install --locked --bin jj jj-cli
```

### Python Setup

```bash
cd backend
uv venv
uv pip install -e ".[dev]"
```

### Environment Variables

```bash
# .env file
DATABASE_PATH=./data/crabgrass.duckdb
STORAGE_ROOT=./data/ideas
GEMINI_API_KEY=your-api-key-here
```

### Frontend

```bash
cd frontend
# No build step - just serve
npx serve .
```

---

## Running the Application

```bash
# Terminal 1: Backend
cd backend
uv run uvicorn crabgrass.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npx serve . -l 3000
```

Access at http://localhost:3000

---

## Slice Estimates

| Slice | Description | Complexity | Phase |
|-------|-------------|------------|-------|
| 1 | Project Foundation | Medium | MVP |
| 2 | Ideas List & Creation | Medium | MVP |
| 3 | Idea Workspace & File Viewing | Low | MVP |
| 4 | File Editor with Canvas | Medium | MVP |
| 5 | First Agent (ChallengeAgent) | High | MVP |
| 6 | Remaining Kernel Agents | Medium | MVP |
| 7 | CoherenceAgent | Medium | MVP |
| 8 | Context Files | Medium | MVP |
| 9 | Objectives | Medium | MVP |
| 10 | Sessions, Embeddings & Polish | Medium | MVP |
| 11 | WYSIWYG Canvas & AST Foundation | Medium | Post-MVP |
| 12 | Canvas-Agent Integration & Selection Actions | High | Post-MVP |

---

## Risk Areas

| Risk | Mitigation |
|------|------------|
| **JJ integration complexity** | Shell out to CLI, keep operations simple |
| **Google ADK learning curve** | Start with basic GenAI SDK patterns, ADK adds structure |
| **DuckDB extensions stability** | Test early in Slice 1, have fallback plan |
| **SSE connection management** | Use proven sse-starlette library |
| **Agent prompt engineering** | Iterate on prompts, structured output helps |
| **WYSIWYG editor selection** (Slice 11) | Evaluate Quill.js, Editor.js, ProseMirror early; all are proven Vanilla JS options |
| **AST ↔ Editor sync complexity** (Slice 11-12) | Start simple, defer OT/CRDT to future; last-write-wins acceptable |

---

## Success Criteria

MVP is complete when:

- [ ] Two users can switch between accounts
- [ ] Ideas can be created and listed
- [ ] All 4 kernel files can be edited with agent coaching
- [ ] Agents can mark kernel files complete
- [ ] CoherenceAgent checks cross-file consistency
- [ ] Context files can be added with ContextAgent insights
- [ ] Objectives exist and ideas can be linked to them
- [ ] Sessions persist conversation history
- [ ] Kernel file embeddings are stored
- [ ] Version history is viewable via JJ
- [ ] Demo walkthrough is smooth

---

*Document version: 1.1.0*
*Last updated: 2026-01-02*
