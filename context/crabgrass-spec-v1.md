# Crabgrass: Product Specification

**Version:** 0.1.0-draft  
**Date:** 2025-12-31  
**Status:** Initial Specification

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
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│   │  Draft   │───▶│  Active  │───▶│ Connected│───▶│Innovation│ │
│   │          │    │          │    │          │    │          │ │
│   │ 0-1 files│    │ 2-3 files│    │ 4 files  │    │ Executed │ │
│   │ complete │    │ complete │    │ + links  │    │          │ │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│        │                │               │               │       │
│        ▼                ▼               ▼               ▼       │
│   Agent nudges    Agent coaches   Agent connects  Agent tracks │
│   to start        for quality     across org      outcomes     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Organizational Graph

Ideas exist in a graph of relationships:

- **Similar Challenge**: Ideas addressing related problems
- **Complementary Approach**: Ideas that could combine
- **Contradictory Assumptions**: Ideas with conflicting premises
- **Same Strategic Vector**: Ideas aligned to same objective
- **Shared Collaborators**: Ideas with overlapping teams

---

## 3. Architecture

### 3.1 Design Philosophy: Concepts and Synchronizations

Crabgrass follows the Concepts and Synchronizations model (Jackson, MIT 2025) for both backend and frontend:

**Concepts** are independent, self-contained units of functionality with:
- Clear purpose
- Defined state
- Explicit actions
- Observable behavior

**Synchronizations** coordinate concepts without coupling them.

### 3.2 Backend Concepts

```
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND CONCEPTS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Idea     │  │    File     │  │   Version   │             │
│  │   Concept   │  │   Concept   │  │   Concept   │             │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤             │
│  │ create()    │  │ create()    │  │ commit()    │             │
│  │ archive()   │  │ read()      │  │ history()   │             │
│  │ getStatus() │  │ update()    │  │ branch()    │             │
│  │ listAll()   │  │ delete()    │  │ merge()     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Agent     │  │   Search    │  │    Graph    │             │
│  │   Concept   │  │   Concept   │  │   Concept   │             │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤             │
│  │ analyze()   │  │ similar()   │  │ connect()   │             │
│  │ suggest()   │  │ query()     │  │ traverse()  │             │
│  │ notify()    │  │ embed()     │  │ recommend() │             │
│  │ act()       │  │ reindex()   │  │ visualize() │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │    User     │  │   Collab    │                              │
│  │   Concept   │  │   Concept   │                              │
│  ├─────────────┤  ├─────────────┤                              │
│  │ authenticate│  │ invite()    │                              │
│  │ preferences │  │ share()     │                              │
│  │ activity()  │  │ comment()   │                              │
│  └─────────────┘  └─────────────┘                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Frontend Concepts

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND CONCEPTS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Canvas    │  │    Chat     │  │  FileTree   │             │
│  │   Concept   │  │   Concept   │  │   Concept   │             │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤             │
│  │ render()    │  │ send()      │  │ list()      │             │
│  │ edit()      │  │ receive()   │  │ select()    │             │
│  │ save()      │  │ stream()    │  │ organize()  │             │
│  │ history()   │  │ clear()     │  │ filter()    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Kernel    │  │ Connection  │  │   Toast     │             │
│  │   Status    │  │   Panel     │  │   Concept   │             │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤             │
│  │ progress()  │  │ show()      │  │ notify()    │             │
│  │ navigate()  │  │ preview()   │  │ action()    │             │
│  │ validate()  │  │ link()      │  │ dismiss()   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Key Synchronizations

```python
# Example: File saved triggers re-indexing and agent analysis
sync FileUpdated:
    when File.update(idea_id, file_type, content):
        if file_type in KERNEL_FILES:
            Search.embed(idea_id, file_type, content)
            Graph.connect(idea_id)
            Agent.analyze(idea_id)

# Example: Agent suggestion triggers notification
sync AgentSuggestion:
    when Agent.suggest(idea_id, suggestion):
        Toast.notify(idea_id, suggestion)
        if suggestion.involves_other_user:
            Collab.notify(suggestion.other_user_id)

# Example: Similar ideas found triggers connection panel
sync SimilarityFound:
    when Search.similar(idea_id) returns matches:
        if matches.score > THRESHOLD:
            ConnectionPanel.show(idea_id, matches)
            Agent.notify(idea_id, "found_similar", matches)
