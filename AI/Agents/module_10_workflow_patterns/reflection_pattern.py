"""
=============================================================================
PATTERN 6: Reflection — Self-Critique and Iterative Improvement
=============================================================================
CONCEPT:
    Unlike Evaluator-Optimizer (which uses TWO agents), Reflection uses
    a SINGLE agent that critiques its OWN output and improves it.

    The agent generates → reviews its own work → identifies weaknesses
    → rewrites with improvements. This is SELF-CORRECTION.

    Generate → Self-Critique → Improve → Self-Critique → Done

WHEN TO USE:
    ✅ You want quality improvement without a separate evaluator
    ✅ The agent can meaningfully critique its own work
    ✅ Writing, code generation, reasoning tasks
    ❌ Objective quality criteria exist (use Evaluator-Optimizer instead)
    ❌ Self-critique is unreliable for the domain

RUN:
    python module_10_workflow_patterns/reflection_pattern.py
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: The Reflective Agent
# =============================================================================
def generate(topic: str) -> str:
    """Initial generation."""
    return chat(
        prompt=f"Write a technical explanation of: {topic}",
        system="You are a technical writer.",
        max_tokens=400,
    )


def self_critique(content: str, topic: str) -> str:
    """
    The agent critiques its OWN output.

    KEY INSIGHT: We ask the LLM to look at the content as if it were
    a reviewer, not the author. This shift in perspective helps it
    find issues it wouldn't see during generation.
    """
    return chat(
        prompt=f"""Critically review this content about '{topic}'. 
Be HARSH and specific. Find:
1. Factual inaccuracies or unsupported claims
2. Missing important topics
3. Unclear explanations
4. Poor structure or flow
5. Unnecessary verbosity

Content:
{content}

List ALL weaknesses you find. Be specific about what's wrong and how to fix it.""",
        system="You are a harsh but fair technical reviewer. Find genuinely meaningful issues, not nitpicks.",
        max_tokens=300,
    )


def improve(content: str, critique: str, topic: str) -> str:
    """Rewrite the content addressing the self-critique."""
    return chat(
        prompt=f"""Rewrite this content about '{topic}', addressing ALL these issues:

ORIGINAL:
{content}

ISSUES FOUND:
{critique}

Write an improved version that fixes every issue while keeping what was good.""",
        system="You are a technical writer improving your own work based on criticism.",
        max_tokens=500,
    )


# =============================================================================
# Step 2: The Reflection Loop
# =============================================================================
def run_reflection(topic: str, reflection_rounds: int = 2) -> dict:
    """Run the reflection loop."""
    rounds = []

    # Initial generation
    console.print("\n[bold blue]✍️  Initial Generation[/bold blue]")
    content = generate(topic)
    console.print(f"  [dim]{content[:120]}...[/dim]")

    for i in range(1, reflection_rounds + 1):
        console.print(f"\n[bold yellow]═══ Reflection Round {i}/{reflection_rounds} ═══[/bold yellow]")

        # Self-critique
        console.print("  [red]🔍 Self-Critique:[/red]")
        critique = self_critique(content, topic)
        console.print(f"  [dim]{critique[:120]}...[/dim]")

        # Improve based on critique
        console.print("  [green]✨ Improving:[/green]")
        improved = improve(content, critique, topic)
        console.print(f"  [dim]{improved[:120]}...[/dim]")

        rounds.append({
            "round": i,
            "critique": critique,
            "improved_content": improved,
        })

        content = improved  # Use improved version for next round

    return {
        "topic": topic,
        "initial_content": rounds[0]["critique"] if rounds else content,
        "rounds": rounds,
        "final_content": content,
    }


if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Pattern: Reflection (Self-Critique)[/bold]\n\n"
            "A SINGLE agent:\n"
            "  1. Generates content\n"
            "  2. Critiques its OWN output (as if it were a reviewer)\n"
            "  3. Rewrites to fix the issues it found\n"
            "  4. Repeats for N rounds",
            title="📖 Reflection Pattern",
            border_style="yellow",
        )
    )

    result = run_reflection(
        "Event-Driven Architecture: When and How to Use It",
        reflection_rounds=2,
    )

    console.print(
        Panel(result["final_content"], title="📋 Final (After Reflection)", border_style="green")
    )

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "1. [cyan]Single agent, dual role[/cyan] — same LLM generates AND reviews\n"
            "2. [cyan]Perspective shift[/cyan] — asking it to 'review' activates critical thinking\n"
            "3. [cyan]Diminishing returns[/cyan] — 2-3 rounds is usually optimal\n"
            "4. [cyan]Cheaper than Evaluator-Optimizer[/cyan] — no separate evaluator agent\n\n"
            "[bold]REFLECTION vs EVALUATOR-OPTIMIZER:[/bold]\n"
            "• Reflection: same agent reviews itself (simpler, cheaper)\n"
            "• Evaluator-Optimizer: separate agents (more objective, more robust)",
            title="💡 When to Use Reflection",
            border_style="green",
        )
    )
