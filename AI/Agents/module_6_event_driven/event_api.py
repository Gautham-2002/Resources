"""
=============================================================================
MODULE 6 — EVENT API: FastAPI Event-Driven Agent Orchestration
=============================================================================
RUN:
    uvicorn module_6_event_driven.event_api:app --reload --port 8006
    Then open http://localhost:8006/docs

ENDPOINTS:
    POST /events/emit       — Emit an event (acts as webhook receiver)
    GET  /events/log        — View all processed events
    GET  /events/stats      — Queue statistics
=============================================================================
"""

import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel, Field
from shared.llm import chat

app = FastAPI(
    title="Module 6: Event-Driven Orchestration API",
    description="Emit events and watch agents process them automatically.",
    version="1.0.0",
)

event_log: list[dict] = []


class EventRequest(BaseModel):
    event_type: str = Field(
        default="code_push",
        description="Type of event: code_push, new_ticket, payment, custom",
    )
    payload: dict = Field(
        default={"repo": "myapp/backend", "message": "Fix auth bug", "files": ["auth.py"]},
        description="Event payload data",
    )


HANDLER_PROMPTS = {
    "code_push": ("Code Review Agent", "Review this code change and provide feedback: {payload}"),
    "new_ticket": ("Support Triage Agent", "Triage this support ticket and classify priority: {payload}"),
    "payment": ("Invoice Agent", "Generate an invoice summary for this payment: {payload}"),
}


@app.post("/events/emit", tags=["Events"])
def emit_event(req: EventRequest):
    """
    **Emit an event** — triggers the appropriate agent workflow.

    Simulates receiving a webhook from an external system.
    The server routes it to a specialized agent based on event_type.
    """
    event_id = str(uuid.uuid4())[:8]
    handler_info = HANDLER_PROMPTS.get(req.event_type)

    if handler_info:
        agent_name, prompt_template = handler_info
        result = chat(
            prompt=prompt_template.format(payload=str(req.payload)),
            system=f"You are a {agent_name}. Be concise.",
            max_tokens=200,
        )
        status = "processed"
    else:
        result = chat(
            prompt=f"Handle this event: type={req.event_type}, payload={req.payload}",
            system="You are a general-purpose agent. Handle the event appropriately.",
            max_tokens=200,
        )
        agent_name = "General Agent"
        status = "processed"

    entry = {
        "event_id": event_id,
        "event_type": req.event_type,
        "agent": agent_name,
        "status": status,
        "result": result,
        "timestamp": datetime.now().isoformat(),
    }
    event_log.append(entry)

    return entry


@app.get("/events/log", tags=["Events"])
def get_event_log():
    """**View all processed events** and their results."""
    return {"total": len(event_log), "events": event_log}


@app.get("/events/stats", tags=["Events"])
def get_stats():
    """**Event processing statistics.**"""
    by_type: dict[str, int] = {}
    for e in event_log:
        by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1
    return {"total_events": len(event_log), "by_type": by_type}


@app.get("/", tags=["Overview"])
def root():
    return {
        "module": "Module 6: Event-Driven Orchestration",
        "endpoints": {
            "POST /events/emit": "Emit an event to trigger an agent",
            "GET /events/log": "View processed events",
            "GET /events/stats": "Event statistics",
        },
        "supported_events": list(HANDLER_PROMPTS.keys()) + ["custom (any type)"],
        "docs": "/docs",
    }
