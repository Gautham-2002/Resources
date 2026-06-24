"""
=============================================================================
MODULE 6 — DEMO 1: Webhook-Triggered Agent Workflows
=============================================================================
CONCEPT:
    Webhooks are HTTP callbacks — external systems send POST requests
    to your server when something happens. Your server then triggers
    the appropriate agent workflow.

    Example real-world triggers:
    - GitHub: push event → code review agent
    - Stripe: payment event → invoice agent
    - Slack: message event → support agent

WHAT THIS DEMO DOES:
    A FastAPI server that receives different types of webhooks and
    routes each to a specialized agent:

    - "code_push"    → Code Review Agent
    - "new_ticket"   → Support Triage Agent
    - "payment"      → Invoice Agent

RUN:
    python module_6_event_driven/webhook_trigger_demo.py

    This runs the server AND sends test webhooks automatically.
=============================================================================
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Define event handlers (agent workflows triggered by webhooks)
# =============================================================================
class WebhookProcessor:
    """
    Processes incoming webhooks by routing them to the appropriate agent.

    This is the CORE PATTERN of event-driven orchestration:
    1. Receive event
    2. Classify/route
    3. Trigger appropriate workflow
    4. Log results
    """

    def __init__(self):
        self.event_log: list[dict] = []
        self.handlers = {
            "code_push": self._handle_code_push,
            "new_ticket": self._handle_new_ticket,
            "payment": self._handle_payment,
        }

    def process(self, event_type: str, payload: dict) -> dict:
        """Route an incoming webhook to the appropriate handler."""
        console.print(f"\n[bold blue]📨 Webhook Received:[/bold blue] {event_type}")
        console.print(f"  [dim]Payload: {json.dumps(payload)[:100]}...[/dim]")

        handler = self.handlers.get(event_type)
        if not handler:
            result = {"status": "error", "message": f"Unknown event type: {event_type}"}
        else:
            result = handler(payload)

        self.event_log.append(
            {
                "event_type": event_type,
                "payload": payload,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return result

    def _handle_code_push(self, payload: dict) -> dict:
        """Code Review Agent — triggered by code push events."""
        console.print("  [yellow]🔍 Code Review Agent triggered...[/yellow]")

        review = chat(
            prompt=f"Review this code change:\nRepo: {payload.get('repo', 'unknown')}\nFiles changed: {payload.get('files', [])}\nCommit message: {payload.get('message', 'no message')}\n\nProvide a brief code review with potential issues.",
            system="You are a code review agent. Be concise and focus on potential issues.",
            max_tokens=200,
        )

        console.print("  [green]✅ Review complete[/green]")
        return {"status": "reviewed", "review": review}

    def _handle_new_ticket(self, payload: dict) -> dict:
        """Support Triage Agent — triggered by new support tickets."""
        console.print("  [yellow]🏷️  Support Triage Agent triggered...[/yellow]")

        triage = chat(
            prompt=f"Triage this support ticket:\nTitle: {payload.get('title', 'unknown')}\nDescription: {payload.get('description', 'none')}\n\nClassify priority (P1-P4), category, and suggest initial response.",
            system="You are a support triage agent. Classify and prioritize tickets.",
            max_tokens=200,
        )

        console.print("  [green]✅ Triage complete[/green]")
        return {"status": "triaged", "triage": triage}

    def _handle_payment(self, payload: dict) -> dict:
        """Invoice Agent — triggered by payment events."""
        console.print("  [yellow]💰 Invoice Agent triggered...[/yellow]")

        invoice = chat(
            prompt=f"Generate invoice summary:\nAmount: ${payload.get('amount', 0)}\nCustomer: {payload.get('customer', 'unknown')}\nProduct: {payload.get('product', 'unknown')}\n\nGenerate a brief invoice confirmation.",
            system="You are an invoice generation agent.",
            max_tokens=150,
        )

        console.print("  [green]✅ Invoice generated[/green]")
        return {"status": "invoiced", "invoice": invoice}


# =============================================================================
# Step 2: Simulate webhook events
# =============================================================================
SAMPLE_WEBHOOKS = [
    {
        "event_type": "code_push",
        "payload": {
            "repo": "acme/backend-api",
            "files": ["auth.py", "models.py"],
            "message": "Add JWT token refresh endpoint",
            "author": "dev@acme.com",
        },
    },
    {
        "event_type": "new_ticket",
        "payload": {
            "title": "Cannot login after password reset",
            "description": "User reports that after resetting password, they get 'Invalid credentials' error. Happening since this morning.",
            "customer": "enterprise-client",
        },
    },
    {
        "event_type": "payment",
        "payload": {
            "amount": 4999.00,
            "customer": "TechCorp Inc",
            "product": "Enterprise AI Platform - Annual License",
            "payment_method": "wire_transfer",
        },
    },
]


# =============================================================================
# Step 3: Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Webhook-Triggered Agent Workflows[/bold]\n\n"
            "This demo shows how external events trigger agent workflows:\n"
            "  • code_push → Code Review Agent\n"
            "  • new_ticket → Support Triage Agent\n"
            "  • payment → Invoice Agent\n\n"
            "In production, these webhooks come from GitHub, Stripe, Slack, etc.",
            title="📖 What You'll See",
            border_style="yellow",
        )
    )

    processor = WebhookProcessor()

    for webhook in SAMPLE_WEBHOOKS:
        result = processor.process(webhook["event_type"], webhook["payload"])

    # Summary
    table = Table(title="Webhook Processing Summary")
    table.add_column("Event", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Result Preview", style="white", width=50)

    for entry in processor.event_log:
        first_value = (
            list(entry["result"].values())[1] if len(entry["result"]) > 1 else ""
        )
        preview = str(first_value)[:50] + "..." if first_value else "N/A"
        table.add_row(entry["event_type"], entry["result"]["status"], preview)

    console.print(table)

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "✅ Event-driven = REACT to things happening\n"
            "✅ Producers and consumers are DECOUPLED\n"
            "✅ Easy to add new event types and handlers\n"
            "✅ In production: use message queues (SQS/Kafka) between webhook and handler",
            title="💡 Webhook-Triggered Orchestration",
            border_style="green",
        )
    )
