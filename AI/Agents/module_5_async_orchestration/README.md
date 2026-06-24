# Module 5: Async Orchestration

## Why Async?

When agents make LLM calls, they spend most of their time **waiting for responses**.
Running agents sequentially wastes time. Running them **concurrently** with asyncio
can reduce workflow time by 60-80%.

### Demos

1. **Async Agents** — `python module_5_async_orchestration/async_agents_demo.py`
   - 3 research agents run IN PARALLEL, results merged by coordinator
   - Compare: sequential (30s) vs parallel (10s) execution

2. **Thread Pool Demo** — `python module_5_async_orchestration/thread_pool_demo.py`
   - Mix async code with blocking OpenAI calls via ThreadPoolExecutor

3. **Async API** — `uvicorn module_5_async_orchestration.async_api:app --reload --port 8005`
   - FastAPI with parallel agent fan-out endpoint
   - Docs: http://localhost:8005/docs
