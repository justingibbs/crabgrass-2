# Crabgrass

Innovation acceleration platform that transforms organizational knowledge into competitive advantage through AI-powered idea coaching.

## What This Is

Crabgrass treats ideas as structured projects with 4 required "Kernel Files":
- `Summary.md` - What the idea is
- `Challenge.md` - Problem being solved
- `Approach.md` - How it will be solved
- `CoherentSteps.md` - Concrete next actions

Ideas link to Objectives (org-wide strategic goals). 7 specialized AI agents coach users through completing kernel files.

**Core philosophy:** LLMs are sparring partners, not oracles. Bring organizational insight the LLM cannot generate, and force productive collision.

## Project Status

**Pre-implementation.** Specs are complete, no code written yet.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, Google ADK |
| Database | DuckDB + VSS (vector) + DuckPGQ (graph) |
| Version Control | JJ (Jujutsu) for idea files |
| Frontend | Vanilla JS (ES Modules), no build step |
| LLM | Gemini (embeddings + reasoning) |
| Streaming | AG-UI Protocol over SSE |

## Architecture

Uses **Concepts and Synchronizations** pattern (Jackson, MIT 2025):
- **Concepts**: Self-contained units with state + actions
- **Synchronizations**: Declarative rules coordinating concepts

See `context/concepts-and-synchronizations.md` for full definitions.

## Key Documentation

| File | Contents |
|------|----------|
| `context/crabgrass-spec-v1.md` | Full product spec, data model, API |
| `context/concepts-and-synchronizations.md` | Architecture pattern, all concepts |
| `context/tech-stack.md` | Technology choices, directory structure |
| `context/wireframes.md` | UI screens and interactions |
| `context/value-proposition.md` | Product vision and thesis |
| `context/coding-patterns.md` | Implementation conventions |

## Directory Structure (Target)

```
backend/
  crabgrass/
    concepts/     # idea.py, file.py, agent.py, etc.
    sync/         # synchronizations.py
    db/           # DuckDB connection, migrations
    ai/           # Gemini client, embeddings, prompts
    api/routes/   # FastAPI endpoints
    jj/           # JJ repository wrapper

frontend/
  js/
    concepts/     # canvas.js, chat.js, file-tree.js
    sync/         # synchronizations.js
    api/          # REST + SSE clients
```

## Development Commands

```bash
# Backend
uv run uvicorn crabgrass.main:app --reload

# Frontend (dev server)
npx serve frontend

# Tests
uv run pytest
```

## Important Patterns

1. **Objective linking is optional** - users can create ideas without an objective and attach one later
2. **Kernel files cannot be deleted** - only edited, always exist
3. **Agent-determined completion** - agents mark kernel files complete, not users
4. **Last-write-wins** - no real-time collab complexity; JJ handles versioning
5. **Agents require user approval** - suggestions only, users decide

## Before Implementing

1. Read `context/crabgrass-spec-v1.md` for data model and API
2. Read `context/concepts-and-synchronizations.md` for architecture
3. Read `context/coding-patterns.md` for conventions
4. Start with backend concepts before frontend
