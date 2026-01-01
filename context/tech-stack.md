# Crabgrass: Tech Stack

**Version:** 0.1.0
**Date:** 2025-12-31

---

## Overview

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

---

## Architecture Model

Crabgrass follows the **Concepts and Synchronizations** model ([Jackson, MIT 2025](https://news.mit.edu/2025/mit-researchers-propose-new-model-for-legible-modular-software-1106)) combined with **event-driven architecture**.

### Concepts and Synchronizations

- **Concepts** are independent, self-contained units of functionality with clear purpose, defined state, and explicit actions
- **Synchronizations** are declarative rules that coordinate concepts without coupling them
- The goal is legibility—the system reads "like a book" where concepts map to familiar phenomena

See [concepts-and-synchronizations.md](./concepts-and-synchronizations.md) for the complete concept and synchronization definitions.

### Event-Driven Architecture

- Concepts communicate through events rather than direct calls
- Synchronizations react to events and trigger cascading actions
- Enables loose coupling, scalability, and clear audit trails
- Implemented using Python asyncio for backend coordination and SSE for client-server streaming

---

## Embedding Configuration

- **Model:** Gemini embedding model
- **Dimensions:** 768
- **Usage:** All kernel and context files get embeddings for semantic search and RAG

---

## Python Dependencies

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

---

## Frontend Structure

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

---

## Backend Structure

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

## System Architecture Diagram

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

## References

- [Concepts and Synchronizations (MIT 2025)](https://news.mit.edu/2025/mit-researchers-propose-new-model-for-legible-modular-software-1106)
- [DuckDB](https://duckdb.org/)
- [DuckDB VSS Extension](https://duckdb.org/docs/extensions/vss)
- [DuckPGQ](https://github.com/cwida/duckpgq)
- [JJ (Jujutsu) VCS](https://github.com/jj-vcs/jj)
- [Google ADK](https://developers.google.com/agent-development-kit)
- [AG-UI Protocol](https://github.com/ag-ui-protocol/ag-ui)

---

*Document version: 0.1.0*
*Last updated: 2025-12-31*
