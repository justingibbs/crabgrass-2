# Crabgrass: Concepts & Synchronizations

**Version:** 0.2.0
**Date:** 2025-12-31
**Architecture Pattern:** Concepts and Synchronizations (Jackson, MIT 2025)

---

## Overview

This document defines the modular architecture for Crabgrass using the **Concepts and Synchronizations** pattern. This approach separates:

- **Concepts**: Self-contained, independent units of functionality with clear purpose, state, and actions
- **Synchronizations**: Explicit rules defining how concepts interact without coupling them

The goal is legibility—developers should be able to read the system "like a book" where concepts map to familiar phenomena and synchronizations represent intuition about how they interact.

**Note:** For technology choices and stack details, see [tech-stack.md](./tech-stack.md).

---

## Table of Contents

1. [Backend Concepts](#1-backend-concepts)
2. [Frontend Concepts](#2-frontend-concepts)
3. [Specialized Agents](#3-specialized-agents)
4. [Graph Database Schema](#4-graph-database-schema)
5. [Synchronizations](#5-synchronizations)
6. [Design Decisions](#6-design-decisions)
7. [Deferred to Later Phases](#7-deferred-to-later-phases)

---

## 1. Backend Concepts

### 1.1 Idea

The core project container in Crabgrass. An idea progresses through lifecycle stages toward innovation.

**State:**
- `id`: Unique identifier
- `org_id`: Organization this idea belongs to
- `creator_id`: User who created it
- `title`: Display name
- `objective_id`: Linked objective (required)
- `status`: draft | active | archived
- `kernel_completion`: Count of completed kernel files (0-4)
- `jj_repo_path`: Path to JJ version control repository
- `created_at`, `updated_at`: Timestamps

**Actions:**
- `create(org_id, user_id, title, objective_id?)` - Create new idea (objective optional)
- `update(idea_id, fields)` - Update metadata
- `archive(idea_id)` - Soft delete
- `getStatus(idea_id)` - Get current lifecycle status
- `listAll(org_id, user_id, filters)` - List ideas user can access

**Constraints:**
- Ideas can optionally be linked to one Objective (can be attached later)
- Ideas belong to exactly one Organization
- Status transitions: draft → active → archived

---

### 1.2 Objective

Org-wide strategic objectives that ideas connect to. Flat structure (no hierarchy).

**State:**
- `id`: Unique identifier
- `org_id`: Organization this belongs to
- `title`: Display name
- `description`: Detailed description
- `owner_id`: User accountable for this objective
- `timeframe`: Q1 2025, FY25, H1 2025, etc.
- `status`: active | achieved | deprecated
- `created_at`, `created_by`: Timestamps and creator

**Actions:**
- `create(org_id, title, description, owner_id)` - Admin only
- `update(objective_id, fields)` - Admin only
- `archive(objective_id)` - Admin only
- `list(org_id)` - All users
- `getIdeas(objective_id)` - Get ideas supporting this objective

**Constraints:**
- Only org admins can create/update/archive
- All org members can view and link ideas to objectives

---

### 1.3 KernelFile

Required structured files that define an idea. Four types, cannot be deleted.

**File Types:**
1. `Summary.md` - High-level description of the idea
2. `Challenge.md` - The problem being solved
3. `Approach.md` - How the challenge will be addressed
4. `CoherentSteps.md` - Concrete actions to execute

**State:**
- `id`: Unique identifier
- `idea_id`: Parent idea
- `file_type`: summary | challenge | approach | coherent_steps
- `content`: Markdown content
- `content_hash`: For change detection
- `is_complete`: Boolean, determined by specialized agent
- `embedding`: Vector embedding (see [tech-stack.md](./tech-stack.md) for dimensions)
- `updated_at`, `updated_by`: Timestamps and last editor

**Actions:**
- `read(idea_id, file_type)` - Get content
- `update(idea_id, file_type, content)` - Save changes
- `markComplete(idea_id, file_type)` - Set completion status
- `getCompletionCount(idea_id)` - Count completed files (0-4)
- `setEmbedding(idea_id, file_type, embedding)` - Store vector

**Constraints:**
- Cannot be deleted (only edited)
- Always exist for every idea (initialized empty on idea creation)
- Completion determined by specialized agents, not users

---

### 1.4 ContextFile

Optional supporting materials uploaded by users or created by agents.

**State:**
- `id`: Unique identifier
- `idea_id`: Parent idea
- `filename`: Display name (must end in .md, no spaces)
- `content`: Markdown content (max 50KB)
- `created_by`: User ID or null if agent-created
- `created_by_agent`: Boolean
- `created_at`: Timestamp

**Actions:**
- `create(idea_id, filename, content, user_id?)` - Create file
- `read(idea_id, file_id)` - Get content
- `update(idea_id, file_id, content)` - Update content
- `delete(idea_id, file_id)` - Remove file
- `list(idea_id)` - List all context files

**Constraints:**
- Can be deleted (unlike kernel files)
- Markdown only, max 50KB
- Can be created by ContextAgent with insights

---

### 1.5 Version

JJ (Jujutsu) version control wrapper for file history.

**State:**
- Managed by JJ repository at `{storage_root}/ideas/{idea_id}/`

**Actions:**
- `initialize(idea_id)` - Create new JJ repository
- `commit(idea_id, file_type, content)` - Save version with structured message
- `history(idea_id, file_type?)` - Get commit history
- `restore(idea_id, file_type, commit_id)` - Restore to previous version

**Constraints:**
- One repository per idea
- Conflict-free by design (last-write-wins for simultaneous edits)
- Operations logged for full auditability

---

### 1.6 Search (Deferred to Phase 2)

Semantic search across ideas using vector embeddings. See [Section 7: Deferred to Later Phases](#7-deferred-to-later-phases).

---

### 1.7 Embedding

Vector generation for files.

**Actions:**
- `generate(content)` - Create embedding vector (see [tech-stack.md](./tech-stack.md) for model and dimensions)

**Constraints:**
- Embedding model configured in [tech-stack.md](./tech-stack.md)
- All kernel files get embeddings on save

---

### 1.8 User

Identity and preferences.

**State:**
- `id`: Unique identifier
- `org_id`: Organization membership
- `email`: Unique email
- `name`: Display name
- `role`: org_admin | member
- `preferences`: JSON settings
- `created_at`: Timestamp

**Actions:**
- `authenticate(credentials)` - Login
- `getPreferences(user_id)` - Get settings
- `updatePreferences(user_id, preferences)` - Save settings

---

### 1.9 Organization

Multi-tenant container.

**State:**
- `id`: Unique identifier
- `name`: Display name
- `settings`: JSON org-wide settings
- `created_at`: Timestamp

**Actions:**
- `create(name)` - Create new organization
- `getSettings(org_id)` - Get configuration
- `updateSettings(org_id, settings)` - Update configuration
- `listMembers(org_id)` - Get all users

---

### 1.10 Collab

Sharing and permissions for ideas.

**State:**
- `idea_id`, `user_id`: Composite key
- `role`: owner | contributor | viewer
- `added_at`: Timestamp

**Actions:**
- `invite(idea_id, user_id, role)` - Add collaborator
- `updateRole(idea_id, user_id, role)` - Change permission level
- `remove(idea_id, user_id)` - Remove access
- `listCollaborators(idea_id)` - Get all collaborators

**Constraints:**
- Owner cannot be removed (transfer ownership instead)
- Roles: owner (full control), contributor (can edit), viewer (read-only)

---

### 1.11 Session

Persistent conversation threads with agents.

**State:**
- `id`: Unique identifier
- `idea_id`: Parent idea
- `user_id`: Who started it
- `agent_type`: coherence | summary | challenge | approach | steps | context | objective
- `title`: Auto-generated or user-set
- `messages`: List of conversation messages
- `created_at`, `last_active`: Timestamps

**Actions:**
- `create(idea_id, user_id, agent_type)` - Start new conversation
- `addMessage(session_id, role, content)` - Add to history
- `getHistory(session_id, limit?)` - Load conversation
- `list(idea_id, agent_type?)` - All sessions for an idea/agent

**Constraints:**
- Sessions belong to one idea and one agent type
- Messages stored for context continuity

---

## 2. Frontend Concepts

### 2.1 IdeaWorkspace

The main workspace for viewing and editing an idea.

**State:**
- `idea`: Current idea data
- `kernelFiles`: List of kernel file metadata
- `contextFiles`: List of context file metadata
- `collaborators`: List of collaborators
- `currentSessionId`: Active chat session

**Actions:**
- `load(idea_id)` - Load idea and all related data
- `updateTitle(title)` - Update idea title
- `updateObjective(objective_id)` - Change linked objective
- `refresh()` - Reload from server

---

### 2.2 ObjectiveWorkspace

The workspace for viewing and editing an objective.

**State:**
- `objective`: Current objective data
- `linkedIdeas`: Ideas supporting this objective
- `contextFiles`: List of context file metadata
- `currentSessionId`: Active chat session

**Actions:**
- `load(objective_id)` - Load objective and linked ideas
- `refresh()` - Reload from server

---

### 2.3 Canvas

Markdown rendering and editing surface.

**State:**
- `content`: Current markdown content
- `isDirty`: Has unsaved changes
- `isEditing`: Edit mode vs preview mode
- `cursorPosition`: Current cursor location
- `selection`: Selected text range

**Actions:**
- `load(content)` - Initialize with content
- `edit()` - Enter edit mode
- `save()` - Persist changes
- `preview()` - Toggle preview mode
- `insertText(text, position)` - Add text
- `undo()` - Revert last change
- `redo()` - Restore reverted change

---

### 2.4 Chat

Agent conversation display.

**State:**
- `messages`: List of displayed messages
- `isStreaming`: Agent response in progress
- `pendingMessage`: User input being composed
- `currentSessionId`: Active session ID

**Actions:**
- `send(message)` - Send user message
- `receive(message)` - Display agent message
- `stream(chunk)` - Append streaming response
- `loadSession(session_id)` - Load previous conversation
- `newSession()` - Start fresh conversation

---

### 2.5 FileList

File navigation for kernel and context files.

**State:**
- `kernelFiles`: List of kernel files with completion status
- `contextFiles`: List of context files
- `selectedFile`: Currently selected file

**Actions:**
- `load(idea_id)` - Load file list
- `select(file_id, file_type)` - Select file for editing
- `createContextFile(filename)` - Create new context file
- `deleteContextFile(file_id)` - Remove context file

---

### 2.6 KernelStatus

Progress tracking for kernel file completion.

**State:**
- `completion`: Count of completed files (0-4)
- `fileStatuses`: Map of file_type → is_complete

**Actions:**
- `refresh(idea_id)` - Reload status
- `getProgress()` - Get completion count

---

### 2.7 Toast

Notification display.

**State:**
- `activeToasts`: Currently displayed notifications
- `queue`: Pending notifications

**Actions:**
- `notify(message, priority, actions?)` - Show notification
- `action(toast_id, action_id)` - Handle action button click
- `dismiss(toast_id)` - Close notification

---

### 2.8 IdeaList

Dashboard for viewing all ideas.

**State:**
- `ideas`: List of ideas (owned + shared)
- `objectives`: List of objectives
- `filters`: Active filter criteria

**Actions:**
- `load()` - Load ideas and objectives
- `filter(criteria)` - Apply filters
- `refresh()` - Reload from server

---

## 3. Specialized Agents

All agents require user approval before taking actions. Suggestions are stored in Sessions.

### 3.1 SummaryAgent

Helps articulate the idea clearly in Summary.md.

**Purpose:** Coach users to write a clear, concise, compelling summary.

**Actions:**
- `coach(idea_id, content)` - Provide guidance on improving the summary
- `evaluate(idea_id, content)` - Assess quality against criteria
- `suggest(idea_id)` - Offer specific improvements
- `isComplete(idea_id, content)` - Determine if summary meets completion criteria

**Completion Criteria:**
- Clear: Reader understands the idea immediately
- Concise: No unnecessary detail
- Compelling: Creates interest

---

### 3.2 ChallengeAgent

Helps define the problem space in Challenge.md.

**Purpose:** Coach users to articulate a specific, measurable, significant challenge.

**Actions:**
- `coach(idea_id, content)` - Provide guidance on problem definition
- `evaluate(idea_id, content)` - Assess quality against criteria
- `suggest(idea_id)` - Offer specific improvements
- `isComplete(idea_id, content)` - Determine if challenge meets completion criteria

**Completion Criteria:**
- Specific: Not vague or overly broad
- Measurable: Can determine if it's solved
- Significant: Worth solving

---

### 3.3 ApproachAgent

Helps design how to solve the challenge in Approach.md.

**Purpose:** Coach users to develop a feasible, differentiated approach.

**Actions:**
- `coach(idea_id, content)` - Provide guidance on approach design
- `evaluate(idea_id, content)` - Assess quality against criteria
- `suggest(idea_id)` - Offer specific improvements
- `isComplete(idea_id, content)` - Determine if approach meets completion criteria

**Completion Criteria:**
- Feasible: Can actually be implemented
- Differentiated: Not just the obvious solution
- Addresses Challenge: Actually solves the stated problem

---

### 3.4 StepsAgent

Helps break down into actionable steps in CoherentSteps.md.

**Purpose:** Coach users to create concrete, sequenced, assignable next steps.

**Actions:**
- `coach(idea_id, content)` - Provide guidance on step definition
- `evaluate(idea_id, content)` - Assess quality against criteria
- `suggest(idea_id)` - Offer specific improvements
- `isComplete(idea_id, content)` - Determine if steps meet completion criteria

**Completion Criteria:**
- Concrete: Specific actions, not vague intentions
- Sequenced: Clear order of operations
- Assignable: Someone could take ownership

---

### 3.5 CoherenceAgent

Cross-cutting agent that checks logical consistency across all kernel files.

**Purpose:** Ensure the four kernel files tell a consistent, coherent story.

**Actions:**
- `evaluate(idea_id)` - Check consistency across all kernel files
- `findGaps(idea_id)` - Identify logical disconnects
- `suggest(idea_id)` - Recommend which file to revise
- `suggestObjective(idea_id)` - Recommend objective based on content

**Checks:**
- Does Approach address Challenge?
- Are Steps implementing the Approach?
- Does Summary capture the essence of Challenge + Approach + Steps?
- Will completing Steps actually solve the Challenge?

**Trigger:** Runs when 2+ kernel files are marked complete, and re-runs on subsequent updates.

---

### 3.6 ContextAgent

Extracts insights from uploaded context files.

**Purpose:** Mine uploaded documents for insights that strengthen kernel files.

**Actions:**
- `extract(idea_id, context_file_id)` - Pull out relevant insights
- `summarize(context_file_id)` - Generate summary of uploaded file
- `mapToKernel(insight)` - Identify which kernel file an insight relates to

**Trigger:** Runs when a context file is uploaded.

**Output:** Suggestions like "I found something in 'customer_interview.md' relevant to your Challenge. Would you like to incorporate this?"

---

### 3.7 ObjectiveAgent

Helps define objectives and shows alignment with linked ideas.

**Purpose:** Coach objective definition and summarize idea alignment.

**Actions:**
- `coach(objective_id, content)` - Provide guidance on objective definition
- `summarizeAlignment(objective_id)` - Show how linked ideas support the objective
- `suggest(objective_id)` - Offer improvements

---

## 4. Graph Database Schema

The graph is internal (not visible to users) and powers agent intelligence. MVP uses minimal schema.

### 4.1 Nodes

| Node Type | Key Properties | Notes |
|-----------|----------------|-------|
| **Idea** | id, title, status, org_id | Core entity |
| **Objective** | id, title, timeframe, status, org_id | Flat structure |
| **User** | id, name, org_id, role | Identity |
| **Organization** | id, name | Multi-tenant root |

### 4.2 Relationships (MVP)

| Relationship | From | To | Properties | Notes |
|--------------|------|-----|------------|-------|
| **SUPPORTS** | Idea | Objective | created_at | Optional: can be attached later |
| **CREATED** | User | Idea | created_at | Immutable |
| **COLLABORATES_ON** | User | Idea | role, added_at | Mutable |
| **OWNS** | User | Objective | assigned_at | Accountability |
| **MEMBER_OF** | User | Organization | role, joined_at | Org membership |

---

## 5. Synchronizations

Synchronizations define how concepts interact. They are declarative rules, not buried logic.

### 5.1 Idea Lifecycle

```
sync IdeaCreated:
    when Idea.create(org_id, user_id, title, objective_id?):
        → KernelFile.initializeAll(idea_id)      # Create 4 empty kernel files
        → Version.initialize(idea_id)             # Create JJ repo
        → if objective_id: Graph.connect(idea_id, objective_id, "SUPPORTS")
        → Session.create(idea_id, user_id, "coherence")  # Start coherence agent session

sync IdeaLinkedToObjective:
    when Idea.update(idea_id, objective_id):     # When objective is attached later
        → Graph.connect(idea_id, objective_id, "SUPPORTS")

sync IdeaArchived:
    when Idea.archive(idea_id):
        → Version.commit(idea_id, "archived")
        # Graph edges preserved for historical analysis
```

### 5.2 Kernel File Updates

```
sync KernelFileUpdated:
    when KernelFile.update(idea_id, file_type, content):
        → Version.commit(idea_id, file_type, content)
        → embedding = Embedding.generate(content)
        → KernelFile.setEmbedding(idea_id, file_type, embedding)
        → agent = getAgentForFileType(file_type)
        → agent.evaluate(idea_id, content)        # May mark complete

sync KernelFileMarkedComplete:
    when KernelFile.markComplete(idea_id, file_type):
        → count = KernelFile.getCompletionCount(idea_id)
        → if count >= 2: CoherenceAgent.evaluate(idea_id)
```

### 5.3 Context Files

```
sync ContextFileAdded:
    when ContextFile.create(idea_id, content, filename):
        → insights = ContextAgent.extract(idea_id, content)
        → for insight in insights:
            → Session.addMessage(idea_id, "agent", insight.suggestion)
```

### 5.4 Sessions

```
sync SessionResumed:
    when Chat.loadSession(session_id):
        → history = Session.getHistory(session_id)
        → Chat.display(history)

sync AgentSuggestionMade:
    when Agent.suggest(idea_id, suggestion):
        → Session.addMessage(idea_id, "agent", suggestion.content)
        → Chat.display(suggestion)
```

### 5.5 Collaboration

```
sync CollaboratorAdded:
    when Collab.invite(idea_id, user_id, role):
        → Toast.notify(user_id, "You've been invited to collaborate")
```

---

## 6. Design Decisions

These decisions were made to simplify implementation and align with product goals.

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Simultaneous edits** | Last-write-wins | Avoid complex real-time collaboration; JJ handles versioning |
| **Agent autonomy** | Always requires user approval | Trust and control; agents suggest, users decide |
| **Suggestion persistence** | Stored in Session | Suggestions are conversational context |
| **Graph visibility** | Internal only | Powers agent intelligence; users see results, not raw graph |
| **Kernel completion** | Determined by agents | Quality-based, not length-based or user-declared |
| **Objectives** | Flat structure, admin-created | Simplified model; no hierarchy for MVP |
| **File embeddings** | Kernel files only for MVP | Enables future similarity search |

---

## 7. Deferred to Later Phases

The following concepts and capabilities are intentionally deferred:

| Concept/Feature | Phase | Notes |
|-----------------|-------|-------|
| **Search** | Phase 2 | Semantic search across ideas using embeddings |
| **ConnectionAgent** | Phase 2 | Discover relationships between ideas |
| **Graph traversal** | Phase 2 | SIMILAR_CHALLENGE, COMPLEMENTARY_APPROACH relationships |
| **Notification** | Phase 2 | Email digests, push notifications |
| **Objective hierarchy** | Future | Parent/child objectives (OKR-style) |
| **Context file embeddings** | Phase 2 | RAG for context files |

---

## Appendix: Agent-to-File Mapping

| Agent | File/Screen | Completion Criteria |
|-------|-------------|---------------------|
| SummaryAgent | Summary.md | Clear, concise, compelling |
| ChallengeAgent | Challenge.md | Specific, measurable, significant |
| ApproachAgent | Approach.md | Feasible, differentiated, addresses challenge |
| StepsAgent | CoherentSteps.md | Concrete, sequenced, assignable |
| CoherenceAgent | Idea Workspace | Cross-file logical consistency |
| ContextAgent | Context files | Extracts insights from uploads |
| ObjectiveAgent | Objective Workspace | Clear success criteria, alignment |

---

*Document version: 0.2.0*
*Last updated: 2025-12-31*
