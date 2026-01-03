# Slice 6: Remaining Kernel Agents - Tasks

**Goal:** All 4 kernel file agents functional.

**Status:** Complete

---

## Design Decisions

| Decision | Choice |
|----------|--------|
| Cross-file context | ApproachAgent fetches Challenge.md, StepsAgent fetches Approach.md |
| Evaluation format | JSON with per-criterion feedback (same as ChallengeAgent) |
| Agent visibility | Users don't see agent names - appears as one unified coach |
| Pattern | Follow ChallengeAgent pattern exactly |

---

## Backend Tasks

- [x] 1. Add evaluation prompts to `ai/prompts.py`
  - `SUMMARY_AGENT_EVALUATION_PROMPT`
  - `APPROACH_AGENT_EVALUATION_PROMPT`
  - `STEPS_AGENT_EVALUATION_PROMPT`

- [x] 2. Create SummaryAgent (`concepts/agents/summary_agent.py`)
  - Criteria: Clear, Concise, Compelling
  - `evaluate(idea_id, content)` → EvaluationResult
  - `coach(idea_id, content, user_message, session_id)` → response
  - Mark file complete when all criteria met

- [x] 3. Create ApproachAgent (`concepts/agents/approach_agent.py`)
  - Criteria: Feasible, Differentiated, Addresses Challenge
  - Fetch Challenge.md content for context
  - `evaluate(idea_id, content)` → EvaluationResult
  - `coach(idea_id, content, user_message, session_id)` → response
  - Mark file complete when all criteria met

- [x] 4. Create StepsAgent (`concepts/agents/steps_agent.py`)
  - Criteria: Concrete, Sequenced, Assignable
  - Fetch Approach.md content for context
  - `evaluate(idea_id, content)` → EvaluationResult
  - `coach(idea_id, content, user_message, session_id)` → response
  - Mark file complete when all criteria met

- [x] 5. Update agent factory (`concepts/agents/__init__.py`)
  - Register SummaryAgent
  - Register ApproachAgent
  - Register StepsAgent
  - Update FILE_TYPE_TO_AGENT and AGENT_TYPE_TO_AGENT maps

## Tests

- [x] 6. Add SummaryAgent tests (`test_summary_agent.py`) - 9 tests
- [x] 7. Add ApproachAgent tests (`test_approach_agent.py`) - 9 tests
- [x] 8. Add StepsAgent tests (`test_steps_agent.py`) - 9 tests
- [x] 9. Update agent API tests for all agents
- [ ] 10. Manual testing - chat with each agent type (pending)

---

## Completion Criteria by Agent

| Agent | File | Criteria |
|-------|------|----------|
| SummaryAgent | Summary.md | Clear, Concise, Compelling |
| ChallengeAgent | Challenge.md | Specific, Measurable, Significant |
| ApproachAgent | Approach.md | Feasible, Differentiated, Addresses Challenge |
| StepsAgent | CoherentSteps.md | Concrete, Sequenced, Assignable |

---

## Files Created

### Backend (New)
- `backend/crabgrass/concepts/agents/summary_agent.py`
- `backend/crabgrass/concepts/agents/approach_agent.py`
- `backend/crabgrass/concepts/agents/steps_agent.py`

### Backend (Modified)
- `backend/crabgrass/ai/prompts.py` - Add evaluation prompts (enhanced system prompts + added evaluation prompts)
- `backend/crabgrass/concepts/agents/__init__.py` - Register all agents
- `backend/crabgrass/sync/synchronizations.py` - Updated comment for agent availability

### Tests (New)
- `backend/tests/test_summary_agent.py` - 9 tests
- `backend/tests/test_approach_agent.py` - 9 tests
- `backend/tests/test_steps_agent.py` - 9 tests

### Tests (Modified)
- `backend/tests/test_agent_api.py` - Updated to test all agents

---

## Test Results

All 104 tests pass (39 new agent tests + 65 existing tests).

---

*Started: 2026-01-03*
*Completed: 2026-01-03*
