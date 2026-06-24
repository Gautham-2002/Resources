"""
=============================================================================
MODULE 1 — COMPARISON API: All Three Patterns Side-by-Side
=============================================================================
CONCEPT:
    A FastAPI server that lets you run all three orchestration patterns
    and compare their behavior on similar tasks.

RUN:
    uvicorn module_1_orchestration_patterns.comparison_api:app --reload --port 8001
    
    Then open http://localhost:8001/docs to see the interactive Swagger UI.

ENDPOINTS:
    POST /state-machine    — Run the FSM order processing demo
    POST /dag              — Run the DAG data pipeline demo
    POST /dynamic-graph    — Run the dynamic graph research demo
    GET  /comparison       — Get a comparison summary of all three patterns
=============================================================================
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel, Field

# Import the demo classes and functions
from module_1_orchestration_patterns.state_machine_demo import OrderAgent
from module_1_orchestration_patterns.dag_demo import (
    DAGExecutor, fetch_data, clean_data, analyze_trends, analyze_outliers, generate_report
)
from module_1_orchestration_patterns.dynamic_graph_demo import DynamicGraphAgent


# =============================================================================
# FastAPI App
# =============================================================================
app = FastAPI(
    title="Module 1: Orchestration Patterns Comparison",
    description=(
        "Compare State Machines, DAGs, and Dynamic Graphs — "
        "three fundamental patterns for agent orchestration. "
        "Each endpoint runs the same kind of task through a different pattern."
    ),
    version="1.0.0",
)


# =============================================================================
# Request/Response Models
# =============================================================================
class StateMachineRequest(BaseModel):
    order_details: str = Field(
        default="3 units of iPhone 16 Pro, shipping to San Francisco, CA",
        description="The order to process through the state machine",
    )

class DAGRequest(BaseModel):
    run_pipeline: bool = Field(
        default=True,
        description="Set to true to run the data analysis pipeline",
    )

class DynamicGraphRequest(BaseModel):
    question: str = Field(
        default="What are the pros and cons of serverless architecture?",
        description="The research question for the dynamic graph agent",
    )
    max_steps: int = Field(default=5, ge=2, le=8, description="Maximum steps allowed")


# =============================================================================
# Endpoints
# =============================================================================
@app.post("/state-machine", tags=["Patterns"])
def run_state_machine(req: StateMachineRequest):
    """
    **State Machine Pattern**
    
    Runs an order through a fixed state machine:
    new → validating → validated → processing_payment → paid → fulfilling → shipped
    
    The workflow is COMPLETELY PREDICTABLE. Every transition is defined upfront.
    """
    agent = OrderAgent(req.order_details)
    result = agent.run()
    return {
        "pattern": "state_machine",
        "description": "Fixed states and transitions — fully predictable",
        **result,
    }


@app.post("/dag", tags=["Patterns"])
def run_dag(req: DAGRequest):
    """
    **DAG Pattern**
    
    Runs a data analysis pipeline as a Directed Acyclic Graph:
    fetch → clean → [analyze_trends || analyze_outliers] → generate_report
    
    Independent steps (analyze_trends, analyze_outliers) CAN run in parallel.
    """
    dag = DAGExecutor()
    dag.add_node("fetch_data", fetch_data)
    dag.add_node("clean_data", clean_data, dependencies=["fetch_data"])
    dag.add_node("analyze_trends", analyze_trends, dependencies=["clean_data"])
    dag.add_node("analyze_outliers", analyze_outliers, dependencies=["clean_data"])
    dag.add_node("generate_report", generate_report, dependencies=["analyze_trends", "analyze_outliers"])
    
    results = dag.execute()
    
    return {
        "pattern": "dag",
        "description": "Steps with explicit dependencies — allows parallelism",
        "report": results["generate_report"],
        "execution_log": dag.execution_log,
        "all_results": {k: v[:200] for k, v in results.items()},
    }


@app.post("/dynamic-graph", tags=["Patterns"])
def run_dynamic_graph(req: DynamicGraphRequest):
    """
    **Dynamic Graph Pattern**
    
    A research agent that BUILDS ITS OWN WORKFLOW at runtime.
    The LLM decides at each step what to do next: SEARCH, ANALYZE, SYNTHESIZE, or CONCLUDE.
    
    Run this multiple times — you'll see DIFFERENT execution paths!
    """
    agent = DynamicGraphAgent(req.question, max_steps=req.max_steps)
    result = agent.run()
    return {
        "pattern": "dynamic_graph",
        "description": "LLM decides the workflow at runtime — maximum flexibility",
        **result,
    }


@app.get("/comparison", tags=["Overview"])
def get_comparison():
    """
    **Pattern Comparison**
    
    Returns a side-by-side comparison of all three orchestration patterns.
    Use this to understand when to choose which pattern.
    """
    return {
        "comparison": [
            {
                "pattern": "State Machine",
                "predictability": "HIGH",
                "flexibility": "LOW",
                "parallelism": "NO",
                "best_for": "Fixed workflows (order processing, approvals, ticket handling)",
                "example": "new → validating → validated → payment → shipped",
                "pros": ["Fully predictable", "Easy to audit", "Good for compliance"],
                "cons": ["Cannot handle unexpected paths", "Requires code changes for new states"],
                "try_endpoint": "POST /state-machine",
            },
            {
                "pattern": "DAG (Directed Acyclic Graph)",
                "predictability": "MEDIUM",
                "flexibility": "MEDIUM",
                "parallelism": "YES",
                "best_for": "Data pipelines, multi-step processing with dependencies",
                "example": "fetch → clean → [trends || outliers] → report",
                "pros": ["Parallel execution", "Explicit dependencies", "Deterministic ordering"],
                "cons": ["No loops/iteration", "Fixed structure at design time"],
                "try_endpoint": "POST /dag",
            },
            {
                "pattern": "Dynamic Graph",
                "predictability": "LOW",
                "flexibility": "HIGH",
                "parallelism": "VARIES",
                "best_for": "Research, exploration, novel problems where steps are unknown",
                "example": "START → SEARCH → ANALYZE → SEARCH → SYNTHESIZE → CONCLUDE",
                "pros": ["Maximum flexibility", "Handles novel tasks", "Adapts to context"],
                "cons": ["Unpredictable cost/time", "Hard to debug", "Needs guardrails"],
                "try_endpoint": "POST /dynamic-graph",
            },
        ],
        "choosing_guide": {
            "use_state_machine": "When you know ALL possible states and transitions upfront",
            "use_dag": "When steps are known but have dependency relationships",
            "use_dynamic_graph": "When the LLM needs to decide what to do at each step",
        },
    }


@app.get("/", tags=["Overview"])
def root():
    """Welcome page with links to all endpoints."""
    return {
        "module": "Module 1: Orchestration Patterns",
        "description": "Compare State Machines, DAGs, and Dynamic Graphs",
        "endpoints": {
            "GET /comparison": "Side-by-side comparison of all patterns",
            "POST /state-machine": "Run order processing with FSM",
            "POST /dag": "Run data pipeline with DAG",
            "POST /dynamic-graph": "Run research with dynamic graph",
        },
        "docs": "/docs",
    }
