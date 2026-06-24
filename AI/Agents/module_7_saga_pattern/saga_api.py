"""
=============================================================================
MODULE 7 — SAGA API: FastAPI for Saga Pattern
=============================================================================
RUN:
    uvicorn module_7_saga_pattern.saga_api:app --reload --port 8007
    Then open http://localhost:8007/docs

ENDPOINTS:
    POST /saga/run           — Run a saga (optionally inject a failure)
    GET  /saga/history       — View all saga executions
=============================================================================
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel, Field

from module_7_saga_pattern.saga_orchestrator import run_saga

app = FastAPI(
    title="Module 7: Saga Pattern API",
    description="Execute distributed agent transactions with automatic rollback.",
    version="1.0.0",
)

saga_history: list[dict] = []


class SagaRequest(BaseModel):
    name: str = Field(default="Customer Onboarding", description="Saga name")
    fail_at_step: int | None = Field(
        default=None,
        description="Step number to fail at (0-indexed). None = all succeed. E.g., 2 = fail at step 3.",
    )


@app.post("/saga/run", tags=["Saga"])
def execute_saga(req: SagaRequest):
    """
    **Run a saga.** Optionally inject a failure at a specific step.

    - `fail_at_step=null` → Happy path (all steps succeed)
    - `fail_at_step=2` → Step 3 fails → automatic rollback of steps 1 & 2
    """
    result = run_saga(req.name, req.fail_at_step)
    saga_history.append(result)
    return result


@app.get("/saga/history", tags=["Saga"])
def get_history():
    """**View all saga executions** and their outcomes."""
    return {"total": len(saga_history), "sagas": saga_history}


@app.get("/", tags=["Overview"])
def root():
    return {
        "module": "Module 7: Saga Pattern",
        "description": "Distributed transactions with rollback",
        "try_this": [
            "POST /saga/run with fail_at_step=null (happy path)",
            "POST /saga/run with fail_at_step=2 (failure + rollback)",
        ],
        "docs": "/docs",
    }
