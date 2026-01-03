# Slice 4: File Editor with Canvas - Tasks

**Goal:** Click kernel file → 50/50 editor with canvas (toggle mode), JJ version control.

**Status:** Complete

---

## Design Decisions

| Decision | Choice |
|----------|--------|
| Canvas layout | Toggle mode (Edit OR Preview, not side-by-side) |
| Markdown rendering | marked.js via CDN |
| JJ integration | Full implementation (not deferred) |
| Version control | JJ repo per idea at `{STORAGE_ROOT}/ideas/{idea_id}/` |
| File sync | Write to both DB (source of truth) and filesystem (for JJ) |
| History endpoint | Implemented with JJ log |

---

## Backend Tasks

- [x] 1. Create JJ repository wrapper (`jj/repository.py`)
  - `initialize(idea_id)` - Create repo at `{STORAGE_ROOT}/ideas/{idea_id}/`
  - `commit(idea_id, message)` - Commit current state
  - `get_history(idea_id, file_path)` - Get commit log
  - `write_file(idea_id, file_path, content)` - Write file to repo

- [x] 2. Create Version concept (`concepts/version.py`)
  - Wrapper around JJRepository
  - `initialize(idea_id)`, `commit(idea_id, file_type, content)`, `get_history(idea_id, file_type)`

- [x] 3. Update synchronizations
  - `on_idea_created()`: Call `Version.initialize(idea_id)`
  - `on_kernel_file_updated()`: Call `Version.commit()`

- [x] 4. Add PUT endpoint for kernel file update
  - `PUT /api/ideas/{id}/kernel/{type}` - Update content, trigger sync

- [x] 5. Add history endpoint
  - `GET /api/ideas/{id}/kernel/{type}/history` - Get version history from JJ

## Frontend Tasks

- [x] 6. Add marked.js CDN to index.html

- [x] 7. Create markdown utility (`lib/markdown.js`)
  - Wrapper around marked.js
  - Basic sanitization

- [x] 8. Create Canvas concept (`concepts/canvas.js`)
  - State: content, originalContent, isDirty, mode ('edit' | 'preview')
  - Actions: `load()`, `save()`, `cancel()`, `updateContent()`, `toggleMode()`
  - Render: Toggle tabs + textarea OR rendered preview

- [x] 9. Create File Editor page (`pages/file-editor.js`)
  - 50/50 layout: Chat placeholder (left) + Canvas (right)
  - Header: Back link, file name, completion status
  - Footer: Cancel, Save & Close buttons

- [x] 10. Add API client method for updating kernel file
  - `updateKernelFile(ideaId, fileType, content)`

- [x] 11. Update router to use File Editor page

- [x] 12. Add file editor styles to components.css

## Tests

- [x] 13. Add kernel file update API tests (`test_ideas_api.py::TestUpdateKernelFile`)
- [x] 14. Add kernel file history API tests (`test_ideas_api.py::TestKernelFileHistory`)
- [x] 15. JJ integration tested via synchronization tests

**Test Results:** 55 tests pass (added 9 new tests for PUT endpoint and history)

---

## Files Created/Modified

### Backend (New)
- `backend/crabgrass/jj/__init__.py` - Package init
- `backend/crabgrass/jj/repository.py` - JJ CLI wrapper
- `backend/crabgrass/concepts/version.py` - Version concept

### Frontend (New)
- `frontend/js/lib/markdown.js` - Marked.js wrapper
- `frontend/js/concepts/canvas.js` - Canvas state/rendering
- `frontend/js/pages/file-editor.js` - File editor page

### Modified
- `frontend/index.html` - Add marked.js CDN
- `frontend/js/main.js` - Updated route handler to use FileEditor
- `frontend/js/api/client.js` - Added updateKernelFile, getKernelFileHistory methods
- `frontend/styles/components.css` - File editor and canvas styles
- `backend/crabgrass/api/routes/ideas.py` - Added PUT and history endpoints
- `backend/crabgrass/sync/synchronizations.py` - Added Version calls
- `backend/tests/test_ideas_api.py` - Added TestUpdateKernelFile, TestKernelFileHistory

---

## JJ Command Notes

Important: JJ uses different CLI arguments than Git:
- Initialize: `jj git init` (not `jj init`)
- Limit results: `-n` or `--limit` (not `-l`)

---

## Manual Testing Checklist

- [ ] Click kernel file from workspace → opens file editor
- [ ] Editor shows file content in textarea (Edit mode)
- [ ] Toggle to Preview → shows rendered markdown
- [ ] Toggle back to Edit → shows textarea with content
- [ ] Edit content → Save & Close → navigates back to workspace
- [ ] Reload page → content persists
- [ ] Cancel → discards changes, navigates back
- [ ] JJ repo created at `data/ideas/{idea_id}/`
- [ ] JJ history shows commits after saves

---

*Completed: 2026-01-02*
