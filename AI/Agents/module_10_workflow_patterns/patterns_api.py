"""
=============================================================================
MODULE 10 — PATTERNS API: FastAPI to run any workflow pattern
=============================================================================
RUN:
    uvicorn module_10_workflow_patterns.patterns_api:app --reload --port 8010
    Then open http://localhost:8010/docs

ENDPOINTS:
    POST /patterns/{pattern_name}  — Run a specific pattern
    GET  /patterns                 — List all available patterns
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from module_10_workflow_patterns.prompt_chaining import run_prompt_chain
from module_10_workflow_patterns.router_pattern import route_and_handle
from module_10_workflow_patterns.orchestrator_worker import run_orchestrator_worker
from module_10_workflow_patterns.evaluator_optimizer import run_evaluator_optimizer
from module_10_workflow_patterns.reflection_pattern import run_reflection
from module_10_workflow_patterns.map_reduce import run_map_reduce, DOCUMENTS

app = FastAPI(
    title="Module 10: Workflow Patterns API",
    description="Run and compare agentic workflow patterns via REST.",
    version="1.0.0",
)


class PatternRequest(BaseModel):
    topic: str = Field(
        default="The Future of AI Agents",
        description="Topic or input for the pattern",
    )


PATTERN_INFO = {
    "prompt_chaining": {
        "description": "Sequential pipeline: Research → Outline → Draft → Polish",
        "when": "Fixed sequential steps, each depends on the previous",
    },
    "router": {
        "description": "Classify input → route to specialist agent",
        "when": "Different inputs need different handling",
    },
    "orchestrator_worker": {
        "description": "Central planner decomposes task → workers execute → assemble",
        "when": "Complex tasks needing dynamic decomposition",
    },
    "evaluator_optimizer": {
        "description": "Generate → Evaluate → Refine loop until quality meets threshold",
        "when": "Output quality must meet specific criteria",
    },
    "reflection": {
        "description": "Agent self-critiques and iteratively improves its own output",
        "when": "Improvement without a separate evaluator",
    },
    "map_reduce": {
        "description": "Split data → process chunks independently → aggregate results",
        "when": "Processing data too large for one call",
    },
}


@app.get("/patterns", tags=["Patterns"])
def list_patterns():
    """**List all available patterns** with descriptions and use cases."""
    return PATTERN_INFO


@app.post("/patterns/prompt_chaining", tags=["Patterns"])
def run_chaining(req: PatternRequest):
    """Run the **Prompt Chaining** pattern (sequential pipeline)."""
    result = run_prompt_chain(req.topic)
    return {"pattern": "prompt_chaining", "result": result}


@app.post("/patterns/router", tags=["Patterns"])
def run_router(req: PatternRequest):
    """Run the **Router** pattern (classify and route to specialist)."""
    result = route_and_handle(req.topic)
    return {"pattern": "router", "result": result}


@app.post("/patterns/orchestrator_worker", tags=["Patterns"])
def run_orchestrator(req: PatternRequest):
    """Run the **Orchestrator-Worker** pattern (dynamic task decomposition)."""
    result = run_orchestrator_worker(req.topic)
    return {"pattern": "orchestrator_worker", "result": result}


@app.post("/patterns/evaluator_optimizer", tags=["Patterns"])
def run_evaluator(req: PatternRequest):
    """Run the **Evaluator-Optimizer** pattern (generate → evaluate → refine)."""
    result = run_evaluator_optimizer(req.topic, max_iterations=2)
    return {"pattern": "evaluator_optimizer", "result": result}


@app.post("/patterns/reflection", tags=["Patterns"])
def run_reflect(req: PatternRequest):
    """Run the **Reflection** pattern (self-critique and improve)."""
    result = run_reflection(req.topic, reflection_rounds=2)
    return {"pattern": "reflection", "result": result}


@app.post("/patterns/map_reduce", tags=["Patterns"])
def run_mapreduce(req: PatternRequest):
    """Run the **Map-Reduce** pattern (using sample documents)."""
    result = run_map_reduce(DOCUMENTS, req.topic)
    return {"pattern": "map_reduce", "result": result}


@app.get("/", tags=["Overview"])
def root():
    return {
        "module": "Module 10: Workflow Patterns",
        "patterns": list(PATTERN_INFO.keys()),
        "usage": "POST /patterns/{name} with a topic",
        "docs": "/docs",
    }
