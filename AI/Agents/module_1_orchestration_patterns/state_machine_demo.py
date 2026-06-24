"""
=============================================================================
MODULE 1 — DEMO 1: State Machine Pattern
=============================================================================
CONCEPT:
    A Finite State Machine (FSM) defines a fixed set of states and transitions.
    The agent can ONLY move between predefined states via predefined transitions.

    This is perfect for workflows where you know every possible path upfront,
    like order processing, ticket handling, or approval workflows.

WHAT THIS DEMO DOES:
    Simulates an order processing agent that:
    1. Receives a new order
    2. Validates it (using LLM to check if the order makes sense)
    3. Processes payment
    4. Fulfills the order
    5. Ships it

    Each state transition is FIXED — the agent can't skip steps or invent new ones.

RUN:
    python module_1_orchestration_patterns/state_machine_demo.py
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transitions import Machine
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Define the State Machine
# =============================================================================
class OrderAgent:
    """
    An order processing agent powered by a Finite State Machine.

    States: new → validating → validated → processing_payment → paid → fulfilling → shipped

    KEY INSIGHT: Every state and transition is defined at design time.
    The agent CANNOT deviate from this flow — it's deterministic and predictable.
    """

    # All possible states the order can be in
    states = [
        "new",
        "validating",
        "validated",
        "processing_payment",
        "paid",
        "fulfilling",
        "shipped",
        "failed",  # Error state — can be reached from multiple states
    ]

    def __init__(self, order_details: str):
        self.order_details = order_details
        self.validation_result = ""
        self.payment_result = ""
        self.fulfillment_result = ""
        self.shipping_result = ""
        self.error_message = ""
        self.transition_log: list[str] = []

        # Initialize the state machine
        # This wires up all the transitions — look at how explicit they are!
        self.machine = Machine(
            model=self,
            states=OrderAgent.states,
            initial="new",
            transitions=[
                # trigger name       | from state            | to state
                ["start_validation", "new", "validating"],
                ["validation_passed", "validating", "validated"],
                ["validation_failed", "validating", "failed"],
                ["start_payment", "validated", "processing_payment"],
                ["payment_succeeded", "processing_payment", "paid"],
                ["payment_failed", "processing_payment", "failed"],
                ["start_fulfillment", "paid", "fulfilling"],
                ["fulfillment_done", "fulfilling", "shipped"],
                ["fulfillment_failed", "fulfilling", "failed"],
            ],
        )

    def _log(self, message: str):
        """Log a state transition."""
        self.transition_log.append(f"[{self.state}] {message}")
        console.print(f"  📌 [bold cyan]State:[/bold cyan] {self.state} — {message}")

    # =========================================================================
    # Step 2: Define the action for each state
    # Each method uses the LLM for the "thinking" part, but the FLOW is fixed
    # =========================================================================

    def validate_order(self) -> bool:
        """Use LLM to validate the order details."""
        self.start_validation()  # Transition: new → validating
        self._log("Validating order...")

        result = chat(
            prompt=f"Validate this order. Is it reasonable? Reply with VALID or INVALID and a brief reason.\nOrder: {self.order_details}",
            system="You are an order validation agent. Check if the order is reasonable (valid product, reasonable quantity, etc).",
            max_tokens=100,
        )
        self.validation_result = result

        if "VALID" in result.upper() and "INVALID" not in result.upper():
            self.validation_passed()  # Transition: validating → validated
            self._log(f"✅ Validation passed: {result[:80]}")
            return True
        else:
            self.validation_failed()  # Transition: validating → failed
            self.error_message = f"Validation failed: {result}"
            self._log(f"❌ Validation failed: {result[:80]}")
            return False

    def process_payment(self) -> bool:
        """Simulate payment processing with LLM generating a receipt."""
        self.start_payment()  # Transition: validated → processing_payment
        self._log("Processing payment...")

        result = chat(
            prompt=f"Generate a brief payment confirmation for this order: {self.order_details}. Include a fake transaction ID.",
            system="You are a payment processing agent. Generate realistic payment confirmations.",
            max_tokens=100,
        )
        self.payment_result = result
        self.payment_succeeded()  # Transition: processing_payment → paid
        self._log(f"✅ Payment processed: {result[:80]}")
        return True

    def fulfill_order(self) -> bool:
        """Use LLM to generate fulfillment instructions."""
        self.start_fulfillment()  # Transition: paid → fulfilling
        self._log("Fulfilling order...")

        result = chat(
            prompt=f"Generate brief shipping and fulfillment details for: {self.order_details}. Include a fake tracking number.",
            system="You are a fulfillment agent. Generate realistic shipping details.",
            max_tokens=100,
        )
        self.fulfillment_result = result
        self.fulfillment_done()  # Transition: fulfilling → shipped
        self._log(f"✅ Order shipped: {result[:80]}")
        return True

    # =========================================================================
    # Step 3: Run the entire workflow
    # =========================================================================

    def run(self) -> dict:
        """
        Execute the full order processing workflow.

        Notice how the flow is COMPLETELY LINEAR AND PREDICTABLE:
        new → validating → validated → processing_payment → paid → fulfilling → shipped

        The LLM adds intelligence to each STEP, but the SEQUENCE is fixed.
        """
        console.print(
            Panel(
                f"[bold]Order:[/bold] {self.order_details}",
                title="🛒 Order Processing Agent (State Machine)",
                border_style="blue",
            )
        )

        # Step 1: Validate
        if not self.validate_order():
            return self._build_result()

        # Step 2: Payment
        if not self.process_payment():
            return self._build_result()

        # Step 3: Fulfill
        if not self.fulfill_order():
            return self._build_result()

        console.print(
            "\n[bold green]✅ Order workflow completed successfully![/bold green]\n"
        )
        return self._build_result()

    def _build_result(self) -> dict:
        """Build the final result summary."""
        return {
            "final_state": self.state,
            "order": self.order_details,
            "validation": self.validation_result,
            "payment": self.payment_result,
            "fulfillment": self.fulfillment_result,
            "error": self.error_message,
            "transitions": self.transition_log,
        }


# =============================================================================
# Step 4: Visualize the results
# =============================================================================
def display_results(result: dict):
    """Pretty-print the workflow results."""
    table = Table(title="State Machine Workflow Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row(
        "Final State",
        f"[bold green]{result['final_state']}[/bold green]"
        if result["final_state"] == "shipped"
        else f"[bold red]{result['final_state']}[/bold red]",
    )
    table.add_row("Order", result["order"])
    table.add_row(
        "Validation", result["validation"][:100] if result["validation"] else "N/A"
    )
    table.add_row("Payment", result["payment"][:100] if result["payment"] else "N/A")
    table.add_row(
        "Fulfillment", result["fulfillment"][:100] if result["fulfillment"] else "N/A"
    )

    if result["error"]:
        table.add_row("Error", f"[red]{result['error'][:100]}[/red]")

    console.print(table)

    console.print("\n[bold]Transition Log:[/bold]")
    for entry in result["transitions"]:
        console.print(f"  → {entry}")


# =============================================================================
# Step 5: Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]State Machine Pattern Demo[/bold]\n\n"
            "This demo shows an order processing agent using a Finite State Machine.\n"
            "The workflow is FIXED: new → validating → validated → payment → paid → fulfilling → shipped\n"
            "The LLM adds intelligence to each step, but the sequence NEVER changes.",
            title="📖 What You'll See",
            border_style="yellow",
        )
    )

    # Run a valid order
    console.print("\n[bold yellow]═══ Test 1: Valid Order ═══[/bold yellow]\n")
    agent = OrderAgent(
        "5 units of MacBook Pro M4 for office use, shipping to New York, NY"
    )
    result = agent.run()
    display_results(result)

    # Run an invalid order
    console.print("\n\n[bold yellow]═══ Test 2: Invalid Order ═══[/bold yellow]\n")
    agent2 = OrderAgent(
        "negative -50 units of invisible unicorn dust, deliver to the moon"
    )
    result2 = agent2.run()
    display_results(result2)

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "✅ State Machines are PREDICTABLE — you know every possible state\n"
            "✅ Great for compliance, auditing, and regulated workflows\n"
            "❌ Not flexible — can't handle unexpected situations\n"
            "❌ Adding new states requires code changes",
            title="💡 When to Use State Machines",
            border_style="green",
        )
    )
