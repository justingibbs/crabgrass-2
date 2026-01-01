# Crabgrass: Concepts & Synchronizations

**Version:** 0.1.0
**Date:** 2025-12-31
**Architecture Pattern:** Concepts and Synchronizations (Jackson, MIT 2025)

---

## Overview

This document defines the modular architecture for Crabgrass using the **Concepts and Synchronizations** pattern. This approach separates:

- **Concepts**: Self-contained, independent units of functionality with clear purpose, state, and actions
- **Synchronizations**: Explicit rules defining how concepts interact without coupling them

The goal is legibility—developers should be able to read the system "like a book" where concepts map to familiar phenomena and synchronizations represent intuition about how they interact.

---

## Table of Contents

1. [Backend Concepts](#1-backend-concepts)
2. [Frontend Concepts](#2-frontend-concepts)
3. [Specialized Agents](#3-specialized-agents)
4. [Graph Database Schema](#4-graph-database-schema)
5. [Synchronizations](#5-synchronizations)
6. [Design Decisions](#6-design-decisions)

---

## 1. Backend Concepts

### 1.1 Idea

The core project container in Crabgrass. An idea progresses through lifecycle stages toward innovation.

**State:**
- `id`: Unique identifier
- `org_id`: Organization this idea belongs to
- `creator_id`: User who created it
- `title`: Display name
- `status`: draft | active | connected | innovation | archived
- `kernel_completion`: Count of completed kernel files (0-4)
- `jj_repo_path`: Path to JJ version control repository
- `created_at`, `updated_at`: Timestamps

**Actions:**
- `create(org_id, user_id, title, objective_id)` - Create new idea linked to an objective
- `update(idea_id, fields)` - Update metadata
- `archive(idea_id)` - Soft delete
- `getStatus(idea_id)` - Get current lifecycle status
- `listAll(org_id, user_id, filters)` - List ideas user can access
- `linkObjective(idea_id, objective_id)` - Connect idea to additional objective

**Constraints:**
- Every idea MUST be linked to at least one Objective
- Ideas belong to exactly one Organization
- Status transitions follow lifecycle rules (draft → active → connected → innovation)

---

### 1.2 Objective

Org-wide strategic objectives that ideas connect to. Hierarchical (OKR-style).

**State:**
- `id`: Unique identifier
- `org_id`: Organization this belongs to
- `parent_id`: Parent objective (for hierarchy), null if top-level
- `title`: Display name
- `description`: Detailed description
- `owner_id`: User accountable for this objective
- `timeframe`: Q1 2025, FY25, H1 2025, etc.
- `status`: active | achieved | deprecated
- `created_at`, `created_by`: Timestamps and creator

**Actions:**
- `create(org_id, title, description, owner_id, parent_id?)` - Admin only
- `update(objective_id, fields)` - Admin only
- `archive(objective_id)` - Admin only
- `setParent(objective_id, parent_id)` - Admin only
- `list(org_id)` - All users, flat list
- `getTree(org_id)` - All users, hierarchical view
- `getChildren(objective_id)` - Get sub-objectives
- `getIdeas(objective_id)` - Get ideas supporting this objective

**Constraints:**
- Only org admins can create/update/archive
- All org members can view and link ideas to objectives
- Archiving does NOT cascade to children (reassigns to grandparent or orphans)

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
- `embedding`: Vector embedding (768 dimensions for Gemini)
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
- Synced to vector database for similarity search

---

### 1.4 ContextFile

Optional supporting materials uploaded by users or created by agents.

**State:**
- `id`: Unique identifier
- `idea_id`: Parent idea
- `filename`: Display name
- `content`: File content (text extracted if PDF, etc.)
- `mime_type`: File type
- `embedding`: Vector embedding
- `created_by`: User ID or null if agent-created
- `created_by_agent`: Boolean
- `created_at`: Timestamp

**Actions:**
- `create(idea_id, filename, content, mime_type, user_id?)` - Upload file
- `read(idea_id, file_id)` - Get content
- `delete(idea_id, file_id)` - Remove file
- `list(idea_id)` - List all context files
- `setEmbedding(file_id, embedding)` - Store vector

**Constraints:**
- Can be deleted (unlike kernel files)
- Not indexed in graph database directly (but embeddings stored for RAG)
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
- `branch(idea_id, branch_name)` - Create exploration branch
- `merge(idea_id, branch_name)` - Merge branch back
- `undo(idea_id)` - Revert last operation

**Constraints:**
- One repository per idea
- Conflict-free by design (last-write-wins for simultaneous edits)
- Operations logged for full auditability

---

### 1.6 Search

Vector similarity search using embeddings.

**State:**
- Embeddings stored in DuckDB VSS extension

**Actions:**
- `findSimilar(embedding, file_type?, threshold)` - Find similar content
- `query(org_id, text_query)` - Semantic search across ideas
- `reindex(idea_id)` - Regenerate all embeddings for an idea

**Constraints:**
- Scoped to organization (cross-org search not allowed)
- Only kernel files are indexed (context files have embeddings but for RAG only)

---

### 1.7 Graph

Relationship storage and traversal using DuckPGQ.

**State:**
- Property graph with nodes and edges (see Section 4)

**Actions:**
- `connect(source_id, target_id, relationship_type, properties)` - Create edge
- `disconnect(source_id, target_id, relationship_type)` - Remove edge
- `traverse(start_id, relationship_types, depth)` - Graph traversal
- `getConnections(idea_id)` - Get all relationships for an idea

**Constraints:**
- Scoped to organization
- Not directly visible to users (internal for agent intelligence)
- Edges have properties (strength, created_by, timestamps)

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
- `activity(user_id)` - Get recent activity

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
- `role`: owner | editor | viewer
- `added_at`: Timestamp

**Actions:**
- `invite(idea_id, user_id, role)` - Add collaborator
- `updateRole(idea_id, user_id, role)` - Change permission level
- `remove(idea_id, user_id)` - Remove access
- `listCollaborators(idea_id)` - Get all collaborators

**Constraints:**
- Owner cannot be removed (transfer ownership instead)
- Viewers can read but not edit

---

### 1.11 Session

Persistent conversation threads with agents (like Claude Projects).

**State:**
- `id`: Unique identifier
- `idea_id`: Parent idea
- `user_id`: Who started it
- `title`: Auto-generated or user-set
- `messages`: List of conversation messages
- `created_at`, `last_active`: Timestamps

**Actions:**
- `create(idea_id, user_id)` - Start new conversation
- `addMessage(session_id, role, content)` - Add to history
- `getHistory(session_id, limit?)` - Load conversation
- `rename(session_id, title)` - Update title
- `list(idea_id)` - All sessions for an idea
- `resume(session_id)` - Load previous conversation

**Constraints:**
- Sessions belong to one idea
- Messages are ephemeral for agent suggestions (not permanently stored beyond session)

---

### 1.12 Embedding

Vector generation for files.

**Actions:**
- `generate(content)` - Create embedding vector (768 dimensions for Gemini)

**Constraints:**
- Uses Gemini embedding model
- All kernel and context files get embeddings

---

### 1.13 Notification

Backend notification management.

**State:**
- `id`: Unique identifier
- `user_id`: Recipient
- `type`: idea_created | idea_linked | invited_to_idea | connection_suggested | etc.
- `priority`: high | medium | low
- `content`: JSON payload
- `read`: Boolean
- `created_at`: Timestamp

**Actions:**
- `create(user_id, type, priority, content)` - Create notification
- `markRead(notification_id)` - Mark as read
- `listPending(user_id)` - Get unread notifications
- `digest(user_id)` - Generate email digest

---

## 2. Frontend Concepts

### 2.1 Canvas

Markdown rendering and editing surface.

**State:**
- `content`: Current markdown content
- `isDirty`: Has unsaved changes
- `isEditing`: Edit mode vs preview mode

**Actions:**
- `render(content)` - Display markdown
- `edit()` - Enter edit mode
- `save()` - Persist changes
- `preview()` - Toggle preview mode

---

### 2.2 Editor

Text manipulation within canvas.

**State:**
- `cursorPosition`: Current cursor location
- `selection`: Selected text range
- `undoStack`, `redoStack`: Edit history

**Actions:**
- `load(content)` - Initialize with content
- `insertText(text, position)` - Add text
- `deleteText(start, end)` - Remove text
- `undo()` - Revert last change
- `redo()` - Restore reverted change
- `getCursor()` - Get cursor position

---

### 2.3 Chat

Agent conversation display.

**State:**
- `messages`: List of displayed messages
- `isStreaming`: Agent response in progress
- `pendingMessage`: User input being composed

**Actions:**
- `send(message)` - Send user message
- `receive(message)` - Display agent message
- `stream(chunk)` - Append streaming response
- `clear()` - Clear conversation display
- `loadHistory(messages)` - Restore previous session

---

### 2.4 Session (Frontend)

Session picker and history management.

**State:**
- `currentSession`: Active session
- `sessionList`: Available sessions for current idea
- `isLoading`: Loading state

**Actions:**
- `load(session_id)` - Resume previous conversation
- `create()` - Start new session
- `switchTo(session_id)` - Change active session
- `listAll(idea_id)` - Show session picker
- `rename(session_id, title)` - Edit session title

---

### 2.5 FileTree

File navigation for kernel and context files.

**State:**
- `files`: List of files
- `selectedFile`: Currently selected
- `expandedFolders`: UI state

**Actions:**
- `list(idea_id)` - Load file list
- `select(file_id)` - Select file for editing
- `organize()` - Rearrange (context files only)
- `filter(criteria)` - Filter displayed files

---

### 2.6 KernelStatus

Progress tracking for kernel file completion.

**State:**
- `completion`: Count of completed files (0-4)
- `fileStatuses`: Per-file completion state

**Actions:**
- `refresh(idea_id)` - Reload status
- `navigate(file_type)` - Go to specific kernel file
- `getProgress()` - Get completion percentage

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
- `ideas`: List of ideas
- `filters`: Active filter criteria
- `sortField`, `sortDirection`: Sort state

**Actions:**
- `list(filters?)` - Load ideas
- `filter(criteria)` - Apply filters
- `sort(field, direction)` - Change sort order
- `refresh()` - Reload from server

---

### 2.9 ObjectiveTree

Hierarchical view of organizational objectives.

**State:**
- `objectives`: Tree structure of objectives
- `expandedNodes`: UI state
- `selectedObjective`: Currently selected

**Actions:**
- `load(org_id)` - Load objective tree
- `expand(objective_id)` - Show children
- `collapse(objective_id)` - Hide children
- `select(objective_id)` - Select for linking

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

**Checks:**
- Does Approach address Challenge?
- Are Steps implementing the Approach?
- Does Summary capture the essence of Challenge + Approach + Steps?
- Will completing Steps actually solve the Challenge?

**Trigger:** Runs when 2+ kernel files are marked complete, and re-runs on subsequent updates.

---

### 3.6 ConnectionAgent

Finds related ideas across the organization.

**Purpose:** Discover connections between ideas to enable collaboration and avoid duplication.

**Actions:**
- `discover(idea_id)` - Find related ideas using embeddings and graph
- `explain(idea_id, target_id)` - Generate explanation of relationship
- `recommend(idea_id)` - Suggest connections for user approval

**Relationship Types Discovered:**
- Similar Challenge: Ideas addressing related problems
- Complementary Approach: Ideas that could combine
- Contradictory: Ideas with conflicting assumptions
- Builds On: Ideas that extend others

**Trigger:** Runs when all 4 kernel files are complete.

**Constraint:** Always suggests to user; never auto-creates connections.

---

### 3.7 ContextAgent

Extracts insights from uploaded context files.

**Purpose:** Mine uploaded documents for insights that strengthen kernel files.

**Actions:**
- `extract(idea_id, context_file_id)` - Pull out relevant insights
- `summarize(context_file_id)` - Generate summary of uploaded file
- `mapToKernel(insight)` - Identify which kernel file an insight relates to

**Trigger:** Runs when a context file is uploaded.

**Output:** Suggestions like "I found something in 'customer_interview.md' relevant to your Challenge: [quote]. Would you like to incorporate this?"

---

## 4. Graph Database Schema

The graph is internal (not visible to users) and powers agent intelligence.

### 4.1 Nodes

| Node Type | Key Properties | Notes |
|-----------|----------------|-------|
| **Idea** | id, title, status, org_id, kernel_completion | Core entity |
| **Objective** | id, title, timeframe, status, org_id, parent_id | Hierarchical |
| **User** | id, name, org_id, role | Identity |
| **Organization** | id, name | Multi-tenant root |
| **KernelFile** | id, idea_id, file_type, is_complete, embedding | With vector |
| **ContextFile** | id, idea_id, filename, embedding | With vector |

### 4.2 Relationships

#### Idea Relationships

| Relationship | From | To | Properties | Notes |
|--------------|------|-----|------------|-------|
| **SUPPORTS** | Idea | Objective | strength, created_at, created_by | Required: every idea must have at least one |
| **SIMILAR_CHALLENGE** | Idea | Idea | similarity (0-1), discovered_at | Computed from Challenge embeddings |
| **COMPLEMENTARY_APPROACH** | Idea | Idea | compatibility (0-1), explanation | Approaches that could combine |
| **CONTRADICTS** | Idea | Idea | tension_type, explanation | Conflicting assumptions |
| **BUILDS_ON** | Idea | Idea | relationship, created_by | User-declared extension |

#### User Relationships

| Relationship | From | To | Properties | Notes |
|--------------|------|-----|------------|-------|
| **CREATED** | User | Idea | created_at | Immutable |
| **COLLABORATES_ON** | User | Idea | role (owner/editor/viewer), added_at | Mutable |
| **OWNS** | User | Objective | assigned_at | Accountability |
| **MEMBER_OF** | User | Organization | role, joined_at | Org membership |

#### Objective Relationships

| Relationship | From | To | Properties | Notes |
|--------------|------|-----|------------|-------|
| **PARENT_OF** | Objective | Objective | created_at | Creates OKR-style hierarchy |

#### File Relationships

| Relationship | From | To | Properties | Notes |
|--------------|------|-----|------------|-------|
| **BELONGS_TO** | KernelFile | Idea | file_type | Ownership |
| **BELONGS_TO** | ContextFile | Idea | uploaded_at | Ownership |
| **SIMILAR_CONTENT** | KernelFile | KernelFile | similarity (0-1) | Cross-idea, same file_type |
| **INFORMS** | ContextFile | KernelFile | relevance (0-1), extracted_insights | Created by ContextAgent |

---

## 5. Synchronizations

Synchronizations define how concepts interact. They are declarative rules, not buried logic.

### 5.1 Idea Lifecycle

```
sync IdeaCreated:
    when Idea.create(org_id, user_id, title, objective_id):
        → KernelFile.initializeAll(idea_id)      # Create 4 empty kernel files
        → Version.initialize(idea_id)             # Create JJ repo
        → Graph.connect(idea_id, objective_id, "SUPPORTS")
        → Session.create(idea_id, user_id)        # Start first conversation

sync IdeaObjectiveLinked:
    when Idea.linkObjective(idea_id, objective_id):
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
        → if count == 4: ConnectionAgent.discover(idea_id)
```

### 5.3 Similarity & Connections

```
sync SimilarityComputed:
    when Embedding.generate(idea_id, file_type, embedding):
        → similar = Search.findSimilar(embedding, file_type, threshold=0.75)
        → for match in similar where match.idea_id != idea_id:
            → Graph.connect(idea_id, match.idea_id, "SIMILAR_CONTENT", similarity=match.score)
            → if file_type == "challenge":
                → Graph.connect(idea_id, match.idea_id, "SIMILAR_CHALLENGE", similarity=match.score)

sync ConnectionDiscovered:
    when ConnectionAgent.discover(idea_id):
        → connections = ConnectionAgent.getPendingConnections(idea_id)
        → for conn in connections:
            → Session.addMessage(idea_id, "agent", suggestion)
            # User must approve; agent never auto-creates user-facing connections

sync ConnectionApproved:
    when User.approveConnection(idea_id, target_id, connection_type):
        → Graph.connect(idea_id, target_id, connection_type, created_by="user")
```

### 5.4 Context Files

```
sync ContextFileAdded:
    when ContextFile.create(idea_id, content, filename):
        → embedding = Embedding.generate(content)
        → ContextFile.setEmbedding(file_id, embedding)
        → insights = ContextAgent.extract(idea_id, content)
        → for insight in insights:
            → Graph.connect(context_file_id, insight.kernel_file_id, "INFORMS", relevance=insight.relevance)
            → Session.addMessage(idea_id, "agent", insight.suggestion)
```

### 5.5 Sessions

```
sync SessionResumed:
    when Session.resume(session_id):
        → history = Session.getHistory(session_id)
        → Chat.loadHistory(history)

sync AgentSuggestionMade:
    when Agent.suggest(idea_id, suggestion):
        → Session.addMessage(idea_id, "agent", suggestion.content)
        → Chat.display(suggestion)
        # All suggestions stored in session for context
```

### 5.6 Objectives

```
sync ObjectiveCreated:
    when Objective.create(org_id, title, parent_id?):
        → if parent_id: Graph.connect(parent_id, objective_id, "PARENT_OF")

sync ObjectiveArchived:
    when Objective.archive(objective_id):
        → children = Objective.getChildren(objective_id)
        → grandparent = Objective.getParent(objective_id)
        → for child in children:
            → Objective.setParent(child.id, grandparent)  # Reassign to grandparent or orphan
```

### 5.7 Collaboration

```
sync CollaboratorAdded:
    when Collab.invite(idea_id, user_id, role):
        → Notification.create(user_id, "invited_to_idea", idea_id)
```

### 5.8 Notifications

```
sync HighPriorityNotification:
    when Notification.create(user_id, type, priority="high", content):
        → Toast.notify(content, priority, actions)

sync ObjectiveOwnerNotified:
    when Idea.linkObjective(idea_id, objective_id):
        → owner = Objective.getOwner(objective_id)
        → Notification.create(owner, "idea_linked", {idea_id, objective_id})
```

---

## 6. Design Decisions

These decisions were made to simplify implementation and align with product goals.

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Simultaneous edits** | Last-write-wins | Avoid complex real-time collaboration; JJ handles versioning |
| **Agent autonomy** | Always requires user approval | Trust and control; agents suggest, users decide |
| **Suggestion persistence** | Ephemeral (stored in Session) | Suggestions are conversational, not permanent records |
| **Graph visibility** | Internal only | Powers agent intelligence; users see results, not raw graph |
| **Kernel completion** | Determined by agents | Quality-based, not length-based or user-declared |
| **Objectives** | Org-wide, hierarchical, admin-created | Ensures strategic alignment; no personal objectives |
| **File embeddings** | All files get embeddings | Enables RAG for context files, similarity for kernel files |

---

## Appendix: Agent-to-File Mapping

| Agent | Kernel File | Completion Criteria |
|-------|-------------|---------------------|
| SummaryAgent | Summary.md | Clear, concise, compelling |
| ChallengeAgent | Challenge.md | Specific, measurable, significant |
| ApproachAgent | Approach.md | Feasible, differentiated, addresses challenge |
| StepsAgent | CoherentSteps.md | Concrete, sequenced, assignable |
| CoherenceAgent | (all files) | Cross-file logical consistency |
| ConnectionAgent | (none) | Discovers related ideas |
| ContextAgent | (none) | Extracts insights from uploads |

---

*Document version: 0.1.0*
*Last updated: 2025-12-31*
