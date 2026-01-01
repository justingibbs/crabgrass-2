# Crabgrass: Coding Patterns

**Version:** 0.1.0
**Date:** 2025-12-31

Implementation conventions for AI assistants and developers.

---

## Core Principle: Concepts and Synchronizations

Every feature maps to either a **Concept** or a **Synchronization**. Never embed coordination logic inside concepts.

---

## Backend Concept Pattern

Concepts are self-contained modules with state and actions.

```python
# backend/crabgrass/concepts/idea.py

from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Optional
from ..db.connection import get_db

@dataclass
class Idea:
    """State representation."""
    id: UUID
    org_id: UUID
    creator_id: UUID
    title: str
    objective_id: Optional[UUID]  # Can be attached later
    status: str  # 'draft' | 'active' | 'archived'
    kernel_completion: int  # 0-4
    created_at: datetime
    updated_at: datetime


class IdeaConcept:
    """Actions for the Idea concept."""

    async def create(
        self,
        org_id: UUID,
        user_id: UUID,
        title: str,
        objective_id: Optional[UUID] = None  # Optional, can be attached later
    ) -> Idea:
        """Create a new idea. Does NOT trigger synchronizations."""
        async with get_db() as db:
            result = await db.execute(
                """
                INSERT INTO ideas (org_id, creator_id, title, objective_id)
                VALUES (?, ?, ?, ?)
                RETURNING *
                """,
                (org_id, user_id, title, objective_id)
            )
            return Idea(**result.fetchone())

    async def get(self, idea_id: UUID) -> Optional[Idea]:
        """Get idea by ID."""
        async with get_db() as db:
            result = await db.execute(
                "SELECT * FROM ideas WHERE id = ?",
                (idea_id,)
            )
            row = result.fetchone()
            return Idea(**row) if row else None

    async def update(self, idea_id: UUID, **fields) -> Idea:
        """Update idea fields."""
        # Implementation...
        pass

    async def archive(self, idea_id: UUID) -> None:
        """Soft delete by setting status to 'archived'."""
        await self.update(idea_id, status='archived')
```

**Key patterns:**
- Concept classes contain ONLY their own logic
- Methods do NOT call other concepts directly
- Return domain objects, not dicts
- Use `async/await` throughout

---

## Synchronization Pattern

Synchronizations coordinate concepts. They live in `sync/synchronizations.py`.

```python
# backend/crabgrass/sync/synchronizations.py

from ..concepts.idea import IdeaConcept
from ..concepts.kernel_file import KernelFileConcept
from ..concepts.version import VersionConcept
from ..concepts.graph import GraphConcept
from ..concepts.session import SessionConcept

idea_concept = IdeaConcept()
kernel_file_concept = KernelFileConcept()
version_concept = VersionConcept()
graph_concept = GraphConcept()
session_concept = SessionConcept()


async def on_idea_created(idea):
    """
    sync IdeaCreated:
        when Idea.create():
            → KernelFile.initializeAll(idea_id)
            → Version.initialize(idea_id)
            → if objective_id: Graph.connect(idea_id, objective_id, "SUPPORTS")
            → Session.create(idea_id, user_id, "coherence")
    """
    await kernel_file_concept.initialize_all(idea.id)
    await version_concept.initialize(idea.id)
    if idea.objective_id:
        await graph_concept.connect(idea.id, idea.objective_id, "SUPPORTS")
    await session_concept.create(idea.id, idea.creator_id, "coherence")


async def on_idea_linked_to_objective(idea_id, objective_id):
    """
    sync IdeaLinkedToObjective:
        when Idea.update(idea_id, objective_id):
            → Graph.connect(idea_id, objective_id, "SUPPORTS")
    """
    await graph_concept.connect(idea_id, objective_id, "SUPPORTS")


async def on_kernel_file_updated(idea_id, file_type, content):
    """
    sync KernelFileUpdated:
        when KernelFile.update():
            → Version.commit()
            → Embedding.generate()
            → Agent.evaluate()
    """
    from ..concepts.embedding import EmbeddingConcept
    from ..concepts.agent import get_agent_for_file_type

    await version_concept.commit(idea_id, file_type, content)

    embedding = await EmbeddingConcept().generate(content)
    await kernel_file_concept.set_embedding(idea_id, file_type, embedding)

    agent = get_agent_for_file_type(file_type)
    await agent.evaluate(idea_id, content)
```

**Key patterns:**
- One function per synchronization rule
- Synchronizations are the ONLY place concepts interact
- Name functions `on_<event>` to match the trigger
- Include the spec pseudocode as docstring

---

## API Route Pattern

Routes are thin - they call concepts and trigger synchronizations.

