# Canvas Feature Specification

**Version:** 0.2.0
**Date:** 2026-01-02
**Status:** Draft
**Parent:** crabgrass-spec.md
**Implementation:** Slices 4, 11, 12 (see implementation-plan-v1.md)

---

## 1. Overview

The Canvas is the markdown editor for all files (Kernel Files and Context Files) within an Idea. It evolves across three implementation slices:

| Slice | Capability | Phase |
|-------|------------|-------|
| **4** | Textarea + markdown preview, Save/Cancel | MVP |
| **11** | WYSIWYG editor, AST parsing, formatting toolbar | Post-MVP |
| **12** | Selection + AI popup, agent edits canvas, ag-ui sync | Post-MVP |

**Core Principle:** The Canvas and Chat are equal participants. User edits flow to the agent, agent edits flow to the Canvas—both sides have full visibility via ag-ui protocol.

**Tech Constraint:** Vanilla JS only (no React, no build step). See Section 3.4 for editor options.

---

## 2. User Experience

### 2.1 Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Back to Idea                               Challenge.md          │
├────────────────────────────────┬────────────────────────────────────┤
│                                │                                    │
│         CHAT PANEL             │           CANVAS PANEL             │
│                                │                                    │
│  Agent messages appear here    │   WYSIWYG editor with markdown     │
│  User can type messages        │   file loaded                      │
│                                │                                    │
│  [Agent]: "Your challenge      │   ## The Problem                   │
│   could be more specific..."   │                                    │
│                                │   Our customers struggle with...   │
│  [User]: "Make it focus on     │                                    │
│   enterprise customers"        │   ### Key Pain Points              │
│                                │                                    │
│  [Agent]: "Done. I've updated  │   - Long onboarding cycles         │
│   the challenge to target..."  │   - Scattered documentation        │
│                                │                                    │
│                                │                                    │
├────────────────────────────────┴────────────────────────────────────┤
│  [Cancel]                                                   [Save]  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Editing Modes

| Mode | Description | Slice |
|------|-------------|-------|
| **Direct Edit** | User types directly in Canvas (textarea → WYSIWYG) | 4 → 11 |
| **Chat Edit** | User asks agent via Chat; agent suggests changes (→ edits Canvas) | 5 → 12 |
| **Selection Edit** | User highlights text, types instruction in popup | 12 |

### 2.3 User Flow

1. User opens a file (e.g., `Challenge.md`) from the Idea workspace
2. Canvas loads the file content in WYSIWYG mode
3. User can:
   - Edit directly in Canvas
   - Chat with the agent to request changes
   - Highlight text and request targeted edits
4. All edits (user or agent) are visible immediately in Canvas
5. User clicks **Save** → JJ commit created
6. User clicks **Cancel** → All changes discarded, file reverts

### 2.4 Selection + AI Action (Slice 12)

When the user highlights text in the Canvas:

```
┌──────────────────────────────────────┐
│ Our customers [struggle with long    │  ← Selected text
│ onboarding cycles that can take]     │
│ months to complete.                  │
│         ┌─────────────────────────┐  │
│         │ Ask AI about selection  │  │
│         │ ____________________    │  │
│         │ "make this more urgent" │  │
│         │            [Submit] ▶   │  │
│         └─────────────────────────┘  │
└──────────────────────────────────────┘
```

- A popup appears near the selection
- User types an instruction (e.g., "make this more urgent", "expand on this", "simplify")
- Agent receives the instruction with selection context
- Agent edits only the selected portion (or nearby, as appropriate)

---

## 3. Technical Architecture

### 3.1 Why AST? (Slice 11+)

Using an Abstract Syntax Tree (AST) for markdown enables:

| Capability | Benefit |
|------------|---------|
| **Targeted edits** | Agent can modify specific nodes (paragraphs, headers, lists) without re-rendering entire document |
| **Selection mapping** | Map user's text selection to specific AST nodes |
| **Structural awareness** | Agent knows document structure (e.g., "rewrite the second bullet under Key Pain Points") |
| **Diff generation** | Generate precise diffs for ag-ui events |
| **WYSIWYG rendering** | Each AST node maps to a rendered component |