```

### 3.5 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 CLIENT                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Vanilla JS + AG-UI Protocol                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │  Canvas  │  │   Chat   │  │ FileTree │  │  Kernel  │            │   │
│  │  │          │  │          │  │          │  │  Status  │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    │ SSE + REST                             │
│                                    ▼                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                 SERVER                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     FastAPI + Google ADK                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │   Idea   │  │   File   │  │  Agent   │  │  Search  │            │   │
│  │  │ Concept  │  │ Concept  │  │ Concept  │  │ Concept  │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                 ┌──────────────────┼──────────────────┐                    │
│                 ▼                  ▼                  ▼                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │     DuckDB      │  │       JJ        │  │     Gemini      │           │
│  │  ┌───────────┐  │  │  (Version Ctrl) │  │   (LLM + Emb)   │           │
│  │  │  Tables   │  │  │                 │  │                 │           │
│  │  ├───────────┤  │  │  - Commits      │  │  - Analysis     │           │
│  │  │  VSS Ext  │  │  │  - Branches     │  │  - Suggestions  │           │
│  │  │  (Vector) │  │  │  - Operations   │  │  - Embeddings   │           │
│  │  ├───────────┤  │  │                 │  │                 │           │
│  │  │  DuckPGQ  │  │  │                 │  │                 │           │
│  │  │  (Graph)  │  │  │                 │  │                 │           │
│  │  └───────────┘  │  │                 │  │                 │           │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘           │
│                                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

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

-- Ideas (Projects)
CREATE TABLE ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    creator_id UUID REFERENCES users(id),
    title VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'draft', -- draft, active, connected, innovation, archived
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
    role VARCHAR DEFAULT 'editor', -- 'owner', 'editor', 'viewer'
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (idea_id, user_id)
);

-- Agent Interactions
CREATE TABLE agent_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id UUID REFERENCES ideas(id),
    user_id UUID REFERENCES users(id),
    interaction_type VARCHAR, -- 'suggestion', 'analysis', 'connection', 'nudge'
    content JSON,
    user_response VARCHAR, -- 'accepted', 'rejected', 'ignored', NULL
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

### 4.3 Graph Storage (DuckPGQ)

```sql
-- Graph schema for idea relationships
CREATE PROPERTY GRAPH idea_graph
VERTEX TABLES (
    ideas,
    users
)
EDGE TABLES (
    idea_connections SOURCE KEY (source_idea_id) REFERENCES ideas(id)
                     DESTINATION KEY (target_idea_id) REFERENCES ideas(id),
    idea_collaborators SOURCE KEY (idea_id) REFERENCES ideas(id)
                       DESTINATION KEY (user_id) REFERENCES users(id)
);

-- Idea connections (edges)
CREATE TABLE idea_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_idea_id UUID REFERENCES ideas(id),
    target_idea_id UUID REFERENCES ideas(id),
    connection_type VARCHAR, -- 'similar_challenge', 'complementary_approach', 
                             -- 'contradictory', 'same_vector', 'user_linked'
    strength FLOAT, -- 0.0 to 1.0, computed from embeddings or explicit
    discovered_by VARCHAR, -- 'agent', 'user'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_idea_id, target_idea_id, connection_type)
);

-- Example graph traversal (find ideas 2 hops away)
-- FROM GRAPH_TABLE (idea_graph
--     MATCH (i1:ideas)-[c:idea_connections]->(i2:ideas)-[c2:idea_connections]->(i3:ideas)
--     WHERE i1.id = $idea_id
--     COLUMNS (i3.id, i3.title, c.connection_type, c2.connection_type)
-- )
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

The Crabgrass agent is **proactive, not reactive**. It doesn't wait for user requests—it actively pushes ideas toward innovation.

**Posture:** Coach, not assistant. Sparring partner, not oracle.

### 5.2 Agent Behaviors

#### 5.2.1 Completion Nudging

Triggers when kernel files are incomplete:

