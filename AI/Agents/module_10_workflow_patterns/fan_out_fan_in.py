"""
=============================================================================
PATTERN 3: Fan-out / Fan-in — Parallel Execution + Merge
=============================================================================
CONCEPT:
    Split a task into INDEPENDENT subtasks, run them in PARALLEL,
    then MERGE the results with a coordinator agent.

                ┌─→ Agent A ─┐
    Task ──────┼─→ Agent B ─┼──→ Coordinator → Final Output
                └─→ Agent C ─┘

    Fan-out = split into parallel agents
    Fan-in  = merge results together

WHEN TO USE:
    ✅ Subtasks are independent (no dependencies between them)
    ✅ Speed is important (parallelism = faster)
    ✅ You want multiple perspectives on the same topic
    ❌ Steps depend on each other (use Prompt Chaining)
    ❌ The number of subtasks isn't known upfront (use Orchestrator-Worker)

RUN:
    python module_10_workflow_patterns/fan_out_fan_in.py
=============================================================================
"""

import sys
import os
import asyncio
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import achat

console = Console()


# =============================================================================
# Step 1: Define the parallel agents (Fan-out)
# =============================================================================
PERSPECTIVES = [
    ("Technical Expert", "Analyze from a technical/engineering perspective. Focus on implementation challenges and solutions."),
    ("Business Analyst", "Analyze from a business perspective. Focus on market impact, ROI, and strategic implications."),
    ("End User Advocate", "Analyze from the end user's perspective. Focus on usability, adoption barriers, and benefits."),
    ("Ethics Researcher", "Analyze from an ethical perspective. Focus on risks, fairness, bias, and societal impact."),
]


async def run_perspective_agent(name: str, system_prompt: str, topic: str) -> dict:
    """Run a single perspective agent."""
    start = time.time()
    result = await achat(
        prompt=f"Analyze this topic: '{topic}'. Provide 3 key insights from your perspective.",
        system=f"You are a {name}. {system_prompt}",
        max_tokens=250,
    )
    duration = time.time() - start
    return {"name": name, "result": result, "duration": duration}


# =============================================================================
# Step 2: Coordinator agent (Fan-in)
# =============================================================================
async def coordinator(topic: str, perspectives: list[dict]) -> str:
    """
    The COORDINATOR merges all parallel results into a single output.
    This is the Fan-in step — the synthesis.
    """
    combined = "\n\n".join([
        f"### {p['name']}:\n{p['result']}" for p in perspectives
    ])

    result = await achat(
        prompt=f"""You received analysis of '{topic}' from 4 different perspectives:

{combined}

Synthesize these into a comprehensive executive summary that integrates all viewpoints.
Highlight areas of agreement and tension between perspectives.""",
        system="You are a synthesis coordinator. Create balanced, comprehensive summaries.",
        max_tokens=400,
    )
    return result


# =============================================================================
# Step 3: The Fan-out / Fan-in pipeline
# =============================================================================
async def fan_out_fan_in(topic: str) -> dict:
    """Execute the full fan-out/fan-in pattern."""
    console.print(
        Panel(f"Topic: {topic}", title="🌐 Fan-out: Launching parallel agents", border_style="blue")
    )

    # FAN-OUT: Run all agents in parallel
    start = time.time()
    tasks = [
        run_perspective_agent(name, system_prompt, topic)
        for name, system_prompt in PERSPECTIVES
    ]
    perspectives = await asyncio.gather(*tasks)
    fan_out_time = time.time() - start

    for p in perspectives:
        console.print(f"  ✅ {p['name']}: done in {p['duration']:.1f}s")

    console.print(f"\n  [bold]Fan-out total: {fan_out_time:.1f}s[/bold] (all ran in parallel!)")

    # FAN-IN: Merge results
    console.print(
        Panel("Merging perspectives...", title="🔗 Fan-in: Coordinator", border_style="magenta")
    )
    summary = await coordinator(topic, perspectives)

    return {
        "topic": topic,
        "perspectives": perspectives,
        "summary": summary,
        "fan_out_time": fan_out_time,
    }


# =============================================================================
# Step 4: Run the demo
# =============================================================================
async def main():
    console.print(
        Panel(
            "[bold]Pattern: Fan-out / Fan-in[/bold]\n\n"
            "4 agents analyze the same topic from different perspectives:\n"
            "  Technical | Business | End User | Ethics\n\n"
            "All run IN PARALLEL, then a Coordinator merges the results.",
            title="📖 Fan-out / Fan-in",
            border_style="yellow",
        )
    )

    result = await fan_out_fan_in("The Rise of AI Coding Assistants in Professional Software Development")

    # Show each perspective
    for p in result["perspectives"]:
        console.print(
            Panel(p["result"][:300] + "...", title=f"🔍 {p['name']}", border_style="cyan")
        )

    # Show merged result
    console.print(
        Panel(result["summary"], title="📋 Synthesized Summary", border_style="green")
    )

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "1. [cyan]Fan-out[/cyan] — asyncio.gather runs all agents simultaneously\n"
            "2. [cyan]Fan-in[/cyan] — Coordinator synthesizes all partial results\n"
            "3. [cyan]Speed[/cyan] — Total time ≈ slowest agent (not sum of all)\n"
            "4. [cyan]Quality[/cyan] — Multiple perspectives > single perspective\n\n"
            "[bold]REAL-WORLD USES:[/bold]\n"
            "• Multi-source research (search + DB + internal docs)\n"
            "• Multi-model consensus (GPT-4 + Claude + Gemini → best answer)\n"
            "• Parallel document processing",
            title="💡 When to Use Fan-out / Fan-in",
            border_style="green",
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
