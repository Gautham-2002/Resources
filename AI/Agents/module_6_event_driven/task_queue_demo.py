"""
=============================================================================
MODULE 6 — DEMO 2: Durable Task Queue (Simulating SQS/Kafka)
=============================================================================
CONCEPT:
    A durable task queue sits between event producers and consumers:

    Producer → [QUEUE] → Consumer (Agent)

    The queue provides:
    - Durability: tasks survive crashes
    - Retry: failed tasks are retried
    - Ordering: tasks are processed in order
    - Backpressure: consumers process at their own speed

    This demo builds an in-memory queue with these properties
    (no external dependencies like SQS/Kafka needed).

RUN:
    python module_6_event_driven/task_queue_demo.py
=============================================================================
"""

import sys
import os
import uuid
from collections import deque
from datetime import datetime
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Build the durable task queue
# =============================================================================
class TaskState(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"  # Failed too many times


class QueuedTask:
    """A task in the queue with retry metadata."""

    def __init__(self, task_type: str, payload: dict, max_retries: int = 3):
        self.task_id = str(uuid.uuid4())[:8]
        self.task_type = task_type
        self.payload = payload
        self.state = TaskState.QUEUED
        self.max_retries = max_retries
        self.retry_count = 0
        self.error: str | None = None
        self.result: dict | None = None
        self.created_at = datetime.now()
        self.completed_at: datetime | None = None


class DurableTaskQueue:
    """
    An in-memory durable task queue with retry semantics.

    In production, replace this with:
    - AWS SQS
    - Apache Kafka
    - Redis Streams
    - RabbitMQ

    The CONCEPT is the same regardless of implementation.
    """

    def __init__(self, name: str):
        self.name = name
        self.queue: deque[QueuedTask] = deque()
        self.processing: dict[str, QueuedTask] = {}
        self.completed: list[QueuedTask] = []
        self.dead_letter: list[QueuedTask] = []
        self.handlers: dict[str, callable] = {}

    def register_handler(self, task_type: str, handler):
        """Register a handler function for a task type."""
        self.handlers[task_type] = handler

    def enqueue(self, task_type: str, payload: dict) -> QueuedTask:
        """Add a task to the queue."""
        task = QueuedTask(task_type, payload)
        self.queue.append(task)
        console.print(f"  [cyan]📥 Enqueued:[/cyan] {task.task_id} ({task_type})")
        return task

    def process_next(self) -> QueuedTask | None:
        """
        Process the next task in the queue.

        KEY PATTERN:
        1. Dequeue the task
        2. Mark as "processing"
        3. Execute the handler
        4. On success: mark as "completed"
        5. On failure: retry or send to dead letter queue
        """
        if not self.queue:
            return None

        task = self.queue.popleft()
        task.state = TaskState.PROCESSING
        self.processing[task.task_id] = task

        handler = self.handlers.get(task.task_type)
        if not handler:
            task.state = TaskState.FAILED
            task.error = f"No handler for task type: {task.task_type}"
            self.dead_letter.append(task)
            del self.processing[task.task_id]
            return task

        try:
            console.print(
                f"  [yellow]⚙️  Processing:[/yellow] {task.task_id} (attempt {task.retry_count + 1}/{task.max_retries + 1})"
            )
            task.result = handler(task.payload)
            task.state = TaskState.COMPLETED
            task.completed_at = datetime.now()
            self.completed.append(task)
            console.print(f"  [green]✅ Completed:[/green] {task.task_id}")

        except Exception as e:
            task.retry_count += 1
            task.error = str(e)

            if task.retry_count <= task.max_retries:
                # RETRY: Put back in queue
                task.state = TaskState.QUEUED
                self.queue.append(task)
                console.print(
                    f"  [yellow]🔄 Retrying:[/yellow] {task.task_id} (attempt {task.retry_count}/{task.max_retries})"
                )
            else:
                # DEAD LETTER: Too many failures
                task.state = TaskState.DEAD_LETTER
                self.dead_letter.append(task)
                console.print(f"  [red]💀 Dead Letter:[/red] {task.task_id} — {e}")

        if task.task_id in self.processing:
            del self.processing[task.task_id]

        return task

    def process_all(self):
        """Process all tasks in the queue."""
        while self.queue:
            self.process_next()

    def stats(self) -> dict:
        """Get queue statistics."""
        return {
            "queued": len(self.queue),
            "processing": len(self.processing),
            "completed": len(self.completed),
            "dead_letter": len(self.dead_letter),
        }


# =============================================================================
# Step 2: Define agent handlers
# =============================================================================
def summarize_handler(payload: dict) -> dict:
    """Agent that summarizes text."""
    result = chat(
        prompt=f"Summarize this in 2 sentences: {payload['text']}",
        system="You are a summarization agent.",
        max_tokens=100,
    )
    return {"summary": result}


def classify_handler(payload: dict) -> dict:
    """Agent that classifies text."""
    result = chat(
        prompt=f"Classify the sentiment of this text as positive/negative/neutral: {payload['text']}",
        system="You are a sentiment classifier.",
        max_tokens=50,
    )
    return {"classification": result}


def failing_handler(payload: dict) -> dict:
    """An intentionally failing handler to demonstrate retry and dead letter."""
    raise Exception("Simulated external API failure!")


# =============================================================================
# Step 3: Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Durable Task Queue Demo[/bold]\n\n"
            "This demo shows a task queue with:\n"
            "  • Message ordering (FIFO)\n"
            "  • Automatic retries on failure\n"
            "  • Dead letter queue for permanently failed tasks\n\n"
            "In production, replace with SQS, Kafka, or Redis Streams.",
            title="📖 What You'll See",
            border_style="yellow",
        )
    )

    # Create the queue
    queue = DurableTaskQueue("agent-tasks")

    # Register handlers
    queue.register_handler("summarize", summarize_handler)
    queue.register_handler("classify", classify_handler)
    queue.register_handler("failing_task", failing_handler)

    # Enqueue tasks
    console.print(
        Panel("Enqueueing tasks...", title="📥 Producer", border_style="blue")
    )

    queue.enqueue(
        "summarize",
        {
            "text": "AI agents are autonomous systems that can perform tasks on behalf of users. They use LLMs for reasoning and can call tools and APIs."
        },
    )
    queue.enqueue(
        "classify",
        {
            "text": "I absolutely love this product, it has changed my workflow completely!"
        },
    )
    queue.enqueue(
        "failing_task", {"text": "This will fail to demonstrate retry semantics."}
    )
    queue.enqueue(
        "summarize",
        {
            "text": "Event-driven architecture decouples producers from consumers, enabling scalable and resilient systems."
        },
    )

    # Process all tasks
    console.print(
        Panel(
            "Processing queue...",
            title="⚙️  Consumer (Agent Workers)",
            border_style="magenta",
        )
    )
    queue.process_all()

    # Show stats
    stats = queue.stats()
    table = Table(title="Queue Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="yellow")

    table.add_row("Completed", f"[green]{stats['completed']}[/green]")
    table.add_row("Dead Letter (failed)", f"[red]{stats['dead_letter']}[/red]")
    table.add_row("Still Queued", str(stats["queued"]))

    console.print(table)

    # Show completed results
    console.print("\n[bold]Completed Tasks:[/bold]")
    for task in queue.completed:
        console.print(
            f"  ✅ {task.task_id} ({task.task_type}): {str(task.result)[:80]}..."
        )

    console.print("\n[bold]Dead Letter Queue:[/bold]")
    for task in queue.dead_letter:
        console.print(f"  💀 {task.task_id} ({task.task_type}): {task.error}")

    console.print(
        Panel(
            "[bold]KEY CONCEPTS:[/bold]\n"
            "1. [cyan]Enqueue[/cyan] — Producer adds tasks (decoupled from processing)\n"
            "2. [cyan]Process[/cyan] — Consumer picks up and executes tasks\n"
            "3. [cyan]Retry[/cyan] — Failed tasks are re-queued automatically\n"
            "4. [cyan]Dead Letter Queue[/cyan] — Tasks that fail too many times\n"
            "5. [cyan]Backpressure[/cyan] — Queue grows if consumers are slower than producers",
            title="💡 Durable Task Queue Pattern",
            border_style="green",
        )
    )