```python
class CompletionNudgeAgent:
    """Nudges users to complete kernel files."""
    
    def analyze(self, idea: Idea) -> Optional[Nudge]:
        incomplete = [f for f in idea.kernel_files if not f.is_complete]
        
        if not incomplete:
            return None
            
        # Prioritize in order: Summary → Challenge → Approach → Steps
        priority_order = ['summary', 'challenge', 'approach', 'coherent_steps']
        next_file = min(incomplete, key=lambda f: priority_order.index(f.file_type))
        
        return Nudge(
            type='completion',
            target=next_file.file_type,
            message=self.generate_nudge_message(idea, next_file)
        )
```

#### 5.2.2 Coherence Checking

Validates that kernel files are logically consistent:

```python
class CoherenceAgent:
    """Checks logical consistency across kernel files."""
    
    async def analyze(self, idea: Idea) -> Optional[Suggestion]:
        # Check: Does Approach address Challenge?
        if idea.challenge.is_complete and idea.approach.is_complete:
            coherence = await self.llm.evaluate_coherence(
                challenge=idea.challenge.content,
                approach=idea.approach.content
            )
            
            if coherence.score < 0.7:
                return Suggestion(
                    type='coherence',
                    message=f"Your Approach may not fully address your Challenge. {coherence.explanation}",
                    action='edit_approach'
                )
        
        # Check: Are Steps concrete enough?
        # Check: Does Summary capture the essence?
        # ... etc
```

#### 5.2.3 Quality Coaching

Pushes for substantive, actionable content:

```python
class QualityAgent:
    """Coaches users toward higher quality kernel files."""
    
    QUALITY_CRITERIA = {
        'summary': ['clear', 'concise', 'compelling'],
        'challenge': ['specific', 'measurable', 'significant'],
        'approach': ['feasible', 'differentiated', 'addresses_challenge'],
        'coherent_steps': ['concrete', 'sequenced', 'assignable']
    }
    
    async def analyze(self, idea: Idea, file_type: str) -> Optional[Suggestion]:
        content = idea.get_kernel_file(file_type).content
        
        evaluation = await self.llm.evaluate_quality(
            content=content,
            file_type=file_type,
            criteria=self.QUALITY_CRITERIA[file_type]
        )
        
        if evaluation.weakest_criterion:
            return Suggestion(
                type='quality',
                message=evaluation.improvement_suggestion,
                action='edit',
                target=file_type
            )
```

#### 5.2.4 Connection Discovery

Finds related ideas across the organization:

```python
class ConnectionAgent:
    """Discovers connections between ideas across the organization."""
    
    async def analyze(self, idea: Idea) -> List[Connection]:
        connections = []
        
        # Find similar challenges
        similar = await self.search.find_similar(
            idea_id=idea.id,
            file_type='challenge',
            threshold=0.75
        )
        
        for match in similar:
            if match.idea_id != idea.id:
                connections.append(Connection(
                    type='similar_challenge',
                    target_idea_id=match.idea_id,
                    strength=match.similarity,
                    explanation=await self.llm.explain_similarity(
                        idea.challenge.content,
                        match.content
                    )
                ))
        
        # Find complementary approaches
        # Find contradictions
        # ... etc
        
        return connections
```

#### 5.2.5 Context Extraction

Extracts useful insights from context files (referenced via `@filename.md` in chat):

```python
class ContextExtractionAgent:
    """Extracts insights from Markdown context files to strengthen kernel files."""
    
    async def analyze(self, idea: Idea, context_file: ContextFile) -> List[Insight]:
        insights = await self.llm.extract_insights(
            context=context_file.content,
            kernel_files={
                'summary': idea.summary.content,
                'challenge': idea.challenge.content,
                'approach': idea.approach.content,
                'steps': idea.coherent_steps.content
            }
        )
        
        return [
            Insight(
                source_file=context_file.filename,
                quote=i.quote,
                relevance=i.relevant_to,  # which kernel file
                suggestion=i.how_to_use
            )
            for i in insights
        ]
```

### 5.3 Agent Orchestration