```python
# backend/crabgrass/api/routes/ideas.py

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from pydantic import BaseModel

from ...concepts.idea import IdeaConcept
from ...sync.synchronizations import on_idea_created
from ...auth import get_current_user

router = APIRouter(prefix="/api/ideas", tags=["ideas"])
idea_concept = IdeaConcept()


class CreateIdeaRequest(BaseModel):
    title: str
    objective_id: Optional[UUID] = None  # Can be attached later


@router.post("")
async def create_idea(
    request: CreateIdeaRequest,
    user = Depends(get_current_user)
):
    """Create a new idea and trigger synchronizations."""
    idea = await idea_concept.create(
        org_id=user.org_id,
        user_id=user.id,
        title=request.title,
        objective_id=request.objective_id
    )

    # Trigger synchronization
    await on_idea_created(idea)

    return {"id": idea.id, "title": idea.title}


@router.get("/{idea_id}")
async def get_idea(
    idea_id: UUID,
    user = Depends(get_current_user)
):
    """Get idea by ID."""
    idea = await idea_concept.get(idea_id)
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea
```

**Key patterns:**
- Use Pydantic models for request/response
- Routes call concepts, then trigger synchronizations
- Keep routes thin - no business logic

---

## Agent Pattern

Agents are specialized concepts that interact with Gemini.

```python
# backend/crabgrass/concepts/agents/challenge_agent.py

from google import genai
from dataclasses import dataclass
from uuid import UUID
from typing import Optional

from ..kernel_file import KernelFileConcept
from ...ai.prompts import CHALLENGE_AGENT_SYSTEM_PROMPT

kernel_file_concept = KernelFileConcept()


@dataclass
class EvaluationResult:
    is_complete: bool
    feedback: str
    criteria: dict  # {specific: bool, measurable: bool, significant: bool}


class ChallengeAgent:
    """Coaches users to articulate a specific, measurable, significant challenge."""

    COMPLETION_CRITERIA = ["specific", "measurable", "significant"]

    def __init__(self):
        self.client = genai.Client()

    async def evaluate(self, idea_id: UUID, content: str) -> EvaluationResult:
        """Assess content against completion criteria."""
        response = await self.client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"""
            Evaluate this Challenge statement against criteria:
            - Specific: Not vague or overly broad
            - Measurable: Can determine if it's solved
            - Significant: Worth solving

            Content:
            {content}

            Return JSON: {{"specific": bool, "measurable": bool, "significant": bool, "feedback": str}}
            """,
            config={"response_mime_type": "application/json"}
        )

        result = response.parsed
        is_complete = all(result.get(c) for c in self.COMPLETION_CRITERIA)

        if is_complete:
            await kernel_file_concept.mark_complete(idea_id, "challenge")

        return EvaluationResult(
            is_complete=is_complete,
            feedback=result["feedback"],
            criteria=result
        )

    async def coach(self, idea_id: UUID, content: str, user_message: str) -> str:
        """Provide guidance on improving the challenge."""
        response = await self.client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {"role": "user", "parts": [{"text": CHALLENGE_AGENT_SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": f"Current content:\n{content}"}]},
                {"role": "user", "parts": [{"text": user_message}]}
            ]
        )
        return response.text
```

