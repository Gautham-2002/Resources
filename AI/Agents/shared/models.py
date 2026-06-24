"""
Shared Pydantic models used across modules.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class AgentTask(BaseModel):
    """Represents a task assigned to an agent."""
    task_id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class WorkflowStep(BaseModel):
    """Represents a single step in a workflow."""
    step_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float | None = None


class WorkflowRun(BaseModel):
    """Represents a complete workflow execution."""
    run_id: str
    workflow_name: str
    status: TaskStatus = TaskStatus.PENDING
    steps: list[WorkflowStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
