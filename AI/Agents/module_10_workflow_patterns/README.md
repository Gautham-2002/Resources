# Module 10: Agentic Workflow Patterns

## The Complete Pattern Catalog

Every demo uses the **same task** (research + report) so you can directly compare patterns.

| # | Pattern | File | When to Use |
|---|---------|------|-------------|
| 1 | **Prompt Chaining** | `prompt_chaining.py` | Fixed sequential steps, each depends on the previous |
| 2 | **Router** | `router_pattern.py` | Input type determines which specialist handles it |
| 3 | **Fan-out / Fan-in** | `fan_out_fan_in.py` | Independent subtasks that can run in parallel |
| 4 | **Orchestrator-Worker** | `orchestrator_worker.py` | Complex tasks needing dynamic decomposition |
| 5 | **Evaluator-Optimizer** | `evaluator_optimizer.py` | Output quality must meet specific criteria |
| 6 | **Reflection** | `reflection_pattern.py` | Agent self-improves by critiquing its own work |
| 7 | **Map-Reduce** | `map_reduce.py` | Process large datasets in chunks, then aggregate |
| 8 | **Handoff** | `handoff_pattern.py` | Agent-to-agent delegation with context transfer |

### Decision Flowchart

```
Is the task a fixed sequence?
├── YES → Prompt Chaining
└── NO
    Does input type determine the handler?
    ├── YES → Router
    └── NO
        Are subtasks independent?
        ├── YES → Fan-out / Fan-in
        └── NO
            Is the task too complex to pre-plan?
            ├── YES → Orchestrator-Worker
            └── NO
                Does output need quality checks?
                ├── YES → Evaluator-Optimizer or Reflection
                └── NO
                    Is data too large for one call?
                    ├── YES → Map-Reduce
                    └── NO → Handoff (multi-specialist)
```

### Run Demos

```bash
python module_10_workflow_patterns/prompt_chaining.py
python module_10_workflow_patterns/router_pattern.py
# ... etc

# Or run the API:
uvicorn module_10_workflow_patterns.patterns_api:app --reload --port 8010
```
