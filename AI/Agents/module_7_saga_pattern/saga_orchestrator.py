"""
=============================================================================
MODULE 7 — SAGA ORCHESTRATOR: Distributed Transactions with Rollback
=============================================================================
CONCEPT:
    The Saga Pattern manages distributed transactions across multiple services.
    
    Unlike a database transaction (all-or-nothing), a saga:
    1. Executes steps sequentially
    2. If a step FAILS, runs COMPENSATING ACTIONS in reverse order
    3. Each step has a corresponding "undo" action
    
    This is essential when agents interact with multiple external systems
    (CRM, email, billing, provisioning) that can't be wrapped in a single
    database transaction.

WHAT THIS DEMO DOES:
    Customer onboarding saga:
    
    Step 1: Create CRM record    → Compensate: Delete CRM record
    Step 2: Send welcome email   → Compensate: Send cancellation email
    Step 3: Provision account     → Compensate: Deprovision account
    Step 4: Setup billing         → Compensate: Remove billing record
    
    We run TWO scenarios:
    1. ✅ Happy path: all steps succeed
    2. ❌ Failure path: step 3 fails → rollback steps 2 and 1

RUN:
    python module_7_saga_pattern/saga_orchestrator.py
=============================================================================
"""

import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Define the Saga Step structure
# =============================================================================
class SagaStep:
    """
    A single step in a saga.
    
    Each step has:
    - action: the forward action (do something)
    - compensation: the rollback action (undo it)
    
    The compensation is only called if a LATER step fails.
    """
    
    def __init__(self, name: str, action, compensation, should_fail: bool = False):
        self.name = name
        self.action = action            # Function: (context) -> result
        self.compensation = compensation # Function: (context, result) -> None
        self.should_fail = should_fail
        self.result = None
        self.status = "pending"
        self.error: str | None = None


# =============================================================================
# Step 2: The Saga Orchestrator
# =============================================================================
class SagaOrchestrator:
    """
    Orchestrates a saga — executes steps and handles rollback.
    
    This is the ORCHESTRATOR variant of the saga pattern:
    - A central coordinator manages the entire workflow
    - On failure, it calls compensations in REVERSE ORDER
    
    (The other variant is CHOREOGRAPHY, where services communicate
    via events — more complex but more decoupled.)
    """
    
    def __init__(self, name: str):
        self.name = name
        self.saga_id = str(uuid.uuid4())[:8]
        self.steps: list[SagaStep] = []
        self.completed_steps: list[SagaStep] = []
        self.execution_log: list[str] = []
        self.status = "pending"
    
    def add_step(self, step: SagaStep):
        """Add a step to the saga."""
        self.steps.append(step)
    
    def execute(self, context: dict) -> dict:
        """
        Execute the saga.
        
        The key algorithm:
        1. Run steps in order
        2. If any step fails:
           a. Stop executing forward steps
           b. Run compensations for ALL completed steps in REVERSE order
        """
        console.print(Panel(
            f"Saga: {self.name}\nID: {self.saga_id}\nSteps: {len(self.steps)}",
            title="🎭 Saga Execution",
            border_style="blue",
        ))
        
        self.status = "executing"
        
        for i, step in enumerate(self.steps):
            console.print(f"\n  [bold]Step {i+1}/{len(self.steps)}: {step.name}[/bold]")
            
            try:
                if step.should_fail:
                    raise Exception(f"Simulated failure in '{step.name}'")
                
                # Execute the forward action
                step.result = step.action(context)
                step.status = "completed"
                self.completed_steps.append(step)
                self.execution_log.append(f"✅ {step.name} — SUCCESS")
                console.print(f"    [green]✅ {step.name} completed[/green]")
                
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                self.execution_log.append(f"❌ {step.name} — FAILED: {e}")
                console.print(f"    [red]❌ {step.name} FAILED: {e}[/red]")
                
                # ROLLBACK: compensate all completed steps in REVERSE order
                console.print(Panel(
                    f"Step '{step.name}' failed!\n"
                    f"Rolling back {len(self.completed_steps)} completed step(s)...",
                    title="⚠️  SAGA ROLLBACK INITIATED",
                    border_style="red",
                ))
                
                self._rollback(context)
                self.status = "rolled_back"
                
                return {
                    "saga_id": self.saga_id,
                    "status": "rolled_back",
                    "failed_step": step.name,
                    "error": str(e),
                    "log": self.execution_log,
                }
        
        self.status = "completed"
        console.print(Panel(
            "[bold green]All steps completed successfully![/bold green]",
            title="✅ Saga Complete",
            border_style="green",
        ))
        
        return {
            "saga_id": self.saga_id,
            "status": "completed",
            "log": self.execution_log,
        }
    
    def _rollback(self, context: dict):
        """
        Execute compensating actions in REVERSE ORDER.
        
        This is the magic of the saga pattern:
        Step 3 failed → Compensate Step 2 → Compensate Step 1
        """
        for step in reversed(self.completed_steps):
            try:
                console.print(f"    [yellow]🔄 Rolling back: {step.name}[/yellow]")
                step.compensation(context, step.result)
                self.execution_log.append(f"🔄 ROLLBACK {step.name} — SUCCESS")
                console.print(f"    [green]✅ Rollback of {step.name} successful[/green]")
            except Exception as e:
                self.execution_log.append(f"🔄 ROLLBACK {step.name} — FAILED: {e}")
                console.print(f"    [red]❌ Rollback of {step.name} FAILED: {e}[/red]")


