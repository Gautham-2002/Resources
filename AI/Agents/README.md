# 🤖 Agent Orchestration & State Management

A comprehensive, hands-on learning project covering **11 modules** of agent orchestration patterns, workflow patterns, and framework comparison. Each module has runnable demos, detailed explanations, and FastAPI endpoints.

## ⚡ Quick Setup

```bash
# 1. Create and activate virtual environment
cd Agent-Orchestration
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your OpenAI API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

## 📚 Modules

| # | Module | Topic | Run Demo | Run API |
|---|--------|-------|----------|---------|
| 1 | [Orchestration Patterns](module_1_orchestration_patterns/README.md) | State Machines vs DAGs vs Dynamic Graphs | `python module_1_orchestration_patterns/state_machine_demo.py` | `uvicorn module_1_orchestration_patterns.comparison_api:app --port 8001` |
| 2 | [LangGraph Deep Dive](module_2_langgraph_deepdive/README.md) | Nodes, Edges, Conditional Routing, Subgraphs | `python module_2_langgraph_deepdive/basic_graph.py` | — |
| 3 | [Checkpointing](module_3_checkpointing/README.md) | Save/Resume Mid-Workflow (SQLite) | `python module_3_checkpointing/sqlite_checkpoint_demo.py` | `uvicorn module_3_checkpointing.checkpoint_api:app --port 8003` |
| 4 | [Human-in-the-Loop](module_4_human_in_the_loop/README.md) | Approval Gates, Feedback Loops | `python module_4_human_in_the_loop/approval_gate_demo.py` | `uvicorn module_4_human_in_the_loop.hitl_api:app --port 8004` |
| 5 | [Async Orchestration](module_5_async_orchestration/README.md) | Concurrent Agents with asyncio | `python module_5_async_orchestration/async_agents_demo.py` | `uvicorn module_5_async_orchestration.async_api:app --port 8005` |
| 6 | [Event-Driven](module_6_event_driven/README.md) | Webhooks, Durable Task Queues | `python module_6_event_driven/webhook_trigger_demo.py` | `uvicorn module_6_event_driven.event_api:app --port 8006` |
| 7 | [Saga Pattern](module_7_saga_pattern/README.md) | Distributed Transactions & Rollback | `python module_7_saga_pattern/saga_orchestrator.py` | `uvicorn module_7_saga_pattern.saga_api:app --port 8007` |
| 8 | [Idempotency](module_8_idempotency/README.md) | Safe Agent Retries & Deduplication | `python module_8_idempotency/idempotency_demo.py` | `uvicorn module_8_idempotency.idempotency_api:app --port 8008` |
| 9 | [Production Patterns](module_9_production_patterns/README.md) | Retry, Circuit Breaker, Observability, Rate Limiting | `python module_9_production_patterns/retry_circuit_breaker.py` | — |
| 10 | [Workflow Patterns](module_10_workflow_patterns/README.md) | Chaining, Router, Fan-out, Orchestrator, Reflection, Map-Reduce, Handoff | `python module_10_workflow_patterns/prompt_chaining.py` | `uvicorn module_10_workflow_patterns.patterns_api:app --port 8010` |
| 11 | [Framework Comparison](module_11_framework_comparison/README.md) | OpenAI SDK, LangChain, CrewAI, Pydantic AI, Google ADK, Anthropic | `python module_11_framework_comparison/openai_agents_demo.py` | — |

## 🧠 Concept Map

```
                    ┌──────────────────────────────────────┐
                    │    ORCHESTRATION PATTERNS (M1)        │
                    │  State Machine │ DAG │ Dynamic Graph  │
                    └─────────┬────────────────────────────┘
                              │
                    ┌─────────▼────────────────────────────┐
                    │    LANGGRAPH FRAMEWORK (M2)           │
                    │  Nodes │ Edges │ Routing │ Subgraphs  │
                    └─────────┬────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
  ┌─────────▼──────┐ ┌──────▼───────┐ ┌──────▼───────┐
  │ CHECKPOINTING  │ │    HITL      │ │    ASYNC     │
  │   (M3)         │ │    (M4)      │ │    (M5)      │
  │ Save/Resume    │ │ Approvals    │ │ Parallelism  │
  └────────────────┘ └──────────────┘ └──────────────┘
            │                 │                 │
            └─────────────────┼─────────────────┘
                              │
  ┌───────────────────────────┼───────────────────────────┐
  │                           │                           │
  ┌─────────▼──────┐ ┌──────▼───────┐ ┌────────▼───────┐
  │ EVENT-DRIVEN   │ │    SAGA      │ │  IDEMPOTENCY   │
  │   (M6)         │ │    (M7)      │ │    (M8)        │
  │ Webhooks/Queues│ │ Transactions │ │ Deduplication  │
  └────────────────┘ └──────────────┘ └────────────────┘
                              │
                    ┌─────────▼────────────────────────────┐
                    │   PRODUCTION PATTERNS (M9)            │
                    │ Retry │ Circuit Breaker │ Observability│
                    │ Rate Limiting │ Tracing               │
                    └──────────────────────────────────────┘
```

## 🎯 Recommended Learning Path

1. **Start with Module 1** — Understand the three fundamental patterns
2. **Module 2** — Learn LangGraph (the practical framework)
3. **Modules 3-4** — Add persistence and human oversight
4. **Module 5** — Speed things up with async
5. **Modules 6-8** — Production patterns for real-world systems
6. **Module 9** — Make it robust and observable
7. **Module 10** — Master all workflow patterns (Router, Fan-out, Orchestrator, etc.)
8. **Module 11** — Compare frameworks and learn to choose the right one

## 📁 Project Structure

```
Agent-Orchestration/
├── README.md                        ← You are here
├── requirements.txt
├── .env.example
├── shared/                          ← Shared utilities (config, LLM wrapper)
├── module_1_orchestration_patterns/ ← State Machine, DAG, Dynamic Graph
├── module_2_langgraph_deepdive/    ← LangGraph primitives
├── module_3_checkpointing/         ← SQLite checkpointing
├── module_4_human_in_the_loop/     ← Approval gates, feedback loops
├── module_5_async_orchestration/   ← Concurrent agents
├── module_6_event_driven/          ← Webhooks, task queues
├── module_7_saga_pattern/          ← Distributed transactions
├── module_8_idempotency/           ← Safe retries
├── module_9_production_patterns/   ← Retry, observability, rate limiting
├── module_10_workflow_patterns/    ← All agentic workflow patterns
└── module_11_framework_comparison/ ← 6 frameworks compared side-by-side
```

## 🛠️ Tech Stack

- **Python 3.11+** — Language
- **FastAPI** — REST APIs with auto-generated Swagger docs
- **OpenAI (GPT-4o-mini)** — LLM backend
- **LangGraph** — Graph-based orchestration framework
- **SQLite** — Checkpointing database
- **Rich** — Beautiful terminal output
- **asyncio** — Async/concurrent execution
- **OpenAI Agents SDK** — Multi-agent handoffs
- **LangChain** — LCEL chains and integrations
- **CrewAI** — Role-based multi-agent crews
- **Pydantic AI** — Type-safe agent outputs
- **Google ADK** — Google's agent framework
- **Anthropic** — Claude tool use and agentic loops
