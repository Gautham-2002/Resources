"""
=============================================================================
MODULE 8 — IDEMPOTENCY API: FastAPI with Idempotent Endpoints
=============================================================================
RUN:
    uvicorn module_8_idempotency.idempotency_api:app --reload --port 8008
    Then open http://localhost:8008/docs

ENDPOINTS:
    POST /contacts         — Create a contact (with idempotency header)
    GET  /contacts         — List all contacts
    GET  /idempotency/stats — View deduplication statistics
=============================================================================
"""

import sys
import os
import hashlib
import json
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Header
from pydantic import BaseModel, Field
from shared.llm import chat

app = FastAPI(
    title="Module 8: Idempotency API",
    description="Demonstrates idempotent API endpoints for agent actions.",
    version="1.0.0",
)

# In-memory storage
contacts: list[dict] = []
idempotency_cache: dict[str, dict] = {}
stats = {"total_requests": 0, "duplicates_caught": 0, "new_records": 0}


class CreateContactRequest(BaseModel):
    name: str = Field(default="Alex Johnson", description="Contact name")
    email: str = Field(default="alex@techcorp.com", description="Contact email")
    company: str = Field(default="TechCorp", description="Company name")
    generate_note: bool = Field(
        default=True,
        description="Use LLM to generate a contact note",
    )


@app.post("/contacts", tags=["Contacts"])
def create_contact(
    req: CreateContactRequest,
    x_idempotency_key: str | None = Header(default=None, description="Unique key for deduplication"),
):
    """
    **Create a CRM contact** with idempotency protection.

    Pass `X-Idempotency-Key` header to enable deduplication.
    Try sending the SAME request with the SAME key multiple times —
    you'll see it returns the cached result instead of creating duplicates.
    """
    stats["total_requests"] += 1

    # Compute fingerprint
    fingerprint = hashlib.sha256(
        json.dumps({"name": req.name, "email": req.email, "company": req.company}, sort_keys=True).encode()
    ).hexdigest()[:12]

    # Check for duplicate
    key = x_idempotency_key or fingerprint
    if key in idempotency_cache:
        stats["duplicates_caught"] += 1
        cached = idempotency_cache[key].copy()
        cached["_idempotent"] = True
        cached["_message"] = "Duplicate detected — returning cached result"
        return cached

    # New record
    record = {
        "id": f"CRM-{uuid.uuid4().hex[:6].upper()}",
        "name": req.name,
        "email": req.email,
        "company": req.company,
        "created_at": datetime.now().isoformat(),
        "idempotency_key": key,
        "_idempotent": False,
    }

    if req.generate_note:
        note = chat(
            prompt=f"Write a 1 sentence CRM note for new contact {req.name} from {req.company}.",
            system="You are a CRM agent.",
            max_tokens=50,
        )
        record["note"] = note

    contacts.append(record)
    idempotency_cache[key] = record
    stats["new_records"] += 1

    return record


@app.get("/contacts", tags=["Contacts"])
def list_contacts():
    """**List all contacts** in the CRM."""
    return {"total": len(contacts), "contacts": contacts}


@app.get("/idempotency/stats", tags=["Idempotency"])
def get_stats():
    """
    **Deduplication statistics.**

    Shows how many duplicates were caught vs new records created.
    """
    return stats


@app.get("/", tags=["Overview"])
def root():
    return {
        "module": "Module 8: Idempotency",
        "description": "Idempotent API endpoints with deduplication",
        "try_this": [
            "1. POST /contacts with X-Idempotency-Key header",
            "2. Send the SAME request again with SAME key",
            "3. GET /idempotency/stats to see dedup count",
        ],
        "docs": "/docs",
    }