```python
class CrabgrassAgent:
    """Main agent orchestrator."""
    
    def __init__(self):
        self.completion = CompletionNudgeAgent()
        self.coherence = CoherenceAgent()
        self.quality = QualityAgent()
        self.connection = ConnectionAgent()
        self.extraction = ContextExtractionAgent()
    
    async def on_idea_updated(self, idea: Idea, trigger: str):
        """Called when an idea is updated."""
        
        results = []
        
        # Always check completion status
        if nudge := await self.completion.analyze(idea):
            results.append(nudge)
        
        # Check coherence if multiple files complete
        if idea.kernel_completion >= 2:
            if suggestion := await self.coherence.analyze(idea):
                results.append(suggestion)
        
        # Check quality of recently edited file
        if trigger.startswith('file_updated:'):
            file_type = trigger.split(':')[1]
            if suggestion := await self.quality.analyze(idea, file_type):
                results.append(suggestion)
        
        # Look for connections (async, non-blocking)
        asyncio.create_task(self._discover_connections(idea))
        
        return results
    
    async def on_context_file_added(self, idea: Idea, context_file: ContextFile):
        """Called when a context file is added."""
        
        insights = await self.extraction.analyze(idea, context_file)
        
        if insights:
            return AgentMessage(
                type='insights_found',
                content=insights,
                actions=['add_to_kernel', 'ignore']
            )
```

### 5.4 Notification Priority

Not all agent messages are equal:

| Priority | Type | Delivery |
|----------|------|----------|
| **High** | Coherence problem, Connection to ping another user | Immediate toast |
| **Medium** | Quality suggestion, Context insight | In-panel on next visit |
| **Low** | Completion nudge (after 24h) | Email digest |

---

## 6. User Interface

### 6.1 Screen: Idea Overview

The home screen for an idea showing kernel status, context files, and connections.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← All Ideas                                                [User] ⚙️  ?    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  {Idea Title}                                                  ⭐  •••     │
│  {Description}                                                              │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  IDEA KERNEL                                                     ◉ {n}/4   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │ {✓|○}       │  │ {✓|○}       │  │ {✓|○}       │  │ {✓|○}       │ │   │
│  │  │ Summary     │  │ Challenge   │  │ Approach    │  │ Coherent    │ │   │
│  │  │             │  │             │  │             │  │ Steps       │ │   │
│  │  │ {preview}   │  │ {preview}   │  │ {preview}   │  │ {preview}   │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │
│    ⚡ Agent: {current suggestion}                          [Action]     │   │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CONTEXT FILES                                                   + Add     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  {file cards or empty state}                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CONNECTIONS                                               {n} found       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  {connection cards or empty state}                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Screen: File Editor (70/30 Split)

When editing any file, show canvas and agent chat side-by-side.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← {Idea} / {Filename}                                      [User] ⚙️  ?   │
├─────────────────────────────────────────────────┬───────────────────────────┤
│                                                 │                           │
│              CANVAS (70%)                       │     AGENT CHAT (30%)      │
│                                                 │                           │
├─────────────────────────────────────────────────┤───────────────────────────┤
│                                                 │                           │
│  {Filename}                        ↻ ⬇️ •••   │  ⚡ Crabgrass Agent        │
│  ───────────────────────────────────────────   │                           │
│                                                 │  ┌───────────────────────┐│
│  {Markdown content}                             │  │ {Agent message}       ││
│                                                 │  │                       ││
│  |                                              │  │ [Action] [Dismiss]    ││
│                                                 │  └───────────────────────┘│
│                                                 │                           │
│                                                 │  {Chat history}           │
│                                                 │                           │
│                                                 │───────────────────────────│
│                                                 │  ┌───────────────────────┐│
│                                                 │  │ Reply... @file.md     ││
│                                                 │  │                       ││
│                                                 │  │            ⬆️ [Send] ││
│                                                 │  └───────────────────────┘│
│                                                 │                           │
├─────────────────────────────────────────────────┴───────────────────────────┤
│  {Footer: kernel status for kernel files, "Context file" for context}      │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Chat @ References:**
- Type `@` in chat to see available context files
- Select a file (e.g., `@research-notes.md`) to include its content as context
- Agent will read the referenced file when responding

