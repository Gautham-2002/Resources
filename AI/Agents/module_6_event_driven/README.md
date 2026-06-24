# Module 6: Event-Driven Orchestration

## Why Event-Driven?

Instead of polling or direct invocation, event-driven systems **react to events**:
- A webhook fires → triggers an agent workflow
- A message lands in a queue → worker picks it up
- This decouples **producers** (who trigger work) from **consumers** (who do the work)

### Demos

1. **Webhook Trigger** — `python module_6_event_driven/webhook_trigger_demo.py`
   - FastAPI receives webhooks → triggers appropriate agent workflows

2. **Task Queue** — `python module_6_event_driven/task_queue_demo.py`
   - In-memory durable queue with retry semantics (simulates SQS/Kafka)

3. **Event API** — `uvicorn module_6_event_driven.event_api:app --reload --port 8006`
   - Complete event-driven system: produce events, consume with agents
   - Docs: http://localhost:8006/docs