### 3.2 AST Library Choice

**Recommended: [unified](https://unifiedjs.com/) ecosystem**

- **remark** – Markdown ↔ AST (mdast)
- **rehype** – HTML ↔ AST (hast)  
- **remark-rehype** – Transform mdast → hast for rendering

```
Markdown String
     ↓ remark.parse()
   mdast (Markdown AST)
     ↓ remark-rehype
   hast (HTML AST)
     ↓ rehype-react / custom renderer
   React Components (WYSIWYG)
```

### 3.3 AST Node Example

```javascript
// Markdown: "## Key Pain Points\n\n- Long onboarding"

{
  type: 'root',
  children: [
    {
      type: 'heading',
      depth: 2,
      children: [{ type: 'text', value: 'Key Pain Points' }],
      position: { start: { line: 1, column: 1 }, end: { line: 1, column: 18 } }
    },
    {
      type: 'list',
      ordered: false,
      children: [
        {
          type: 'listItem',
          children: [
            {
              type: 'paragraph',
              children: [{ type: 'text', value: 'Long onboarding' }]
            }
          ]
        }
      ]
    }
  ]
}
```

### 3.4 WYSIWYG Editor (Slice 11)

**Slice 4 (MVP):** Simple textarea + live markdown preview using [marked.js](https://marked.js.org/)

**Slice 11 (Post-MVP):** Upgrade to WYSIWYG. Vanilla JS options (no React):

| Option | Pros | Cons |
|--------|------|------|
| **[Quill.js](https://quilljs.com/)** | Popular, well-documented, easy to integrate | Delta format (not markdown-native) |
| **[Editor.js](https://editorjs.io/)** | Block-based, clean JSON output, extensible | Block-based (different mental model) |
| **[ProseMirror](https://prosemirror.net/)** | Most flexible, markdown-native possible | Steeper learning curve |
| **[Milkdown](https://milkdown.dev/)** | Built on ProseMirror, markdown-first, plugin system | Newer, smaller community |

**Recommended: ProseMirror or Milkdown** – both support markdown-native editing and work without React.

All options support:
- Rich text editing with markdown shortcuts
- Custom node types
- Selection tracking
- Programmatic content updates

**Integration pattern (Slice 11+):**

```
┌─────────────────────────────────────────────────────────────────┐
│                         CANVAS STATE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐    │
│   │  Markdown   │ ───▶ │    mdast    │ ───▶ │   Editor    │    │
│   │   String    │      │    (AST)    │      │  (Vanilla)  │    │
│   └─────────────┘      └─────────────┘      └─────────────┘    │
│         ▲                    ▲ │                   │            │
│         │                    │ │                   │            │
│         │              ┌─────┘ └─────┐             │            │
│         │              │             │             │            │
│    serialize      Agent Edit    User Edit     onChange         │
│         │              │             │             │            │
│         └──────────────┴─────────────┴─────────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Slice 4 (MVP) pattern:**

```
┌─────────────────────────────────────────────────────────────────┐
│                         CANVAS STATE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐                           ┌─────────────┐    │
│   │  Markdown   │ ◀────── User Edit ──────▶ │  Textarea   │    │
│   │   String    │                           │             │    │
│   └──────┬──────┘                           └─────────────┘    │
│          │                                                      │
│          │ marked.js                                            │
│          ▼                                                      │
│   ┌─────────────┐                                               │
│   │   Preview   │  (rendered HTML, read-only)                   │
│   │    Panel    │                                               │
│   └─────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. ag-ui Integration (Slice 12)

### 4.1 Event Flow

The ag-ui protocol enables bidirectional sync between Canvas and Chat. This is implemented in Slice 12.

```
┌─────────────┐                              ┌─────────────┐
│   CANVAS    │                              │    CHAT     │
│   (User)    │                              │   (Agent)   │
└──────┬──────┘                              └──────┬──────┘
       │                                            │
       │  user_edit                                 │
       │  {path: "Challenge.md",                    │
       │   operation: "replace",                    │
       │   range: {start: 45, end: 67},             │
       │   content: "enterprise customers"}         │
       │ ──────────────────────────────────────────▶│
       │                                            │
       │                                            │ (Agent sees edit,
       │                                            │  may respond)
       │                                            │
       │                              agent_edit    │
       │  {path: "Challenge.md",                    │
       │   operation: "replace",                    │
       │   range: {start: 120, end: 180},           │
       │   content: "...refined text..."}           │
       │◀────────────────────────────────────────── │
       │                                            │
       │  (Canvas updates)                          │
       │                                            │
```

### 4.2 Event Types

#### Canvas → Agent (User Actions)

```javascript
// CanvasUserEdit - sent when user edits content
{
  type: 'user_edit',
  file_path: 'Challenge.md',
  operation: 'insert' | 'replace' | 'delete',
  range: { start: 45, end: 67 },  // Character offsets
  content: 'new text here',       // For insert/replace
  ast_path: ['root', 'paragraph', '0'],  // Optional: path to AST node (Slice 11+)
  timestamp: '2026-01-02T10:30:00Z'
}

// CanvasSelectionAction - sent when user requests AI action on selection
{
  type: 'selection_action',
  file_path: 'Challenge.md',
  selection: { start: 45, end: 67 },
  selected_text: 'the selected text',
  instruction: 'make this more urgent',
  timestamp: '2026-01-02T10:30:00Z'
}
```

#### Agent → Canvas (Agent Actions)

```javascript
// AgentEdit - agent's targeted edit to canvas
{
  type: 'agent_edit',
  file_path: 'Challenge.md',
  operation: 'insert' | 'replace' | 'delete',
  range: { start: 120, end: 180 },
  content: 'refined text from agent',
  timestamp: '2026-01-02T10:30:05Z'
}

// AgentEditStream - streaming edit events
// Start:
{ type: 'agent_edit_stream_start', file_path: 'Challenge.md', message_id: 'msg_123', range: { start: 120, end: 180 } }
// Chunks:
{ type: 'agent_edit_stream_chunk', file_path: 'Challenge.md', message_id: 'msg_123', chunk: 'partial text...' }
// End:
{ type: 'agent_edit_stream_end', file_path: 'Challenge.md', message_id: 'msg_123' }
```

### 4.3 Conflict Handling (MVP)

For MVP, we use a **last-write-wins** strategy:

- User and agent can edit simultaneously
- Edits are applied in order received
- No locking, no operational transform
- If edits overlap, later edit may overwrite earlier

**Future:** Implement operational transforms or CRDTs for proper conflict resolution.

---

## 5. State Management

### 5.1 Canvas State

**Slice 4 (MVP):**

```javascript
// Simple state for textarea + preview
const canvasState = {
  // File info
  file_path: 'Challenge.md',
  file_type: 'kernel',  // 'kernel' | 'context'

  // Content
  original_content: '',  // Content when file was opened
  current_content: '',   // Current textarea content

  // Editor state
  is_dirty: false,       // Has unsaved changes
}
```

**Slice 11+ (WYSIWYG + AST):**

```javascript
// Extended state for WYSIWYG with AST
const canvasState = {
  // File info
  file_path: 'Challenge.md',
  file_type: 'kernel',

  // Content
  original_content: '',
  current_content: '',
  ast: null,             // mdast root node (Slice 11+)

  // Editor state
  is_dirty: false,
  selection: null,       // { start, end } or null
  editorInstance: null,  // WYSIWYG editor instance

  // Agent sync (Slice 12)
  pending_agent_edits: [],
  last_sync_timestamp: null,
}
```

### 5.2 Edit Lifecycle

**Slice 4 (MVP):**

```
┌──────────────────────────────────────────────────────────────────┐
│                    EDIT LIFECYCLE (Slice 4)                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. File Opened                                                  │
│     └─▶ Load markdown from API                                   │
│     └─▶ Display in textarea                                      │
│     └─▶ Render preview with marked.js                            │
│     └─▶ Store original_content                                   │
│                                                                  │
│  2. User Edits                                                   │
│     └─▶ Update textarea content                                  │
│     └─▶ Re-render preview                                        │
│     └─▶ Set is_dirty = true                                      │
│                                                                  │
│  3a. User Clicks SAVE                                            │
│      └─▶ PUT /api/ideas/{id}/kernel/{type}                       │
│      └─▶ Backend creates JJ commit                               │
│      └─▶ Update original_content                                 │
│      └─▶ Set is_dirty = false                                    │
│      └─▶ Navigate back to Idea workspace                         │
│                                                                  │
│  3b. User Clicks CANCEL                                          │
│      └─▶ Confirm if is_dirty ("Discard changes?")                │
│      └─▶ Discard current_content                                 │
│      └─▶ Navigate back to Idea workspace                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Slice 11+ (with AST and agent edits):**

```
┌──────────────────────────────────────────────────────────────────┐
│                   EDIT LIFECYCLE (Slice 11+)                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. File Opened                                                  │
│     └─▶ Load markdown from API                                   │
│     └─▶ Parse to AST (remark)                                    │
│     └─▶ Render in WYSIWYG editor                                 │
│     └─▶ Store original_content                                   │
│                                                                  │
│  2. User/Agent Edits                                             │
│     └─▶ Update editor content                                    │
│     └─▶ Re-parse AST                                             │
│     └─▶ Emit ag-ui event (Slice 12)                              │
│     └─▶ Set is_dirty = true                                      │
│                                                                  │
│  3a. User Clicks SAVE                                            │
│      └─▶ Serialize AST to markdown                               │
│      └─▶ PUT /api/ideas/{id}/kernel/{type}                       │
│      └─▶ Backend creates JJ commit                               │
│      └─▶ Update original_content                                 │
│      └─▶ Set is_dirty = false                                    │
│      └─▶ Navigate back to Idea workspace                         │
│                                                                  │
│  3b. User Clicks CANCEL                                          │
│      └─▶ Confirm if is_dirty ("Discard changes?")                │
│      └─▶ Discard current_content                                 │
│      └─▶ Navigate back to Idea workspace                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. WYSIWYG Formatting Support (Slice 11)

### 6.1 Supported Formatting

| Format | Markdown | Toolbar | Shortcut |
|--------|----------|---------|----------|
| **Bold** | `**text**` | ✓ | Cmd+B |
| *Italic* | `*text*` | ✓ | Cmd+I |
| Heading 1 | `# text` | ✓ | Cmd+1 |
| Heading 2 | `## text` | ✓ | Cmd+2 |
| Heading 3 | `### text` | ✓ | Cmd+3 |
| Bullet List | `- item` | ✓ | - + Space |
| Numbered List | `1. item` | ✓ | 1. + Space |
| Blockquote | `> text` | ✓ | > + Space |
| Code (inline) | `` `code` `` | ✓ | Cmd+E |
| Link | `[text](url)` | ✓ | Cmd+K |

### 6.2 Future Formatting (Post-MVP)

- Code blocks with syntax highlighting
- Tables
- Images (when file upload is supported)
- Task lists (`- [ ] item`)

---

## 7. Component Structure

**Slice 4 (MVP) - Vanilla JS:**

```
frontend/js/
├── concepts/
│   └── canvas.js             # Canvas state + actions (textarea + preview)
├── pages/
│   └── file-editor.js        # 50/50 layout: chat placeholder + canvas
├── components/
│   └── canvas-footer.js      # Save/Cancel buttons
└── lib/
    └── markdown.js           # marked.js wrapper for preview
```

**Slice 11+ (WYSIWYG) - Vanilla JS:**

```
frontend/js/
├── concepts/
│   └── canvas.js             # Extended with AST, editor instance
├── pages/
│   └── file-editor.js        # 50/50 layout: chat + WYSIWYG canvas
├── components/
│   ├── canvas-toolbar.js     # Formatting toolbar (Slice 11)
│   ├── canvas-footer.js      # Save/Cancel buttons
│   └── selection-popup.js    # "Ask AI" popup (Slice 12)
├── lib/
│   ├── editor.js             # WYSIWYG editor wrapper (ProseMirror/Milkdown)
│   └── markdown-ast.js       # remark/unified AST parsing
└── sync/
    └── canvas-sync.js        # ag-ui event handling (Slice 12)
```

---

## 8. API Integration

### 8.1 Loading File

```javascript
// GET /api/ideas/{idea_id}/kernel/{file_type}
// GET /api/ideas/{idea_id}/context/{file_id}

// Response:
{
  content: '# Challenge\n\nOur customers...',  // Raw markdown
  updated_at: '2026-01-02T10:30:00Z',
  updated_by: 'sally_chen',
  is_complete: false  // For kernel files only
}
```

### 8.2 Saving File

```javascript
// PUT /api/ideas/{idea_id}/kernel/{file_type}
// PUT /api/ideas/{idea_id}/context/{file_id}

// Request:
{
  content: '# Challenge\n\nUpdated content...',  // Markdown string
  commit_message: 'Updated challenge focus'      // Optional
}

// Response:
{
  version: 'abc123def',      // JJ commit hash
  saved_at: '2026-01-02T10:35:00Z'
}
```

---

## 9. Agent Context (Slice 12)

When the agent receives user edits or selection actions, it should have access to:

```javascript
// Context provided to agent for canvas interactions
const agentCanvasContext = {
  file_path: 'Challenge.md',
  file_type: 'challenge',  // 'summary' | 'challenge' | 'approach' | 'coherent_steps' | 'context'
  full_content: '# Challenge\n\nCurrent content...',
  recent_edits: [
    // Last N user_edit events (see section 4.2)
  ],

  // For selection actions (when user selects text + types instruction)
  selection: {
    text: 'selected text here',
    instruction: 'make this more urgent',
    position: { start: 45, end: 67 }
  }
}
```

---

## 10. Error Handling

| Scenario | Behavior |
|----------|----------|
| **Save fails** | Show error toast, keep editor open, allow retry |
| **Agent edit conflicts with user typing** | Apply agent edit anyway (last-write-wins) |
| **Connection lost** | Show warning banner, queue edits, retry when reconnected |
| **File modified externally** | On save, show conflict dialog (future: merge) |

---

## 11. Open Questions

1. **Undo/Redo:** Should undo include agent edits, or only user edits?
2. **Version preview:** Should user be able to preview before saving?
3. **Auto-save drafts:** Should we auto-save to localStorage to prevent data loss?
4. **Agent streaming UX:** When agent is editing, should we show a typing indicator in Canvas?

---

## 12. Implementation Phases

### Slice 4 (MVP) - Basic Editor
- [ ] Textarea for markdown editing
- [ ] Live preview panel (marked.js)
- [ ] Canvas state management (content, is_dirty)
- [ ] Save → JJ commit via API
- [ ] Cancel → Discard changes with confirmation
- [ ] 50/50 layout with chat placeholder

### Slice 11 (Post-MVP) - WYSIWYG Upgrade
- [ ] Evaluate and integrate Vanilla JS editor (ProseMirror/Milkdown/Quill)
- [ ] Markdown ↔ AST parsing (remark/unified)
- [ ] Formatting toolbar
- [ ] Keyboard shortcuts (Cmd+B, Cmd+I, etc.)
- [ ] Editor ↔ AST synchronization
- [ ] Cursor position preservation

### Slice 12 (Post-MVP) - Agent Integration
- [ ] Selection + AI action popup
- [ ] ag-ui bidirectional sync
- [ ] User edit events sent to agent
- [ ] Agent edit events applied to canvas
- [ ] Streaming agent edits with live updates
- [ ] Last-write-wins conflict handling

### Future (Post Slice 12)
- [ ] Operational transforms or CRDTs for conflict resolution
- [ ] Version preview before save
- [ ] Auto-save drafts to localStorage
- [ ] Collaborative editing (multiple users)

---

*Document version: 0.2.0*
*Last updated: 2026-01-02*