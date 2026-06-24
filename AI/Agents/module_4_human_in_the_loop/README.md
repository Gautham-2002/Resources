# Module 4: Human-in-the-Loop (HITL)

## Why HITL?

Not everything should be autonomous. HITL lets agents **pause and wait for human input** at critical points:
- **Approval gates**: Agent drafts an email, human approves/rejects before sending
- **Feedback loops**: Agent produces output, human refines, agent improves
- **Escalation**: Agent recognizes it's outside its capability

### Demos

1. **Approval Gate** — `python module_4_human_in_the_loop/approval_gate_demo.py`
   - Agent drafts, waits for human approval via CLI, then acts

2. **Feedback Loop** — `python module_4_human_in_the_loop/feedback_loop_demo.py`
   - Agent → human feedback → agent improves → repeat

3. **HITL API** — `uvicorn module_4_human_in_the_loop.hitl_api:app --reload --port 8004`
   - REST API with `/start`, `/pending`, `/approve/{id}`, `/reject/{id}`
   - Docs: http://localhost:8004/docs
