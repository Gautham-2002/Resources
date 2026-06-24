"""
=============================================================================
MODULE 4 — DEMO 1: Approval Gate Pattern
=============================================================================
CONCEPT:
    An approval gate is a point in the workflow where the agent PAUSES
    and waits for human approval before proceeding.
    
    This is critical for:
    - Sending emails on behalf of users
    - Making financial transactions
    - Modifying production systems
    - Any action with irreversible consequences

WHAT THIS DEMO DOES:
    An email drafting agent that:
    1. Takes a request (e.g., "write an apology email to a client")
    2. Drafts the email using LLM
    3. PAUSES and shows the draft to the human
    4. Human can: APPROVE (send), REJECT (discard), or EDIT (provide feedback)
    5. If edited, agent revises and asks again

RUN:
    python module_4_human_in_the_loop/approval_gate_demo.py
=============================================================================
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from shared.llm import chat

console = Console()


class ApprovalGateAgent:
    """
    An agent with a built-in approval gate.
    
    The agent produces output, then BLOCKS until a human reviews it.
    This is the simplest but most powerful HITL pattern.
    """
    
    def __init__(self):
        self.drafts: list[str] = []
        self.status = "idle"
        self.approval_history: list[dict] = []
    
    def draft_email(self, request: str, feedback: str = "") -> str:
        """Generate an email draft using the LLM."""
        if feedback:
            prompt = f"""Revise this email based on feedback.

Original request: {request}
Previous draft: {self.drafts[-1]}
Feedback: {feedback}

Write the improved email."""
        else:
            prompt = f"Write a professional email for this request: {request}"
        
        draft = chat(
            prompt=prompt,
            system="You are an email writing assistant. Write professional, clear emails.",
            max_tokens=400,
        )
        self.drafts.append(draft)
        return draft
    
    def request_approval(self, draft: str) -> dict:
        """
        THE APPROVAL GATE: Pause and wait for human input.
        
        This is where the "interrupt" happens. In a real system,
        this might be an API call that sets the workflow to "pending"
        and waits for a webhook callback.
        
        In this CLI demo, we use input() to simulate the wait.
        """
        console.print(Panel(
            draft,
            title="📧 Email Draft — Awaiting Your Approval",
            border_style="yellow",
        ))
        
        console.print("\n[bold]Options:[/bold]")
        console.print("  [green]approve[/green] — Send the email as-is")
        console.print("  [red]reject[/red]  — Discard the email")
        console.print("  [yellow]edit[/yellow]    — Provide feedback for revision\n")
        
        choice = Prompt.ask(
            "Your decision",
            choices=["approve", "reject", "edit"],
            default="approve",
        )
        
        result = {"decision": choice, "feedback": ""}
        
        if choice == "edit":
            result["feedback"] = Prompt.ask("Your feedback")
        
        self.approval_history.append(result)
        return result
    
    def run(self, request: str):
        """
        Main workflow with approval gate.
        
        Flow: draft → [APPROVAL GATE] → send/reject/revise
        The gate can loop back to drafting if human wants edits.
        """
        console.print(Panel(
            f"[bold]Request:[/bold] {request}",
            title="✉️  Email Agent with Approval Gate",
            border_style="blue",
        ))
        
        self.status = "drafting"
        max_revisions = 3
        revision = 0
        feedback = ""
        
        while revision < max_revisions:
            # Step 1: Draft (or revise)
            console.print(f"\n[cyan]{'📝 Drafting...' if revision == 0 else '✏️  Revising based on feedback...'}[/cyan]")
            draft = self.draft_email(request, feedback)
            
            # Step 2: APPROVAL GATE — agent STOPS here
            self.status = "awaiting_approval"
            approval = self.request_approval(draft)
            
            if approval["decision"] == "approve":
                self.status = "approved"
                console.print("\n[bold green]✅ EMAIL APPROVED AND SENT![/bold green]")
                console.print(Panel(draft, title="📤 Sent Email", border_style="green"))
                return {"status": "sent", "final_draft": draft, "revisions": revision}
            
            elif approval["decision"] == "reject":
                self.status = "rejected"
                console.print("\n[bold red]❌ EMAIL REJECTED AND DISCARDED[/bold red]")
                return {"status": "rejected", "drafts": self.drafts, "revisions": revision}
            
            else:  # edit
                feedback = approval["feedback"]
                revision += 1
                console.print(f"\n[yellow]🔄 Revision {revision}/{max_revisions}...[/yellow]")
        
        console.print("\n[red]⚠ Max revisions reached.[/red]")
        return {"status": "max_revisions", "drafts": self.drafts}


if __name__ == "__main__":
    console.print(Panel(
        "[bold]Approval Gate Demo[/bold]\n\n"
        "This demo shows an agent that PAUSES for human approval.\n"
        "The agent drafts an email, then YOU decide:\n"
        "  • approve — send it\n"
        "  • reject — discard it\n"
        "  • edit — give feedback, agent revises\n\n"
        "This is the most common HITL pattern in production agents.",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    agent = ApprovalGateAgent()
    result = agent.run(
        "Write an apology email to our client TechCorp about the 2-hour service outage "
        "that happened yesterday. Mention that we've identified the root cause (database "
        "failover) and implemented safeguards to prevent recurrence."
    )
    
    console.print(Panel(
        "[bold]KEY TAKEAWAY:[/bold]\n"
        "✅ Approval gates prevent agents from taking irreversible actions\n"
        "✅ Humans stay in control of high-stakes decisions\n"
        "✅ The feedback loop lets humans ITERATE with the agent\n"
        "✅ In production: use webhooks/APIs instead of CLI prompts",
        title="💡 Approval Gate Pattern",
        border_style="green",
    ))
