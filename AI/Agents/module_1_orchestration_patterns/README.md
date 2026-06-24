# Module 1: Orchestration Patterns

## State Machines vs DAGs vs Dynamic Graphs

**Core Question:** How does your agent decide what to do next?

### 🔄 State Machine (Finite State Machine / FSM)
- **Best for:** Fixed, well-known workflows where transitions are predetermined 
- **Example:** Order processing (New → Validated → Fulfilled → Shipped)
- **Predictability:** HIGH — Every state and transition is known at design time
- **Run:** `python module_1_orchestration_patterns/state_machine_demo.py`

### 📊 DAG (Directed Acyclic Graph)
- **Best for:** Multi-step pipelines with known dependencies but flexible execution order
- **Example:** Data pipeline (fetch → clean → analyze → summarize) with parallel branches
- **Predictability:** MEDIUM — Steps are known but execution order may vary
- **Run:** `python module_1_orchestration_patterns/dag_demo.py`

### 🌐 Dynamic Graph
- **Best for:** Unpredictable, LLM-driven workflows where next step depends on runtime decisions
- **Example:** Research agent that decides at each step whether to search, analyze, or conclude
- **Predictability:** LOW — The graph shape is determined at runtime by the LLM
- **Run:** `python module_1_orchestration_patterns/dynamic_graph_demo.py`

### 🏁 Comparison API
- **Compare all three** patterns side-by-side via FastAPI
- **Run:** `uvicorn module_1_orchestration_patterns.comparison_api:app --reload --port 8001`
- **Docs:** http://localhost:8001/docs

## When to Choose Which?

| Pattern | Predictability | Flexibility | Complexity | Use When |
|---------|---------------|-------------|------------|----------|
| State Machine | High | Low | Low | You know every possible state/transition |
| DAG | Medium | Medium | Medium | Known steps with dependency ordering |
| Dynamic Graph | Low | High | High | LLM decides the workflow at runtime |
