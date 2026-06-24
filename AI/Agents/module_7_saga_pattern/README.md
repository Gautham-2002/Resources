# Module 7: Saga Pattern

## Why Sagas?

When agent workflows span **multiple services** (CRM, email, billing), you can't use
traditional database transactions. If step 3 fails, you need to **undo steps 1 and 2**.

The Saga Pattern solves this with **compensating actions** — for every action,
you define a rollback that undoes it.

### Example

```
Step 1: Create CRM record    → Rollback: Delete CRM record
Step 2: Send welcome email   → Rollback: Send cancellation email
Step 3: Provision account     → Rollback: Deprovision account
```

If Step 3 fails, the saga runs rollbacks for Steps 2 and 1 **in reverse order**.

### Demos

1. **Saga Orchestrator** — `python module_7_saga_pattern/saga_orchestrator.py`
   - Customer onboarding with automatic rollback on failure

2. **Saga API** — `uvicorn module_7_saga_pattern.saga_api:app --reload --port 8007`
   - REST API to execute sagas and watch rollbacks
   - Docs: http://localhost:8007/docs