**Key patterns:**
- Each agent has `evaluate()`, `coach()`, `suggest()` methods
- Agents CAN mark kernel files complete (they're the authority)
- Use structured output (JSON) for evaluations
- System prompts live in `ai/prompts.py`

---

## Frontend Concept Pattern

Frontend concepts manage state and DOM updates.

```javascript
// frontend/js/concepts/canvas.js

export class Canvas {
  constructor(containerEl) {
    this.container = containerEl;
    this.content = '';
    this.isDirty = false;
    this.isEditing = false;

    this.render();
  }

  // State
  get state() {
    return {
      content: this.content,
      isDirty: this.isDirty,
      isEditing: this.isEditing
    };
  }

  // Actions
  load(content) {
    this.content = content;
    this.isDirty = false;
    this.render();
  }

  edit() {
    this.isEditing = true;
    this.render();
  }

  save() {
    // Emit event for synchronization to handle
    this.container.dispatchEvent(
      new CustomEvent('canvas:save', {
        detail: { content: this.content },
        bubbles: true
      })
    );
    this.isDirty = false;
    this.render();
  }

  updateContent(newContent) {
    this.content = newContent;
    this.isDirty = true;
    this.render();
  }

  // Rendering
  render() {
    if (this.isEditing) {
      this.container.innerHTML = `
        <textarea class="canvas-editor">${this.content}</textarea>
      `;
      this.container.querySelector('textarea')
        .addEventListener('input', (e) => this.updateContent(e.target.value));
    } else {
      this.container.innerHTML = `
        <div class="canvas-preview">${this.renderMarkdown(this.content)}</div>
      `;
    }
  }

  renderMarkdown(md) {
    // Use lib/markdown.js
    return marked.parse(md);
  }
}
```

**Key patterns:**
- Concepts emit CustomEvents, synchronizations listen
- State is encapsulated, accessed via getters
- `render()` updates DOM based on state
- No direct API calls in concepts

---

## Frontend Synchronization Pattern

```javascript
// frontend/js/sync/synchronizations.js

import { apiClient } from '../api/client.js';
import { sseClient } from '../api/events.js';

export function setupSynchronizations(ideaWorkspace) {
  const { canvas, chat, fileList } = ideaWorkspace;

  // sync: Canvas save → API update → Version commit
  document.addEventListener('canvas:save', async (e) => {
    const { content } = e.detail;
    const { ideaId, fileType } = ideaWorkspace.state;

    await apiClient.updateKernelFile(ideaId, fileType, content);
    // Server triggers embedding + agent evaluation
  });

  // sync: SSE agent message → Chat display
  sseClient.on('agent_message', (data) => {
    chat.receive({
      role: 'agent',
      content: data.content,
      actions: data.actions
    });
  });

  // sync: SSE completion changed → KernelStatus update
  sseClient.on('completion_changed', (data) => {
    fileList.updateCompletion(data.file_type, data.is_complete);
  });
}
```

---

## SSE Event Pattern

```python
# backend/crabgrass/api/sse.py

from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter
import asyncio

router = APIRouter()

@router.get("/api/ideas/{idea_id}/events")
async def idea_events(idea_id: UUID):
    """SSE stream for idea updates."""

    async def event_generator():
        queue = await subscribe_to_idea(idea_id)
        try:
            while True:
                event = await queue.get()
                yield {
                    "event": event.type,
                    "data": event.data
                }
        except asyncio.CancelledError:
            await unsubscribe_from_idea(idea_id, queue)

    return EventSourceResponse(event_generator())
```

---

## Database Pattern

Use raw SQL with DuckDB. No ORM.

```python
# backend/crabgrass/db/queries.py

IDEA_QUERIES = {
    "create": """
        INSERT INTO ideas (org_id, creator_id, title, objective_id)
        VALUES ($1, $2, $3, $4)
        RETURNING *
    """,

    "get_by_id": """
        SELECT * FROM ideas WHERE id = $1
    """,

    "list_for_user": """
        SELECT i.* FROM ideas i
        LEFT JOIN idea_collaborators c ON i.id = c.idea_id
        WHERE i.org_id = $1
        AND (i.creator_id = $2 OR c.user_id = $2)
        ORDER BY i.updated_at DESC
    """
}
```

---

## Testing Pattern

```python
# backend/tests/concepts/test_idea.py

import pytest
from crabgrass.concepts.idea import IdeaConcept

@pytest.fixture
def idea_concept():
    return IdeaConcept()

@pytest.mark.asyncio
async def test_create_idea_with_objective(idea_concept, test_db, test_user, test_objective):
    """Ideas can optionally be linked to an objective at creation."""
    idea = await idea_concept.create(
        org_id=test_user.org_id,
        user_id=test_user.id,
        title="Test Idea",
        objective_id=test_objective.id  # Optional
    )

    assert idea.title == "Test Idea"
    assert idea.status == "draft"
    assert idea.kernel_completion == 0
    assert idea.objective_id == test_objective.id

@pytest.mark.asyncio
async def test_idea_without_objective(idea_concept, test_db, test_user):
    """Ideas can be created without an objective (attached later)."""
    idea = await idea_concept.create(
        org_id=test_user.org_id,
        user_id=test_user.id,
        title="Idea Without Objective"
        # objective_id not provided - this is valid
    )

    assert idea.title == "Idea Without Objective"
    assert idea.objective_id is None
```

---

## File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Backend concept | `snake_case.py` | `kernel_file.py` |
| Backend sync | `synchronizations.py` | Single file |
| Frontend concept | `kebab-case.js` | `kernel-status.js` |
| Frontend sync | `synchronizations.js` | Single file |
| Tests | `test_<concept>.py` | `test_idea.py` |

---

## Common Mistakes to Avoid

1. **Calling concepts from concepts** - Use synchronizations
2. **Business logic in routes** - Routes are thin, concepts have logic
3. **Skipping synchronizations** - Every cross-concept action needs a sync
4. **Mutable state in concepts** - Return new objects, don't mutate
5. **Blocking calls** - Use `async/await` everywhere

---

*Document version: 0.1.0*
*Last updated: 2025-12-31*
