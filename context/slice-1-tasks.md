# Slice 1: Project Foundation - Tasks

**Goal:** Runnable backend and frontend with database, dev user switching, and basic navigation.

**Status:** Implementation complete. Ready for manual testing.

---

## Backend Tasks

- [x] 1. Create project structure (`backend/crabgrass/...`)
- [x] 2. Create `pyproject.toml` with dependencies
- [x] 3. Create `config.py` with environment variables
- [x] 4. Create DuckDB connection manager (`db/connection.py`)
- [x] 5. Create migrations with initial schema (`db/migrations.py`)
- [x] 6. Load and verify VSS + DuckPGQ extensions
- [x] 7. Pre-seed Acme Corp org with Sally and Sam users
- [x] 8. Create FastAPI app (`main.py`) with CORS and health check
- [x] 9. Create dev auth routes (`api/routes/auth.py`)
- [x] 10. Auth via cookie (no middleware needed - uses FastAPI Cookie dependency)

## Frontend Tasks

- [x] 11. Create project structure (`frontend/js/...`)
- [x] 12. Create `index.html` shell with header and main area
- [x] 13. Create CSS with variables for theming
- [x] 14. Create API client (`api/client.js`)
- [x] 15. Create user switcher component (`concepts/user-switcher.js`)
- [x] 16. Create hash-based router (`main.js`)

## Tests

- [x] 17. Create `test_db_connection.py` (5 tests, all passing)
- [x] 18. Create `test_auth.py` (7 tests, all passing)

**Total: 12 tests passing**

---

## Manual Testing Checklist

To test, run these commands in separate terminals:

### Terminal 1: Backend
```bash
cd backend
uv run uvicorn crabgrass.main:app --reload --port 8000
```

### Terminal 2: Frontend
```bash
cd frontend
npx serve . -l 3000
```

Then verify:

### Backend
- [ ] `uv run uvicorn crabgrass.main:app --reload` starts without errors
- [ ] `GET http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `GET http://localhost:8000/api/auth/users` returns Sally and Sam
- [ ] `POST http://localhost:8000/api/auth/switch/{user_id}` sets cookie and returns user info
- [ ] `GET http://localhost:8000/api/auth/me` returns current user based on cookie
- [ ] Switching to Sam works the same way
- [ ] DuckDB file is created at `backend/data/crabgrass.duckdb`

### Frontend
- [ ] `npx serve . -l 3000` serves the app at http://localhost:3000
- [ ] Page loads with header showing logo and user dropdown
- [ ] User dropdown shows Sally and Sam
- [ ] Clicking a user switches and reloads
- [ ] Current user is displayed in header
- [ ] Hash routes work (`#/`, `#/ideas/123`, `#/objectives/456`)
- [ ] Route changes update the main content area

### Integration
- [ ] Frontend can call backend API (CORS works)
- [ ] User switch persists across page reload
- [ ] Both Sally and Sam can be switched between

---

## Files Created

### Backend
- `backend/pyproject.toml` - Dependencies and project config
- `backend/crabgrass/config.py` - Environment settings
- `backend/crabgrass/main.py` - FastAPI app
- `backend/crabgrass/db/connection.py` - DuckDB connection manager
- `backend/crabgrass/db/migrations.py` - Schema and seed data
- `backend/crabgrass/api/routes/auth.py` - Auth endpoints
- `backend/tests/test_db_connection.py` - DB tests
- `backend/tests/test_auth.py` - Auth tests

### Frontend
- `frontend/index.html` - Main HTML
- `frontend/styles/main.css` - Core styles and variables
- `frontend/styles/components.css` - Component styles
- `frontend/js/main.js` - Entry point and router
- `frontend/js/api/client.js` - API client
- `frontend/js/concepts/user-switcher.js` - User switcher component

---

*Last updated: 2026-01-01*
