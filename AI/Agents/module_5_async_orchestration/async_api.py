"""
=============================================================================
MODULE 5 — ASYNC API: FastAPI with Parallel Agent Execution
=============================================================================
RUN:
    uvicorn module_5_async_orchestration.async_api:app --reload --port 8005
    Then open http://localhost:8005/docs

ENDPOINTS:
    POST /research/parallel   — Fan-out to multiple agents, merge results
    POST /research/sequential — Same task, but one-at-a-time (for comparison)
=============================================================================
"""

import sys
import os
import asyncio
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel, Field
from shared.llm import achat

app = FastAPI(
    title="Module 5: Async Orchestration API",
    description="Compare parallel vs sequential agent execution via FastAPI.",
    version="1.0.0",
)


class ResearchRequest(BaseModel):
    topic: str = Field(
        default="Artificial Intelligence in Healthcare",
        description="The topic to research from multiple angles",
    )


ANGLES = [
    ("Technical Analysis", "Analyze the technical aspects of {topic}. Be concise."),
    ("Market Impact", "Analyze the market impact of {topic}. Be concise."),
    ("Future Predictions", "Predict the future developments of {topic}. Be concise."),
]


@app.post("/research/parallel", tags=["Async"])
async def research_parallel(req: ResearchRequest):
    """
    **Parallel research** — runs 3 research agents CONCURRENTLY.

    Uses asyncio.gather for true parallelism of I/O-bound LLM calls.
    Compare the timing with the /research/sequential endpoint.
    """
    start = time.time()

    tasks = [
        achat(
            prompt=prompt.format(topic=req.topic),
            system=f"You are a {name} agent.",
            max_tokens=200,
        )
        for name, prompt in ANGLES
    ]

    results = await asyncio.gather(*tasks)
    total = time.time() - start

    summary = await achat(
        prompt="Merge these into a 3-sentence executive summary:\n\n"
        + "\n\n".join(results),
        system="You are a research coordinator.",
        max_tokens=150,
    )

    return {
        "method": "parallel",
        "execution_time_seconds": round(total, 2),
        "summary": summary,
        "agent_results": [
            {"angle": ANGLES[i][0], "result": r} for i, r in enumerate(results)
        ],
    }


@app.post("/research/sequential", tags=["Async"])
async def research_sequential(req: ResearchRequest):
    """
    **Sequential research** — runs the same 3 agents ONE AT A TIME.

    Same task as /research/parallel, but sequential.
    Compare the timing to see the parallel speedup.
    """
    start = time.time()
    results = []

    for name, prompt in ANGLES:
        r = await achat(
            prompt=prompt.format(topic=req.topic),
            system=f"You are a {name} agent.",
            max_tokens=200,
        )
        results.append(r)

    total = time.time() - start

    summary = await achat(
        prompt="Merge these into a 3-sentence executive summary:\n\n"
        + "\n\n".join(results),
        system="You are a research coordinator.",
        max_tokens=150,
    )

    return {
        "method": "sequential",
        "execution_time_seconds": round(total, 2),
        "summary": summary,
        "agent_results": [
            {"angle": ANGLES[i][0], "result": r} for i, r in enumerate(results)
        ],
    }


@app.get("/", tags=["Overview"])
def root():
    return {
        "module": "Module 5: Async Orchestration",
        "description": "Compare parallel vs sequential agent execution",
        "try_this": "POST to /research/parallel then /research/sequential and compare execution_time_seconds",
        "docs": "/docs",
    }
