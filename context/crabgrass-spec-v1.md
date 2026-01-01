# Crabgrass: Product Specification

**Version:** 0.2.0
**Date:** 2025-12-31
**Status:** MVP Specification

---

## Executive Summary

Crabgrass is an innovation acceleration platform that transforms scattered organizational knowledge into competitive advantage. It treats ideas as structured projects with AI-powered coaching that proactively moves ideas from conception toward innovation.

**Core thesis:** The gap between "idea" and "innovation" is where organizational value is created or lost. Crabgrass closes that gap by harvesting human insight—the one thing LLMs cannot generate—and connecting it to AI-powered acceleration.

**Tagline:** *Human insight, AI acceleration. From idea to innovation.*

---

## Table of Contents

1. [Vision & Problem Statement](#1-vision--problem-statement)
2. [Conceptual Model](#2-conceptual-model)
3. [Architecture](#3-architecture)
4. [Data Model](#4-data-model)
5. [Agent System](#5-agent-system)
6. [User Interface](#6-user-interface)
7. [Tech Stack](#7-tech-stack)
8. [API Specification](#8-api-specification)
9. [Security & Permissions](#9-security--permissions)
10. [Roadmap](#10-roadmap)

---

## 1. Vision & Problem Statement

### 1.1 The Problem

Organizations don't suffer from a shortage of ideas—they suffer from an inability to move ideas through the transformation spectrum:

| Stage | Definition | What It Requires |
|-------|------------|------------------|
| **Idea** | A concept or thought | Cheap and abundant |
| **Innovative Idea** | An idea with novel, insightful, or strategic qualities | Insight + Intent + Connection |
| **Innovation** | An idea that survives contact with reality and delivers value | Execution + Adoption + Impact |

Most ideas never leave stage one. They remain unconnected, ungrounded, and eventually forgotten.

### 1.2 The Opportunity

LLMs are extraordinarily powerful but have a critical limitation—they don't know what's inside your organization:

- The scattered insights across teams
- The emerging patterns in operations
- The strategic objectives only leadership understands
- The tacit knowledge employees carry

**Crabgrass mines insight from across the organization to do battle with the LLM.**

### 1.3 The Posture

The relationship with AI is deliberately combative. Don't treat the LLM as an oracle—treat it as a sparring partner. Bring organizational insight the LLM cannot generate, and force it to work with that. Value emerges from the collision.

---

## 2. Conceptual Model

### 2.1 Idea as Project

An **Idea** in Crabgrass is a project container with two types of files:

#### Kernel Files (Required, Structured)

| File | Purpose | Properties |
|------|---------|------------|
| `Summary.md` | High-level description of the idea | Always present, synced to DB |
| `Challenge.md` | The problem being solved | Always present, synced to DB |
| `Approach.md` | How the challenge will be addressed | Always present, synced to DB |
| `CoherentSteps.md` | Concrete actions to execute | Always present, synced to DB |

**Kernel File Properties:**
- Cannot be deleted (only edited)
- Synced to vector database for similarity search
- Synced to graph database for relationship mapping
- Version controlled via JJ
- Collaborative (multiple editors)

#### Context Files (Optional, Markdown)

Additional Markdown files created by the user or agent to support the idea:
- Research notes
- Customer interview summaries
- Meeting notes
- Technical references
- Any supporting documentation

**Context File Properties:**
- Markdown files only (`.md` extension)
- No spaces in filenames (use hyphens: `customer-interview.md`)
- Maximum 50KB per file (~12K tokens)
- Can be created by user or agent
- Can be deleted
- Readable by agent for context
- Referenced in chat using `@filename.md` syntax
- Not synced to vector/graph DB (only Kernel Files are indexed)

**Future:** Support for uploading unstructured files (PDFs, images, data files) is planned, moving toward a more IDE-like project experience.

### 2.2 Idea Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                        IDEA LIFECYCLE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│        ┌──────────┐         ┌──────────┐         ┌──────────┐  │
│        │  Draft   │────────▶│  Active  │────────▶│ Archived │  │
│        │          │         │          │         │          │  │
│        │ 0-3 files│         │ 4 files  │         │          │  │
│        │ complete │         │ complete │         │          │  │
│        └──────────┘         └──────────┘         └──────────┘  │
│             │                    │                              │
│             ▼                    ▼                              │
│        Agent coaches        Coherence                           │
│        per kernel file      agent checks                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Objectives

Ideas can be linked to organizational objectives:

- Ideas can optionally be linked to one objective (can be attached later)
- Objectives are flat (no hierarchy for MVP)
- Only org admins can create/edit objectives
- All org members can view objectives and link ideas to them
- CoherenceAgent can suggest objectives based on idea content

---

## 3. Architecture

### 3.1 Design Philosophy: Concepts and Synchronizations

Crabgrass follows the Concepts and Synchronizations model (Jackson, MIT 2025) for both backend and frontend. See [concepts-and-synchronizations.md](./concepts-and-synchronizations.md) for the complete concept and synchronization definitions.

**Concepts** are independent, self-contained units of functionality with:
- Clear purpose
- Defined state
- Explicit actions
- Observable behavior

**Synchronizations** coordinate concepts without coupling them.

### 3.2 Concept Summary

**Backend Concepts (10):**
- Idea, Objective, KernelFile, ContextFile
- Version (JJ), Embedding
- User, Organization, Collab, Session

**Frontend Concepts (8):**
- IdeaWorkspace, ObjectiveWorkspace
- Canvas, Chat, FileList
- KernelStatus, Toast, IdeaList

**Agents (7):**
- SummaryAgent, ChallengeAgent, ApproachAgent, StepsAgent
- CoherenceAgent, ContextAgent, ObjectiveAgent

### 3.3 System Architecture Diagram

See [tech-stack.md](./tech-stack.md) for the complete system architecture diagram.

---

## 4. Data Model

### 4.1 Core Tables (DuckDB)

```sql
-- Organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings JSON
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    email VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preferences JSON
);

-- Objectives (flat, no hierarchy)
CREATE TABLE objectives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    title VARCHAR NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id),
    timeframe VARCHAR, -- 'Q1 2025', 'FY25', 'H1 2025', etc.
    status VARCHAR DEFAULT 'active', -- active, achieved, deprecated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id)
);

-- Ideas (Projects)
CREATE TABLE ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    creator_id UUID REFERENCES users(id),
    objective_id UUID REFERENCES objectives(id), -- optional, can be attached later
    title VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'draft', -- draft, active, archived
    kernel_completion INTEGER DEFAULT 0, -- 0-4 count of completed kernel files
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    jj_repo_path VARCHAR -- path to JJ repository
);

-- Kernel Files (always exist, versioned content)
CREATE TABLE kernel_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID REFERENCES ideas(id),
    file_type VARCHAR NOT NULL, -- 'summary', 'challenge', 'approach', 'coherent_steps'
    content TEXT,
    content_hash VARCHAR, -- for change detection
    is_complete BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES users(id),
    UNIQUE(idea_id, file_type)
);

-- Context Files (Markdown only, can be deleted)
CREATE TABLE context_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID REFERENCES ideas(id),
    filename VARCHAR NOT NULL,              -- Must end in .md, no spaces (e.g., 'research-notes.md')
    content TEXT,                           -- Markdown content, max 50KB
    size_bytes INTEGER,                     -- Tracked for 50KB limit enforcement
    created_by UUID REFERENCES users(id),   -- NULL if created by agent
    created_by_agent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_filename CHECK (filename ~ '^[a-zA-Z0-9_-]+\.md$'),
    CONSTRAINT max_size CHECK (size_bytes <= 51200)  -- 50KB limit
);

-- Collaborators
CREATE TABLE idea_collaborators (
    idea_id UUID REFERENCES ideas(id),
    user_id UUID REFERENCES users(id),
    role VARCHAR DEFAULT 'contributor', -- 'owner', 'contributor', 'viewer'
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (idea_id, user_id)
);

-- Sessions (conversation threads with agents)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID REFERENCES ideas(id),
    user_id UUID REFERENCES users(id),
    agent_type VARCHAR NOT NULL, -- 'coherence', 'summary', 'challenge', 'approach', 'steps', 'context', 'objective'
    title VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session Messages
CREATE TABLE session_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    role VARCHAR NOT NULL, -- 'user', 'agent'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Vector Storage (VSS Extension)

```sql
-- Vector embeddings for semantic search
CREATE TABLE kernel_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kernel_file_id UUID REFERENCES kernel_files(id),
    idea_id UUID REFERENCES ideas(id),
    file_type VARCHAR,
    embedding FLOAT[768], -- Gemini embedding dimension
    content_hash VARCHAR, -- to detect when re-embedding needed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create VSS index
CREATE INDEX kernel_embedding_idx ON kernel_embeddings 
USING vss(embedding) WITH (metric = 'cosine');

-- Example similarity query
-- SELECT idea_id, file_type, 
--        vss_cosine_similarity(embedding, $query_embedding) as similarity
-- FROM kernel_embeddings
-- WHERE vss_cosine_similarity(embedding, $query_embedding) > 0.7
-- ORDER BY similarity DESC
-- LIMIT 10;
```

### 4.3 Graph Storage (DuckPGQ) - MVP

For MVP, the graph schema is minimal. Advanced graph relationships (similar_challenge, complementary_approach, etc.) are deferred to Phase 2.

```sql
-- MVP Graph schema - basic relationships only
CREATE PROPERTY GRAPH idea_graph
VERTEX TABLES (
    ideas,
    objectives,
    users,
    organizations
)
EDGE TABLES (
    -- Idea supports Objective (optional, can be attached later)
    idea_objective_links SOURCE KEY (idea_id) REFERENCES ideas(id)
                         DESTINATION KEY (objective_id) REFERENCES objectives(id),
    -- User collaborates on Idea
    idea_collaborators SOURCE KEY (idea_id) REFERENCES ideas(id)
                       DESTINATION KEY (user_id) REFERENCES users(id),
    -- User is member of Organization
    user_orgs SOURCE KEY (user_id) REFERENCES users(id)
              DESTINATION KEY (org_id) REFERENCES organizations(id)
);
```

### 4.4 JJ Repository Structure

Each idea has a JJ repository at `{storage_root}/ideas/{idea_id}/`:

```
/ideas/{idea_id}/
├── .jj/                    # JJ internal
├── kernel/
│   ├── Summary.md
│   ├── Challenge.md
│   ├── Approach.md
│   └── CoherentSteps.md
└── context/
    ├── customer_interview.md
    ├── research.pdf
    └── ...
```

**JJ Operations Mapped to User Actions:**

| User Action | JJ Operation | Notes |
|-------------|--------------|-------|
| Edit file | Working copy change | Auto-tracked |
| Save | `jj commit` | With structured message |
| View history | `jj log` | Show in UI |
| Branch idea | `jj branch create` | "What if" exploration |
| Merge branch | `jj merge` | Conflict-free by design |
| Undo | `jj undo` | Operation log |

---

## 5. Agent System

### 5.1 Agent Philosophy

The Crabgrass agent is **proactive, not reactive**. It doesn't wait for user requests—it actively coaches users to develop their ideas.

**Posture:** Coach, not assistant. Sparring partner, not oracle.

### 5.2 Agent Types

See [concepts-and-synchronizations.md](./concepts-and-synchronizations.md) for detailed agent specifications.

| Agent | Purpose | Trigger |
|-------|---------|---------|
| **SummaryAgent** | Coach clear, concise, compelling summary | User edits Summary.md |
| **ChallengeAgent** | Coach specific, measurable, significant challenge | User edits Challenge.md |
| **ApproachAgent** | Coach feasible, differentiated approach | User edits Approach.md |
| **StepsAgent** | Coach concrete, sequenced, assignable steps | User edits CoherentSteps.md |
| **CoherenceAgent** | Check cross-file logical consistency | 2+ kernel files complete |
| **ContextAgent** | Extract insights from uploaded files | Context file added |
| **ObjectiveAgent** | Coach objective definition, show alignment | User edits objective |

### 5.3 Completion Criteria

Each kernel file agent evaluates content against specific criteria:

| File | Criteria |
|------|----------|
| Summary.md | Clear, Concise, Compelling |
| Challenge.md | Specific, Measurable, Significant |
| Approach.md | Feasible, Differentiated, Addresses Challenge |
| CoherentSteps.md | Concrete, Sequenced, Assignable |

### 5.4 Notification Priority

| Priority | Type | Delivery |
|----------|------|----------|
| **High** | Coherence problem | Immediate toast |
| **Medium** | Quality suggestion, Context insight | In-panel |
| **Low** | Completion nudge | In-panel on next visit |

---

## 6. User Interface

See [wireframes.md](./wireframes.md) for the complete UI specification including:

- **Screen 1: Home (Ideas List)** - Dashboard showing ideas and objectives
- **Screen 2: Idea Workspace** - Vertical layout with CoherenceAgent chat, kernel files, context files
- **Screen 3: File Editor** - 50/50 split with chat + canvas for editing any file
- **Screen 4: Objective Workspace** - Similar to Idea Workspace but for objectives
- **Session Management** - Conversation history per agent
- **Version History** - File history via JJ

### 6.1 Design Philosophy

The UI emulates **Claude Projects** with a vertical, document-centric layout:

| Claude Projects | Crabgrass | Notes |
|-----------------|-----------|-------|
| Project | Idea | Core work container |
| Project Files | Kernel Files (4) + Context Files | Kernel files are fixed and required |
| Chat | Agent Chat | Specialized agents per context |
| — | Objective | Strategic container with similar pattern |

### 6.2 Key UI Principles

- Vertical layout mirrors Claude Projects
- Each file opens in a dedicated editor screen (50/50 chat + canvas)
- Agents coach you through completing files
- Consistent pattern across Ideas and Objectives

### 6.3 Sharing & Permissions

| Role | View | Comment | Edit | Manage Collaborators |
|------|------|---------|------|---------------------|
| **Viewer** | ✓ | ✓ | ✗ | ✗ |
| **Contributor** | ✓ | ✓ | ✓ | ✗ |
| **Owner** | ✓ | ✓ | ✓ | ✓ |

---

## 7. Tech Stack

See [tech-stack.md](./tech-stack.md) for the complete technology stack including:
- Overview of all technologies and rationale
- Python dependencies (pyproject.toml)
- Frontend and backend directory structures
- System architecture diagram

---

## 8. API Specification

### 8.1 REST Endpoints

#### Ideas

```
GET    /api/ideas                    # List user's ideas
POST   /api/ideas                    # Create new idea
GET    /api/ideas/{id}               # Get idea details
PATCH  /api/ideas/{id}               # Update idea metadata
DELETE /api/ideas/{id}               # Archive idea (soft delete)
```

#### Files

```
GET    /api/ideas/{id}/kernel/{type}       # Get kernel file
PUT    /api/ideas/{id}/kernel/{type}       # Update kernel file
GET    /api/ideas/{id}/kernel/{type}/history  # Get file history

GET    /api/ideas/{id}/context             # List context files
POST   /api/ideas/{id}/context             # Create context file (Markdown only, no spaces, max 50KB)
GET    /api/ideas/{id}/context/{file_id}   # Get context file
PUT    /api/ideas/{id}/context/{file_id}   # Update context file
DELETE /api/ideas/{id}/context/{file_id}   # Delete context file
```

#### Objectives

```
GET    /api/objectives               # List org objectives
POST   /api/objectives               # Create objective (admin only)
GET    /api/objectives/{id}          # Get objective details
PATCH  /api/objectives/{id}          # Update objective (admin only)
GET    /api/objectives/{id}/ideas    # Get ideas linked to objective
```

#### Agent

```
POST   /api/ideas/{id}/agent/analyze    # Trigger agent analysis
GET    /api/ideas/{id}/agent/suggestions  # Get pending suggestions
POST   /api/ideas/{id}/agent/respond    # Respond to suggestion
```

### 8.2 SSE Protocol

Server-Sent Events provide server → client streaming. Client → server uses REST.

```
# SSE Connection
GET /api/ideas/{id}/events
Accept: text/event-stream
```

#### Server → Client (SSE Stream)

```javascript
// Agent suggestion
event: agent_message
data: {"id": "msg_123", "content": "Your Challenge could be more specific...", "actions": ["edit", "dismiss"], "priority": "medium"}

// File save confirmation
event: file_saved
data: {"file_type": "challenge", "version": "abc123", "saved_at": "2025-01-15T10:30:00Z"}

// Kernel file completion status changed
event: completion_changed
data: {"idea_id": "...", "file_type": "challenge", "is_complete": true, "total_complete": 2}
```

#### Client → Server (REST)

```
# Update file content
PUT /api/ideas/{id}/kernel/{type}
Content-Type: application/json
{"content": "..."}

# Send chat message to agent
POST /api/ideas/{id}/agent/chat
Content-Type: application/json
{"message": "Can you help me refine this?"}
```

### 8.3 AG-UI Protocol Integration

For streaming agent responses over SSE:

```
event: agent_stream_start
data: {"message_id": "msg_456"}

event: agent_stream_chunk
data: {"message_id": "msg_456", "chunk": "Your approach..."}

event: agent_stream_chunk
data: {"message_id": "msg_456", "chunk": " could benefit from..."}

event: agent_stream_end
data: {"message_id": "msg_456", "actions": [{"id": "edit", "label": "Edit Approach"}, {"id": "dismiss", "label": "Dismiss"}]}
```

---

## 9. Security & Permissions

### 9.1 Authentication

- **Demo:** Simple session-based auth
- **Production:** OAuth2/OIDC (Google Workspace, Okta, etc.)

### 9.2 Authorization Model

```
Organization
└── Users (members of org)
    └── Ideas (owned by user, visible to org)
        └── Collaborators (explicit access)
```

### 9.3 Idea Visibility

| Visibility | Who Can See | Who Can Edit |
|------------|-------------|--------------|
| **Private** | Owner + Collaborators | Owner + Editors |
| **Org** | All org members | Owner + Editors |
| **Public** | Anyone with link | Owner + Editors |

Default: **Org** (visible to organization for cross-idea discovery)

### 9.4 Data Isolation

- Each organization has isolated data
- Vector search scoped to organization
- Graph queries scoped to organization
- JJ repositories isolated per idea

---

## 10. Roadmap

### Phase 1: MVP

**Goal:** Core idea creation with agent coaching

- [ ] Core data model (DuckDB tables for ideas, objectives, kernel files, context files)
- [ ] Idea CRUD operations with objective linking
- [ ] Kernel file editing with Markdown
- [ ] All 7 agents (Summary, Challenge, Approach, Steps, Coherence, Context, Objective)
- [ ] Web UI (Home, Idea Workspace, Objective Workspace, File Editor)
- [ ] JJ integration for versioning
- [ ] Session management (conversation history per agent)
- [ ] Basic collaboration (owner, contributor, viewer roles)
- [ ] Embeddings for kernel files (stored for future search)

### Phase 2: Search & Connections

**Goal:** Cross-idea discovery and connections

- [ ] Semantic search using stored embeddings
- [ ] ConnectionAgent for discovering related ideas
- [ ] Similar challenge / complementary approach relationships
- [ ] Graph traversal for idea networks
- [ ] Notification system (email digests, push)

### Phase 3: Scale

**Goal:** Production readiness

- [ ] Performance optimization
- [ ] Advanced analytics dashboard
- [ ] API for integrations
- [ ] Mobile-responsive UI
- [ ] Objective hierarchy (parent/child)

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Idea** | A project container in Crabgrass, linked to an Objective |
| **Objective** | Org-wide strategic goal that ideas support (flat, admin-created) |
| **Kernel File** | One of the four required structured files (Summary, Challenge, Approach, Coherent Steps) |
| **Context File** | Optional Markdown file for supporting material, referenced via `@filename.md` |
| **Session** | Persistent conversation thread with an agent |
| **Agent** | The proactive AI coach (7 types: Summary, Challenge, Approach, Steps, Coherence, Context, Objective) |
| **Concept** | An independent unit of functionality (architecture pattern) |
| **Synchronization** | Coordination logic between concepts |
| **Connection** | A relationship between two ideas (Phase 2) |

---

## Appendix B: References

- [Concepts and Synchronizations (MIT 2025)](https://news.mit.edu/2025/mit-researchers-propose-new-model-for-legible-modular-software-1106)
- [JJ (Jujutsu) VCS](https://github.com/jj-vcs/jj)
- [DuckDB](https://duckdb.org/)
- [DuckDB VSS Extension](https://duckdb.org/docs/extensions/vss)
- [DuckPGQ](https://github.com/cwida/duckpgq)
- [Google ADK](https://developers.google.com/agent-development-kit)
- [AG-UI Protocol](https://github.com/ag-ui-protocol/ag-ui)

---

*Document version: 0.2.0*
*Last updated: 2025-12-31*