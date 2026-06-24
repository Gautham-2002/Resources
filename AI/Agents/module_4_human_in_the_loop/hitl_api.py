"""
=============================================================================
MODULE 4 — HITL API: FastAPI for Human-in-the-Loop Workflows
=============================================================================
CONCEPT:
    A REST API that manages HITL workflows:
    - Start a workflow → agent drafts → workflow goes to "pending" state
    - Human reviews via API → approves/rejects/provides feedback
    - Agent continues or stops based on human decision

    This is how HITL works in PRODUCTION — via APIs, not CLI prompts.

RUN:
    uvicorn module_4_human_in_the_loop.hitl_api:app --reload --port 8004
    Then open http://localhost:8004/docs

FLOW:
    1. POST /tasks/start  → Creates a task, agent drafts, returns pending task
    2. GET  /tasks/pending → List all tasks waiting for human review
    3. POST /tasks/{id}/approve → Approve the task
    4. POST /tasks/{id}/reject  → Reject the task
    5. POST /tasks/{id}/feedback → Send feedback, agent revises
=============================================================================
"""

import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from shared.llm import chat

app = FastAPI(
    title="Module 4: Human-in-the-Loop API",
    description="REST API for managing agent workflows that require human approval.",
    version="1.0.0",
)


# =============================================================================
# In-memory task store (in production, use a database)
# =============================================================================
class HITLTask:
    def __init__(self, task_id: str, request: str):
        self.task_id = task_id
        self.request = request
        self.status = "pending"  # pending | approved | rejected
        self.draft = ""
        self.feedback_history: list[dict] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.revision_count = 0

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "request": self.request,
            "status": self.status,
            "draft": self.draft,
            "feedback_history": self.feedback_history,
            "revision_count": self.revision_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


tasks: dict[str, HITLTask] = {}


# =============================================================================
# Request Models
# =============================================================================
class StartTaskRequest(BaseModel):
    request: str = Field(
        default="Write a professional email apologizing for a service outage",
        description="What the agent should do",
    )

class FeedbackRequest(BaseModel):
    feedback: str = Field(description="Specific feedback for the agent to address")


# =============================================================================
# Endpoints
# =============================================================================
@app.post("/tasks/start", tags=["HITL"])
def start_task(req: StartTaskRequest):
    """
    **Start a new HITL task.**
    
    The agent generates an initial draft, then the task goes to 'pending' status.
    Use `/tasks/{id}/approve`, `/tasks/{id}/reject`, or `/tasks/{id}/feedback` to respond.
    """
    task_id = str(uuid.uuid4())[:8]
    task = HITLTask(task_id, req.request)
    
    # Agent generates initial draft
    draft = chat(
        prompt=f"Complete this task: {req.request}",
        system="You are a professional assistant. Produce high-quality output.",
        max_tokens=400,
    )
    task.draft = draft
    task.status = "pending"
    tasks[task_id] = task
    
    return {
        "message": "Task created and awaiting human review",
        "task": task.to_dict(),
        "next_actions": {
            "approve": f"POST /tasks/{task_id}/approve",
            "reject": f"POST /tasks/{task_id}/reject",
            "feedback": f"POST /tasks/{task_id}/feedback",
        },
    }


@app.get("/tasks/pending", tags=["HITL"])
def get_pending_tasks():
    """**List all tasks** that are waiting for human review."""
    pending = [t.to_dict() for t in tasks.values() if t.status == "pending"]
    return {"pending_count": len(pending), "tasks": pending}


@app.post("/tasks/{task_id}/approve", tags=["HITL"])
def approve_task(task_id: str):
    """
    **Approve a pending task.**
    
    In a real system, this would trigger the agent to execute
    the approved action (send email, make API call, etc).
    """
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail=f"Task is {task.status}, not pending")
    
    task.status = "approved"
    task.updated_at = datetime.now().isoformat()
    
    return {
        "message": "Task APPROVED — agent would now execute the action",
        "task": task.to_dict(),
    }


@app.post("/tasks/{task_id}/reject", tags=["HITL"])
def reject_task(task_id: str):
    """**Reject a pending task.** The draft is discarded."""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail=f"Task is {task.status}, not pending")
    
    task.status = "rejected"
    task.updated_at = datetime.now().isoformat()
    
    return {"message": "Task REJECTED — draft discarded", "task": task.to_dict()}


@app.post("/tasks/{task_id}/feedback", tags=["HITL"])
def send_feedback(task_id: str, req: FeedbackRequest):
    """
    **Send feedback on a pending task.**
    
    The agent will REVISE its draft based on your feedback,
    and the task returns to 'pending' status for another review.
    """
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail=f"Task is {task.status}, not pending")
    
    task.feedback_history.append({
        "feedback": req.feedback,
        "previous_draft": task.draft[:200] + "...",
        "timestamp": datetime.now().isoformat(),
    })
    
    # Agent revises based on feedback
    revised = chat(
        prompt=f"""Revise your previous work based on feedback.

Original request: {task.request}
Previous draft: {task.draft}
Feedback: {req.feedback}

Write the improved version.""",
        system="You are a professional assistant. Address ALL feedback points carefully.",
        max_tokens=400,
    )
    
    task.draft = revised
    task.revision_count += 1
    task.updated_at = datetime.now().isoformat()
    
    return {
        "message": f"Draft revised (revision {task.revision_count}) — awaiting review again",
        "task": task.to_dict(),
        "next_actions": {
            "approve": f"POST /tasks/{task_id}/approve",
            "reject": f"POST /tasks/{task_id}/reject",
            "feedback": f"POST /tasks/{task_id}/feedback",
        },
    }


@app.get("/tasks/{task_id}", tags=["HITL"])
def get_task(task_id: str):
    """**Get task details** including draft, feedback history, and status."""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@app.get("/tasks", tags=["HITL"])
def list_all_tasks():
    """**List all tasks** regardless of status."""
    return {"total": len(tasks), "tasks": [t.to_dict() for t in tasks.values()]}


@app.get("/", tags=["Overview"])
def root():
    return {
        "module": "Module 4: Human-in-the-Loop",
        "description": "REST API for HITL workflows with approval gates and feedback loops",
        "flow": [
            "1. POST /tasks/start — Agent drafts, task goes to 'pending'",
            "2. GET /tasks/pending — See what needs your review",
            "3. POST /tasks/{id}/approve or /reject or /feedback",
        ],
        "docs": "/docs",
    }
