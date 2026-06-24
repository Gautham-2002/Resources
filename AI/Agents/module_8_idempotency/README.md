# Module 8: Idempotency in Agent Actions

## Why Idempotency?

When agents retry failed actions (due to timeouts, crashes, or network issues),
they might execute the **same action twice**. Without idempotency:

- CRM: Creates duplicate customer records
- Billing: Charges the customer twice
- Email: Sends the same email multiple times

**Idempotency** ensures that executing an action multiple times has the
**same effect as executing it once**.

### Key Techniques

| Technique | How It Works | Use Case |
|-----------|-------------|----------|
| **Idempotency Key** | Unique ID per request, deduplicate | API calls |
| **Request Fingerprint** | Hash request content for dedup | Retries |
| **Result Cache** | Store results, return cached on retry | All |

### Demos

1. **Idempotency Demo** — `python module_8_idempotency/idempotency_demo.py`
   - CRM simulation with deduplication
   - Shows what happens WITH and WITHOUT idempotency

2. **Idempotency API** — `uvicorn module_8_idempotency.idempotency_api:app --reload --port 8008`
   - FastAPI with idempotent endpoints
   - Docs: http://localhost:8008/docs
