"""
=============================================================================
PATTERN 1: Prompt Chaining — Sequential Pipeline
=============================================================================
CONCEPT:
    The simplest agentic pattern. Break a large task into smaller,
    sequential steps where each step's output feeds into the next.

    Step 1 → Step 2 → Step 3 → Step 4
    (each step reads the previous step's output)

WHEN TO USE:
    ✅ Task has a natural linear flow (research → analyze → write → edit)
    ✅ Each step depends on the previous step's output
    ✅ You want maximum control and predictability
    ❌ Steps are independent (use Fan-out instead)
    ❌ The workflow is too complex to predefine (use Orchestrator-Worker)

RUN:
    python module_10_workflow_patterns/prompt_chaining.py
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
# The Chain: Research → Outline → Draft → Polish
# =============================================================================
def step_1_research(topic: str) -> str:
    """Step 1: Gather key facts about the topic."""
    console.print("\n[bold blue]🔬 Step 1: Research[/bold blue]")
    result = chat(
        prompt=f"Research the topic '{topic}'. List 5 key facts or findings.",
        system="You are a research agent. Provide concise, factual findings.",
        max_tokens=300,
    )
    console.print(f"  [dim]{result[:120]}...[/dim]")
    return result


def step_2_outline(research: str) -> str:
    """Step 2: Create an outline FROM the research (chains off step 1)."""
    console.print("\n[bold yellow]📝 Step 2: Outline[/bold yellow]  (uses research from Step 1)")
    result = chat(
        prompt=f"Based on this research, create a 4-section article outline:\n\n{research}",
        system="You are an outline planner. Create structured, logical outlines.",
        max_tokens=300,
    )
    console.print(f"  [dim]{result[:120]}...[/dim]")
    return result


def step_3_draft(outline: str) -> str:
    """Step 3: Write a draft FROM the outline (chains off step 2)."""
    console.print("\n[bold magenta]✍️  Step 3: Draft[/bold magenta]  (uses outline from Step 2)")
    result = chat(
        prompt=f"Write a short article following this outline:\n\n{outline}",
        system="You are a writer. Write clear, engaging content.",
        max_tokens=500,
    )
    console.print(f"  [dim]{result[:120]}...[/dim]")
    return result


def step_4_polish(draft: str) -> str:
    """Step 4: Polish the draft (chains off step 3)."""
    console.print("\n[bold green]💎 Step 4: Polish[/bold green]  (uses draft from Step 3)")
    result = chat(
        prompt=f"Polish and improve this article. Fix any issues, improve flow, and make it more engaging:\n\n{draft}",
        system="You are an editor. Improve clarity, flow, and engagement.",
        max_tokens=500,
    )
    console.print(f"  [dim]{result[:120]}...[/dim]")
    return result


# =============================================================================
# Run the chain
# =============================================================================
def run_prompt_chain(topic: str) -> dict:
    """Execute the full prompt chain."""
    research = step_1_research(topic)
    outline = step_2_outline(research)      # Reads step 1 output
    draft = step_3_draft(outline)           # Reads step 2 output
    polished = step_4_polish(draft)         # Reads step 3 output

    return {
        "topic": topic,
        "research": research,
        "outline": outline,
        "draft": draft,
        "polished_article": polished,
    }


if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Pattern: Prompt Chaining[/bold]\n\n"
            "Each step reads the OUTPUT of the previous step:\n"
            "  Research → Outline → Draft → Polish\n\n"
            "The simplest pattern — linear, predictable, easy to debug.",
            title="📖 Prompt Chaining",
            border_style="yellow",
        )
    )

    result = run_prompt_chain("How AI Agents Are Changing Software Engineering")

    console.print(
        Panel(result["polished_article"], title="📋 Final Article", border_style="green")
    )

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "1. [cyan]Output → Input piping[/cyan] — each step uses the previous result\n"
            "2. [cyan]Gate checks[/cyan] — you can add validation between steps\n"
            "3. [cyan]Predictable[/cyan] — always runs the same number of steps\n"
            "4. [cyan]Debuggable[/cyan] — inspect the output of any step\n\n"
            "[bold]REAL-WORLD USES:[/bold]\n"
            "• Content pipelines (research → write → edit)\n"
            "• Data processing (extract → transform → validate → load)\n"
            "• Customer onboarding (verify → setup → notify)",
            title="💡 When to Use Prompt Chaining",
            border_style="green",
        )
    )
