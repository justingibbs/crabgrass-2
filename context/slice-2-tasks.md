# Slice 2: Ideas List & Creation - Tasks

**Goal:** Home page shows ideas, can create new ideas with kernel file initialization.

**Status:** Complete

---

## Backend Tasks

- [x] 1. Add `ideas` and `kernel_files` tables to migrations
- [x] 2. Create Idea concept (`concepts/idea.py`) with dataclass and IdeaConcept class
- [x] 3. Create KernelFile concept (`concepts/kernel_file.py`) with template content
- [x] 4. Create synchronizations file (`sync/synchronizations.py`) with `on_idea_created()`
- [x] 5. Create ideas API routes (`api/routes/ideas.py`)
- [x] 6. Register ideas router in main.py

## Frontend Tasks

- [x] 7. Add ideas API methods to client.js
- [x] 8. Create IdeaList concept (`concepts/idea-list.js`)
- [x] 9. Update home page route to fetch and display real ideas
- [x] 10. Implement "New Idea" → create idea → navigate to workspace flow

## Tests

- [x] 11. Create `test_idea_concept.py` (16 tests)
- [x] 12. Create `test_ideas_api.py` (13 tests)

**Total: 41 tests passing (including Slice 1 tests)**

---

## Design Decisions

| Decision | Choice |
|----------|--------|
| Idea creation UX | Navigate to workspace with default title |
| Kernel file init | Template content with helpful placeholders |
| Auth in routes | Inline cookie extraction (simple) |
| "Shared with me" | Empty until Slice 9 |
| Synchronizations | Single `synchronizations.py` file |

---

## Kernel File Templates

### Summary.md
```markdown
# Summary

_Describe your idea in 2-3 sentences. What is it? What does it do?_
```

### Challenge.md
```markdown
# Challenge

_What problem are you solving? Who experiences this problem? Why does it matter?_
```

### Approach.md
```markdown
# Approach

_How will you solve this challenge? What makes your approach unique or effective?_
```

### CoherentSteps.md
```markdown
# Coherent Steps

_What are the concrete next actions? List 3-5 specific steps to move forward._

1.
2.
3.
```

---

## Files Created/Modified

### Backend (New)
- `backend/crabgrass/concepts/idea.py` - Idea concept with dataclass and IdeaConcept class
- `backend/crabgrass/concepts/kernel_file.py` - KernelFile concept with templates
- `backend/crabgrass/sync/synchronizations.py` - Synchronizations for concept coordination
- `backend/crabgrass/api/routes/ideas.py` - Ideas API routes
- `backend/tests/test_idea_concept.py` - Idea and KernelFile concept tests
- `backend/tests/test_ideas_api.py` - Ideas API tests

### Backend (Modified)
- `backend/crabgrass/db/migrations.py` - Added ideas, kernel_files, idea_collaborators tables
- `backend/crabgrass/main.py` - Registered ideas router

### Frontend (New)
- `frontend/js/concepts/idea-list.js` - IdeaList concept for home page

### Frontend (Modified)
- `frontend/js/api/client.js` - Added ideas API methods
- `frontend/js/main.js` - Updated home route to use IdeaList
- `frontend/styles/components.css` - Added idea card styles

---

## Manual Testing Checklist

To test, run these commands in separate terminals:

### Terminal 1: Backend
```bash
cd backend
rm -f data/crabgrass.duckdb  # Reset DB to pick up new tables
uv run uvicorn crabgrass.main:app --reload --port 8000
```

### Terminal 2: Frontend
```bash
cd frontend
npx serve . -l 3000
```

Then verify:

- [ ] Home page loads and shows "Contributing To" section
- [ ] "New Idea" card is displayed
- [ ] Clicking "New Idea" creates an idea and navigates to workspace
- [ ] Returning to home shows the created idea card
- [ ] Idea card displays title, status (draft), and kernel progress (0/4)
- [ ] Clicking an idea card navigates to its workspace (placeholder for now)
- [ ] "Shared With Me" section shows empty state
- [ ] "Objectives" section shows empty state

---

*Last updated: 2026-01-01*
