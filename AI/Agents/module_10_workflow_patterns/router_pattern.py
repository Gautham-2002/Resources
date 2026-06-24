"""
=============================================================================
PATTERN 2: Router — Classify Input and Route to Specialist
=============================================================================
CONCEPT:
    An LLM classifier looks at the input and routes it to the most
    appropriate specialist agent. Like a hospital triage nurse.

                        ┌─→ Technical Agent
    Input → Classifier ─┼─→ Creative Agent
                        └─→ Analytical Agent

WHEN TO USE:
    ✅ Different inputs need fundamentally different handling
    ✅ You have specialized agents for each category
    ✅ Customer support (route by issue type)
    ❌ All inputs should be handled the same way (use Prompt Chaining)
    ❌ You need all specialists to run (use Fan-out)

RUN:
    python module_10_workflow_patterns/router_pattern.py
=============================================================================
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: The Classifier (Router)
# =============================================================================
def classify_input(user_input: str) -> str:
    """
    The ROUTER: classifies the input and decides which specialist to use.

    This is the heart of the pattern — an LLM decides the route.
    """
    result = chat(
        prompt=f"""Classify this user request into EXACTLY one category.
Reply with ONLY the category name, nothing else.

Categories:
- TECHNICAL: coding, debugging, architecture, APIs
- CREATIVE: writing, brainstorming, design, content
- ANALYTICAL: data analysis, comparisons, research, reports
- SUPPORT: troubleshooting, how-to, help requests

User request: {user_input}""",
        system="You are a classifier. Reply with only the category name.",
        max_tokens=20,
        temperature=0,
    )
    # Normalize
    category = result.strip().upper().replace('"', "").replace("'", "")
    for valid in ["TECHNICAL", "CREATIVE", "ANALYTICAL", "SUPPORT"]:
        if valid in category:
            return valid
    return "ANALYTICAL"  # Default fallback


# =============================================================================
# Step 2: Specialist Agents
# =============================================================================
def technical_agent(query: str) -> str:
    """Specialist for technical questions."""
    console.print("  [cyan]🔧 Routed to: Technical Agent[/cyan]")
    return chat(
        prompt=query,
        system="You are a senior software engineer. Provide detailed technical guidance with code examples where relevant.",
        max_tokens=400,
    )


def creative_agent(query: str) -> str:
    """Specialist for creative tasks."""
    console.print("  [magenta]🎨 Routed to: Creative Agent[/magenta]")
    return chat(
        prompt=query,
        system="You are a creative writer and designer. Be imaginative, engaging, and original.",
        max_tokens=400,
    )


def analytical_agent(query: str) -> str:
    """Specialist for analytical tasks."""
    console.print("  [yellow]📊 Routed to: Analytical Agent[/yellow]")
    return chat(
        prompt=query,
        system="You are a data analyst. Provide structured analysis, comparisons, and data-driven insights.",
        max_tokens=400,
    )


def support_agent(query: str) -> str:
    """Specialist for support questions."""
    console.print("  [green]🎧 Routed to: Support Agent[/green]")
    return chat(
        prompt=query,
        system="You are a helpful support agent. Provide step-by-step guidance and solutions.",
        max_tokens=400,
    )


SPECIALISTS = {
    "TECHNICAL": technical_agent,
    "CREATIVE": creative_agent,
    "ANALYTICAL": analytical_agent,
    "SUPPORT": support_agent,
}


# =============================================================================
# Step 3: The Router Pipeline
# =============================================================================
def route_and_handle(user_input: str) -> dict:
    """Classify the input and route to the appropriate specialist."""
    console.print(f"\n[bold]Input:[/bold] {user_input[:80]}...")

    # Step 1: Classify
    category = classify_input(user_input)
    console.print(f"  [bold blue]🏷️  Classification:[/bold blue] {category}")

    # Step 2: Route to specialist
    handler = SPECIALISTS.get(category, analytical_agent)
    result = handler(user_input)

    return {"input": user_input, "category": category, "response": result}


# =============================================================================
# Step 4: Run the demo
# =============================================================================
TEST_INPUTS = [
    "How do I implement a binary search tree in Python with O(log n) lookup?",
    "Write a haiku about artificial intelligence discovering emotions",
    "Compare the market share dynamics of cloud providers AWS vs Azure vs GCP in 2025",
    "My API keeps returning 503 errors after deploying to production, how do I fix this?",
]

if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Pattern: Router[/bold]\n\n"
            "An LLM classifier routes each input to a specialist:\n"
            "  Input → [Classifier] → Technical | Creative | Analytical | Support\n\n"
            "Each specialist has different system prompts and expertise.",
            title="📖 Router Pattern",
            border_style="yellow",
        )
    )

    results = []
    for user_input in TEST_INPUTS:
        r = route_and_handle(user_input)
        results.append(r)

    # Summary table
    table = Table(title="Router Pattern Results")
    table.add_column("Input", style="white", width=40)
    table.add_column("Route", style="cyan", width=12)
    table.add_column("Response Preview", style="dim", width=40)

    for r in results:
        table.add_row(
            r["input"][:40] + "...",
            r["category"],
            r["response"][:40] + "...",
        )

    console.print(table)

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "1. [cyan]Classify first[/cyan] — LLM decides the route\n"
            "2. [cyan]Specialist agents[/cyan] — each has different system prompts\n"
            "3. [cyan]Fallback[/cyan] — always have a default route\n"
            "4. [cyan]Composable[/cyan] — combine with other patterns (e.g., route → chain)\n\n"
            "[bold]REAL-WORLD USES:[/bold]\n"
            "• Customer support triage (billing / technical / account)\n"
            "• Content moderation (safe / review / block)\n"
            "• Multi-language routing (detect language → translate agent)",
            title="💡 When to Use Router Pattern",
            border_style="green",
        )
    )
