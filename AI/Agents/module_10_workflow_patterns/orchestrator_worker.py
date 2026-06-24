"""
=============================================================================
PATTERN 4: Orchestrator-Worker — Dynamic Task Decomposition
=============================================================================
CONCEPT:
    A central ORCHESTRATOR agent analyzes a complex task, decomposes it
    into sub-tasks AT RUNTIME, delegates each to a WORKER agent,
    and assembles the final result.

    Unlike Prompt Chaining (fixed steps) or Fan-out (fixed agents),
    the Orchestrator DECIDES how many workers to spawn and what each does.

              ┌─→ Worker (sub-task A) ─┐
    Orchestrator ─┼─→ Worker (sub-task B) ─┼─→ Orchestrator → Final
              └─→ Worker (sub-task C) ─┘

WHEN TO USE:
    ✅ Tasks are too complex to predefine all steps
    ✅ The number of sub-tasks varies per input
    ✅ You need dynamic planning + execution
    ❌ Task structure is always the same (use Prompt Chaining)
    ❌ You need strict, auditable workflows (use State Machine)

RUN:
    python module_10_workflow_patterns/orchestrator_worker.py
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
# Step 1: The Orchestrator — plans and decomposes
# =============================================================================
def orchestrator_plan(task: str) -> list[dict]:
    """
    The ORCHESTRATOR analyzes the task and creates a dynamic execution plan.

    KEY INSIGHT: The plan is NOT predetermined — the LLM generates it
    based on the specific task. Different tasks produce different plans.
    """
    console.print(
        Panel(f"Task: {task}", title="🧠 Orchestrator — Planning", border_style="blue")
    )

    result = chat(
        prompt=f"""Decompose this complex task into 3-5 independent sub-tasks that workers can execute:

Task: {task}

Reply in this JSON format:
[
  {{"id": 1, "title": "Sub-task title", "instruction": "Detailed instruction for the worker"}},
  {{"id": 2, "title": "Sub-task title", "instruction": "Detailed instruction for the worker"}}
]

Make sub-tasks specific and self-contained. Each worker operates independently.""",
        system="You are a project manager agent. Decompose complex tasks into clear, actionable sub-tasks. Reply with valid JSON only.",
        max_tokens=500,
        temperature=0,
    )

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        sub_tasks = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        sub_tasks = [
            {"id": 1, "title": "Research", "instruction": f"Research: {task}"},
            {"id": 2, "title": "Analysis", "instruction": f"Analyze: {task}"},
            {"id": 3, "title": "Summary", "instruction": f"Summarize findings about: {task}"},
        ]

    console.print(f"  [green]📋 Created {len(sub_tasks)} sub-tasks:[/green]")
    for st in sub_tasks:
        console.print(f"    {st['id']}. {st['title']}")

    return sub_tasks


# =============================================================================
# Step 2: Worker Agent — executes a single sub-task
# =============================================================================
def worker_execute(sub_task: dict) -> dict:
    """
    A WORKER agent executes a single sub-task.

    Workers are generic — they don't know about the overall plan.
    They just execute their specific instruction.
    """
    console.print(f"\n  [yellow]⚙️  Worker {sub_task['id']}:[/yellow] {sub_task['title']}")

    result = chat(
        prompt=sub_task["instruction"],
        system="You are a worker agent. Execute the given task thoroughly and return a concise result.",
        max_tokens=300,
    )

    console.print(f"    [green]✅ Complete[/green]: {result[:80]}...")
    return {"id": sub_task["id"], "title": sub_task["title"], "result": result}


# =============================================================================
# Step 3: Orchestrator — assembles final result
# =============================================================================
def orchestrator_assemble(task: str, worker_results: list[dict]) -> str:
    """
    The ORCHESTRATOR assembles worker outputs into a final result.

    This is the second role of the orchestrator: synthesis.
    """
    console.print(
        Panel("Assembling worker results...", title="🧠 Orchestrator — Assembly", border_style="magenta")
    )

    combined = "\n\n".join([
        f"### {r['title']}:\n{r['result']}" for r in worker_results
    ])

    result = chat(
        prompt=f"""You decomposed this task: "{task}"

Your workers produced these results:

{combined}

Assemble these into a comprehensive, unified final deliverable.""",
        system="You are a project coordinator. Synthesize sub-task results into a polished final output.",
        max_tokens=500,
    )

    return result


# =============================================================================
# Step 4: Full Pipeline
# =============================================================================
def run_orchestrator_worker(task: str) -> dict:
    """Execute the full orchestrator-worker pattern."""
    # Phase 1: Plan
    sub_tasks = orchestrator_plan(task)

    # Phase 2: Execute workers
    console.print(
        Panel(f"Executing {len(sub_tasks)} workers...", title="⚙️  Workers", border_style="yellow")
    )
    worker_results = [worker_execute(st) for st in sub_tasks]

    # Phase 3: Assemble
    final = orchestrator_assemble(task, worker_results)

    return {
        "task": task,
        "sub_tasks": sub_tasks,
        "worker_results": worker_results,
        "final_output": final,
    }


if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Pattern: Orchestrator-Worker[/bold]\n\n"
            "The Orchestrator DYNAMICALLY plans sub-tasks,\n"
            "delegates to Workers, and assembles the final result.\n\n"
            "Unlike Prompt Chaining, the plan is generated AT RUNTIME.",
            title="📖 Orchestrator-Worker",
            border_style="yellow",
        )
    )

    result = run_orchestrator_worker(
        "Create a comprehensive comparison of Python web frameworks "
        "(Django, FastAPI, Flask) for building AI agent APIs, "
        "covering performance, ecosystem, learning curve, and production readiness."
    )

    console.print(
        Panel(result["final_output"], title="📋 Final Output", border_style="green")
    )

    # Show the dynamic plan
    table = Table(title="Dynamic Execution Plan")
    table.add_column("#", style="cyan", width=3)
    table.add_column("Sub-task", style="white", width=25)
    table.add_column("Result Preview", style="dim", width=50)

    for wr in result["worker_results"]:
        table.add_row(str(wr["id"]), wr["title"], wr["result"][:50] + "...")

    console.print(table)

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "1. [cyan]Dynamic planning[/cyan] — the LLM generates the task decomposition\n"
            "2. [cyan]Generic workers[/cyan] — workers don't know the overall plan\n"
            "3. [cyan]Two-phase orchestrator[/cyan] — plans first, assembles last\n"
            "4. [cyan]Adaptive[/cyan] — different inputs produce different plans\n\n"
            "[bold]REAL-WORLD USES:[/bold]\n"
            "• Complex research tasks (the scope isn't known upfront)\n"
            "• Software project planning (decompose feature into tasks)\n"
            "• Report generation from multiple data sources",
            title="💡 When to Use Orchestrator-Worker",
            border_style="green",
        )
    )