### 6.3 Screen: All Ideas (Dashboard)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Crabgrass                                                  [User] ⚙️  ?   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  MY IDEAS                                      [+ New Idea]  Filter ▼      │
│                                                                             │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────┐ │
│  │ {Title}               │  │ {Title}               │  │ {Title}         │ │
│  │ ◉ 3/4  •  Active      │  │ ◉ 1/4  •  Draft       │  │ ◉ 4/4  •  Done  │ │
│  │ Updated 2h ago        │  │ Updated 3d ago        │  │ Updated 1w ago  │ │
│  │ {connections badge}   │  │ ⚡ Needs attention    │  │                 │ │
│  └───────────────────────┘  └───────────────────────┘  └─────────────────┘ │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SHARED WITH ME                                                            │
│                                                                             │
│  ┌───────────────────────┐  ┌───────────────────────┐                      │
│  │ {Title}               │  │ {Title}               │                      │
│  │ by {User} • Editor    │  │ by {User} • Viewer    │                      │
│  └───────────────────────┘  └───────────────────────┘                      │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CONNECTIONS FEED                                          View all →      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🔗 Your "Customer Feedback" has a similar challenge to              │   │
│  │    "Voice of Customer" by Maria Chen.                    [View]    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🔗 Dev Patel's "API Strategy" approach might complement your        │   │
│  │    "Integration Hub" idea.                               [View]    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.4 Component: Agent Toast (Proactive Notification)

```
┌─────────────────────────────────────────────────────────────┐
│ ⚡ Crabgrass Agent                                      ✕   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  {Message}                                                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ {Preview or detail if relevant}                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│                            [Secondary Action]  [Primary]    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.5 UI State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                      UI STATE MACHINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                      ┌──────────────┐                           │
│                      │   Dashboard  │                           │
│                      │  (All Ideas) │                           │
│                      └──────┬───────┘                           │
│                             │                                   │
│              ┌──────────────┼──────────────┐                   │
│              ▼              ▼              ▼                   │
│       ┌──────────┐   ┌──────────┐   ┌──────────┐              │
│       │  Create  │   │  Select  │   │Connection│              │
│       │   Idea   │   │   Idea   │   │  Feed    │              │
│       └────┬─────┘   └────┬─────┘   └────┬─────┘              │
│            │              │              │                     │
│            ▼              ▼              │                     │
│       ┌─────────────────────────────┐    │                     │
│       │       Idea Overview         │◄───┘                     │
│       └──────┬──────────────┬───────┘                          │
│              │              │                                   │
│       ┌──────┴───┐    ┌─────┴────┐                             │
│       ▼          ▼    ▼          ▼                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│  │ Kernel  │ │ Kernel  │ │ Context │ │Connection│              │
│  │  File   │ │  File   │ │  File   │ │ Preview │              │
│  │ Editor  │ │ Editor  │ │ Editor  │ │         │              │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘              │
│       │          │            │                                │
│       └──────────┴────────────┘                                │
│              │                                                  │
│              ▼                                                  │
│       ┌─────────────┐                                          │
│       │   70/30     │                                          │
│       │ Split View  │                                          │
│       │ (Canvas +   │                                          │
│       │  Agent)     │                                          │
│       └─────────────┘                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Tech Stack

### 7.1 Overview

| Aspect | Technology | Rationale |
|--------|------------|-----------|
| **Backend** | Python 3.11+, FastAPI | Async, type hints, fast development |
| **Event Coordination** | asyncio | Native Python async for synchronizations |
| **AI Framework** | Google ADK | Native Gemini integration, agent primitives |
| **Database** | DuckDB | Embedded, fast analytics, extensible |
| **Vector Search** | DuckDB VSS Extension | Same DB for all queries |
| **Graph DB** | DuckDB DuckPGQ | Same DB, SQL/PGQ interface |
| **Version Control** | JJ (Jujutsu) | Conflict-free, operation log, modern |
| **Frontend** | Vanilla JS (ES Modules) | No build step, direct control |
| **UI Protocol** | AG-UI Protocol | Streaming, agent-native |
| **Package Manager** | uv (Python), npx serve (dev) | Fast, modern |
| **LLM** | Gemini | Embeddings + reasoning |

### 7.2 Python Dependencies

```toml
# pyproject.toml
[project]
name = "crabgrass"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "duckdb>=0.10.0",
    "google-generativeai>=0.4.0",   # Gemini SDK
    "google-adk>=0.1.0",             # Agent Development Kit
    "pydantic>=2.5.0",
    "python-multipart>=0.0.6",       # File uploads
    "sse-starlette>=1.6.0",          # Server-Sent Events
    "httpx>=0.26.0",                 # Async HTTP
    "structlog>=24.1.0",             # Logging
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]
```

### 7.3 Frontend Structure

```
frontend/
├── index.html
├── styles/
│   ├── main.css
│   ├── canvas.css
│   └── components.css
├── js/
│   ├── main.js              # Entry point
│   ├── concepts/
│   │   ├── canvas.js        # Canvas concept
│   │   ├── chat.js          # Chat concept
│   │   ├── file-tree.js     # FileTree concept
│   │   ├── kernel-status.js # KernelStatus concept
│   │   └── toast.js         # Toast concept
│   ├── sync/
│   │   └── synchronizations.js  # Concept coordination
│   ├── api/
│   │   ├── client.js        # REST client
│   │   └── events.js        # SSE EventSource client
│   └── lib/
│       ├── markdown.js      # MD rendering
│       └── ag-ui.js         # AG-UI protocol
└── assets/
    └── icons/