# =============================================================================
# Step 3: Define the customer onboarding steps
# =============================================================================
def create_crm_record(context: dict) -> dict:
    """Step 1: Create a CRM record."""
    result = chat(
        prompt=f"Generate a brief CRM record for new customer: {context['customer_name']}, email: {context['email']}. Include a fake CRM ID.",
        system="You are a CRM agent. Generate concise CRM records.",
        max_tokens=100,
    )
    console.print(f"    [dim]{result[:80]}...[/dim]")
    return {"crm_record": result, "crm_id": f"CRM-{uuid.uuid4().hex[:6].upper()}"}


def rollback_crm_record(context: dict, result: dict):
    """Compensation: Delete the CRM record."""
    crm_id = result.get("crm_id", "unknown")
    console.print(f"    [dim]Deleting CRM record {crm_id}...[/dim]")


def send_welcome_email(context: dict) -> dict:
    """Step 2: Send welcome email."""
    result = chat(
        prompt=f"Draft a brief welcome email for {context['customer_name']} who just signed up for our platform.",
        system="You are an email agent. Write brief, professional emails.",
        max_tokens=100,
    )
    console.print(f"    [dim]Email sent: {result[:60]}...[/dim]")
    return {"email_sent": True, "email_preview": result}


def rollback_welcome_email(context: dict, result: dict):
    """Compensation: Send cancellation email."""
    console.print(f"    [dim]Sending cancellation notice to {context['email']}...[/dim]")


def provision_account(context: dict) -> dict:
    """Step 3: Provision user account."""
    result = chat(
        prompt=f"Generate account provisioning details for {context['customer_name']}. Include fake account ID and initial setup info.",
        system="You are a provisioning agent.",
        max_tokens=100,
    )
    console.print(f"    [dim]{result[:60]}...[/dim]")
    return {"account_id": f"ACC-{uuid.uuid4().hex[:6].upper()}", "details": result}


def rollback_provision_account(context: dict, result: dict):
    """Compensation: Deprovision account."""
    acc_id = result.get("account_id", "unknown")
    console.print(f"    [dim]Deprovisioning account {acc_id}...[/dim]")


def setup_billing(context: dict) -> dict:
    """Step 4: Set up billing."""
    result = chat(
        prompt=f"Generate billing setup confirmation for {context['customer_name']}, plan: {context.get('plan', 'pro')}.",
        system="You are a billing agent.",
        max_tokens=100,
    )
    return {"billing_id": f"BIL-{uuid.uuid4().hex[:6].upper()}", "details": result}


def rollback_billing(context: dict, result: dict):
    """Compensation: Remove billing record."""
    bil_id = result.get("billing_id", "unknown")
    console.print(f"    [dim]Removing billing record {bil_id}...[/dim]")


# =============================================================================
# Step 4: Run the demo
# =============================================================================
def run_saga(name: str, fail_step: int | None = None) -> dict:
    """Build and run a saga, optionally failing at a specific step."""
    saga = SagaOrchestrator(name)
    
    steps = [
        SagaStep("Create CRM Record", create_crm_record, rollback_crm_record),
        SagaStep("Send Welcome Email", send_welcome_email, rollback_welcome_email),
        SagaStep("Provision Account", provision_account, rollback_provision_account),
        SagaStep("Setup Billing", setup_billing, rollback_billing),
    ]
    
    # Mark a step to fail if requested
    if fail_step is not None and 0 <= fail_step < len(steps):
        steps[fail_step].should_fail = True
    
    for step in steps:
        saga.add_step(step)
    
    context = {
        "customer_name": "Alex Johnson",
        "email": "alex@techcorp.com",
        "plan": "enterprise",
    }
    
    return saga.execute(context)


if __name__ == "__main__":
    console.print(Panel(
        "[bold]Saga Pattern Demo[/bold]\n\n"
        "This demo shows the Saga Pattern for distributed transactions.\n"
        "We run TWO scenarios:\n\n"
        "1. ✅ HAPPY PATH — All 4 steps succeed\n"
        "2. ❌ FAILURE PATH — Step 3 fails → Steps 2 & 1 are rolled back\n\n"
        "Steps: CRM Record → Welcome Email → Provision Account → Billing",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    # Scenario 1: Happy path
    console.print("\n[bold yellow]═══ Scenario 1: Happy Path (All Steps Succeed) ═══[/bold yellow]")
    result1 = run_saga("Customer Onboarding - Happy Path")
    
    # Scenario 2: Failure with rollback
    console.print("\n\n[bold yellow]═══ Scenario 2: Failure at Step 3 (Provision Account) ═══[/bold yellow]")
    result2 = run_saga("Customer Onboarding - Failure", fail_step=2)  # 0-indexed: step 3
    
    # Summary
    table = Table(title="Saga Results Summary")
    table.add_column("Scenario", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Steps Completed", style="white")
    
    table.add_row("Happy Path", f"[green]{result1['status']}[/green]", f"{len(result1['log'])} actions")
    table.add_row(
        "Failure at Step 3",
        f"[red]{result2['status']}[/red]",
        f"{len(result2['log'])} actions (including rollbacks)",
    )
    
    console.print(table)
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]Forward Action[/cyan] — The step's primary logic (create, send, provision)\n"
        "2. [cyan]Compensating Action[/cyan] — The undo logic (delete, cancel, deprovision)\n"
        "3. [cyan]Reverse Order Rollback[/cyan] — Most recent step rolled back first\n"
        "4. [cyan]Orchestrator vs Choreography[/cyan] — Central coordinator vs event-based\n\n"
        "[bold]WHEN TO USE:[/bold]\n"
        "✅ Multi-service workflows (CRM + Email + Billing)\n"
        "✅ When actions have side effects that need undoing\n"
        "✅ When you can't use database transactions across services",
        title="💡 Saga Pattern",
        border_style="green",
    ))
