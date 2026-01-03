# Slice 3: Idea Workspace & File Viewing - Tasks

**Goal:** Click idea → see Idea Workspace with kernel files and basic layout.

**Status:** Complete

---

## Design Decisions

| Decision | Choice |
|----------|--------|
| Title editing | Auto-save on blur with debounce |
| CoherenceAgent chat | "Coming soon" placeholder |
| Kernel file click | Navigate to `#/ideas/:id/kernel/:type` placeholder |
| Context files section | Show section header with empty state |
| Archive/Publish buttons | Visible but non-functional placeholders |

---

## Backend Tasks

- [x] 1. Add `GET /api/ideas/{id}/kernel/{type}` endpoint to get kernel file content

## Frontend Tasks

- [x] 2. Create KernelStatus concept (`concepts/kernel-status.js`) - renders ●●○○ progress
- [x] 3. Create FileList concept (`concepts/file-list.js`) - renders kernel file cards
- [x] 4. Create IdeaWorkspace concept (`concepts/idea-workspace.js`) - manages workspace state
- [x] 5. Create Idea Workspace page layout with all sections
- [x] 6. Implement inline title editing with auto-save
- [x] 7. Add placeholder for CoherenceAgent chat ("Coming soon")
- [x] 8. Add context files section with empty state
- [x] 9. Add Archive/Publish button placeholders
- [x] 10. Update router to handle `#/ideas/:id` and `#/ideas/:id/kernel/:type`
- [x] 11. Add workspace styles to components.css

## Tests

- [x] 12. Add kernel file content endpoint test to `test_ideas_api.py`

**Total: 46 tests passing (including Slices 1-2 tests + 5 new kernel file tests)**

---

## Files Created/Modified

### Backend (Modified)
- `backend/crabgrass/api/routes/ideas.py` - Added `GET /api/ideas/{id}/kernel/{type}` endpoint
- `backend/tests/test_ideas_api.py` - Added 5 tests for kernel file endpoint

### Frontend (New)
- `frontend/js/concepts/kernel-status.js` - Renders kernel completion progress (●●○○)
- `frontend/js/concepts/file-list.js` - Renders kernel file cards with click navigation
- `frontend/js/concepts/idea-workspace.js` - Manages idea workspace state and UI

### Frontend (Modified)
- `frontend/js/main.js` - Updated routing for workspace and file editor placeholder
- `frontend/js/api/client.js` - Added `getKernelFile()` method
- `frontend/styles/components.css` - Added workspace, file card, and action bar styles

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

- [x] Click idea card from home → navigates to workspace
- [x] Workspace shows idea title (editable)
- [x] Title edit auto-saves on blur
- [x] Kernel progress shows ●●○○ format correctly
- [x] 4 kernel file cards display with completion status
- [x] Click kernel file card → navigates to placeholder
- [x] "← Home" link works
- [x] CoherenceAgent section shows "Coming soon"
- [x] Context files section shows empty state
- [x] Archive/Publish buttons are visible

---

*Last updated: 2026-01-01*