```

### 7.4 Backend Structure

```
backend/
├── crabgrass/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── concepts/
│   │   ├── __init__.py
│   │   ├── idea.py          # Idea concept
│   │   ├── file.py          # File concept
│   │   ├── version.py       # Version concept (JJ)
│   │   ├── search.py        # Search concept (vector)
│   │   ├── graph.py         # Graph concept
│   │   ├── agent.py         # Agent concept
│   │   ├── user.py          # User concept
│   │   └── collab.py        # Collaboration concept
│   ├── sync/
│   │   ├── __init__.py
│   │   └── synchronizations.py  # Concept coordination
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py    # DuckDB connection
│   │   ├── migrations.py    # Schema migrations
│   │   └── queries.py       # SQL queries
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── gemini.py        # Gemini client
│   │   ├── embeddings.py    # Embedding generation
│   │   └── prompts.py       # System prompts
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── ideas.py
│   │   │   ├── files.py
│   │   │   ├── agent.py
│   │   │   └── search.py
│   │   └── sse.py           # SSE event streams
│   └── jj/
│       ├── __init__.py
│       └── repository.py    # JJ operations wrapper
├── tests/
└── pyproject.toml
```

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

#### Search & Graph

```
POST   /api/search/similar           # Find similar ideas
GET    /api/ideas/{id}/connections   # Get idea connections
POST   /api/ideas/{id}/connections   # Manually link ideas
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

// Connection discovered
event: connection_found
data: {"connection_type": "similar_challenge", "target_idea": {"id": "...", "title": "...", "owner": "..."}, "strength": 0.85}

// File save confirmation
event: file_saved
data: {"file_type": "challenge", "version": "abc123", "saved_at": "2025-01-15T10:30:00Z"}
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

### Phase 1: Foundation (MVP)

**Goal:** Single-user idea creation with agent coaching

- [ ] Core data model (DuckDB tables)
- [ ] Idea CRUD operations
- [ ] Kernel file editing with Markdown
- [ ] Basic agent: completion nudging
- [ ] Single-page web UI
- [ ] JJ integration for versioning

### Phase 2: Intelligence

**Goal:** Semantic search and quality coaching

- [ ] Vector embeddings (Gemini)
- [ ] VSS extension integration
- [ ] Similar idea discovery
- [ ] Quality coaching agent
- [ ] Coherence checking agent
- [ ] Context file support

### Phase 3: Organization

**Goal:** Multi-user, cross-organization connections

- [ ] User authentication
- [ ] Organization model
- [ ] Collaboration (share ideas)
- [ ] Graph database (DuckPGQ)
- [ ] Connection discovery agent
- [ ] Notification system

### Phase 4: Scale

**Goal:** Production readiness

- [ ] Google Spanner migration path
- [ ] Performance optimization
- [ ] Advanced analytics dashboard
- [ ] API for integrations
- [ ] Mobile-responsive UI

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Idea** | A project container in Crabgrass |
| **Kernel File** | One of the four required structured files (Summary, Challenge, Approach, Coherent Steps) |
| **Context File** | Optional Markdown file for supporting material, referenced via `@filename.md` |
| **Innovation** | An idea that has been executed and delivered value |
| **Connection** | A relationship between two ideas |
| **Agent** | The proactive AI coach |
| **Concept** | An independent unit of functionality (architecture pattern) |
| **Synchronization** | Coordination logic between concepts |

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

*Document version: 0.1.0-draft*  
*Last updated: 2025-12-31*