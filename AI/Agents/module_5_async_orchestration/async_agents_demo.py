"""
=============================================================================
MODULE 5 — DEMO 1: Async Agents with asyncio
=============================================================================
CONCEPT:
    When agents call LLMs, they spend 90%+ of time WAITING for responses.
    Running agents concurrently with asyncio lets you execute multiple
    LLM calls in parallel, dramatically reducing total execution time.
    
    Sequential: Agent1(3s) → Agent2(3s) → Agent3(3s) = 9 seconds
    Parallel:   Agent1(3s) ┐
                Agent2(3s) ├ = 3 seconds  (3x faster!)
                Agent3(3s) ┘

WHAT THIS DEMO DOES:
    1. Runs 3 research agents SEQUENTIALLY → measures time
    2. Runs the same 3 agents in PARALLEL → measures time
    3. Shows the dramatic speed difference

RUN:
    python module_5_async_orchestration/async_agents_demo.py
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
from shared.llm import chat, achat

console = Console()


# =============================================================================
# Step 1: Define the research agents
# =============================================================================
RESEARCH_TOPICS = [
    ("Market Research", "Research current trends in AI agent frameworks. List top 3 frameworks and their strengths."),
    ("Technical Analysis", "Analyze the technical challenges of building multi-agent systems. List top 3 challenges."),
    ("Use Case Survey", "Survey real-world use cases of AI agents in enterprise. List top 3 use cases."),
]


def run_agent_sync(name: str, prompt: str) -> dict:
    """Run a single research agent SYNCHRONOUSLY."""
    start = time.time()
    result = chat(
        prompt=prompt,
        system=f"You are a {name} agent. Be concise and specific.",
        max_tokens=200,
    )
    duration = time.time() - start
    return {"name": name, "result": result, "duration": duration}


async def run_agent_async(name: str, prompt: str) -> dict:
    """Run a single research agent ASYNCHRONOUSLY."""
    start = time.time()
    result = await achat(
        prompt=prompt,
        system=f"You are a {name} agent. Be concise and specific.",
        max_tokens=200,
    )
    duration = time.time() - start
    return {"name": name, "result": result, "duration": duration}


# =============================================================================
# Step 2: Sequential execution (the slow way)
# =============================================================================
def run_sequential():
    """Run all agents one after another."""
    console.print("\n[bold red]🐌 SEQUENTIAL EXECUTION[/bold red] — One at a time...\n")
    
    results = []
    total_start = time.time()
    
    for name, prompt in RESEARCH_TOPICS:
        console.print(f"  ▶ Running {name}...")
        result = run_agent_sync(name, prompt)
        results.append(result)
        console.print(f"  ✅ {name} done in {result['duration']:.1f}s")
    
    total_time = time.time() - total_start
    console.print(f"\n  [bold red]Total time: {total_time:.1f}s[/bold red]")
    
    return results, total_time


# =============================================================================
# Step 3: Parallel execution (the fast way)
# =============================================================================
async def run_parallel():
    """Run all agents CONCURRENTLY using asyncio.gather."""
    console.print("\n[bold green]⚡ PARALLEL EXECUTION[/bold green] — All at once!\n")
    
    total_start = time.time()
    
    # Create async tasks for all agents
    tasks = [
        run_agent_async(name, prompt)
        for name, prompt in RESEARCH_TOPICS
    ]
    
    console.print(f"  ▶ Running {len(tasks)} agents concurrently...")
    
    # asyncio.gather runs all tasks in parallel!
    results = await asyncio.gather(*tasks)
    
    total_time = time.time() - total_start
    
    for r in results:
        console.print(f"  ✅ {r['name']} done in {r['duration']:.1f}s")
    
    console.print(f"\n  [bold green]Total time: {total_time:.1f}s[/bold green]")
    
    return results, total_time


# =============================================================================
# Step 4: Coordinator — merges parallel results
# =============================================================================
async def coordinate_and_merge(results: list[dict]) -> str:
    """
    COORDINATOR PATTERN: A final agent merges the parallel results.
    
    This is the fan-out/fan-in pattern:
    1. Fan-out: Multiple agents research in parallel
    2. Fan-in: Coordinator merges all results into a single report
    """
    console.print("\n[bold cyan]🔗 Coordinator[/bold cyan] — Merging results...\n")
    
    combined = "\n\n".join([
        f"### {r['name']}:\n{r['result']}" for r in results
    ])
    
    summary = await achat(
        prompt=f"Synthesize these research findings into a brief executive summary:\n\n{combined}",
        system="You are a research coordinator. Create concise, unified summaries.",
        max_tokens=300,
    )
    
    return summary


# =============================================================================
# Step 5: Run the comparison
# =============================================================================
async def main():
    console.print(Panel(
        "[bold]Async Orchestration Demo[/bold]\n\n"
        "This demo runs 3 research agents both SEQUENTIALLY and PARALLEL.\n"
        "Watch the execution time difference!\n\n"
        "Sequential: Agent1 → Agent2 → Agent3 (each waits for previous)\n"
        "Parallel:   Agent1 ┐\n"
        "            Agent2 ├ All run at the same time!\n"
        "            Agent3 ┘",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    # Run sequential
    seq_results, seq_time = run_sequential()
    
    # Run parallel
    par_results, par_time = await run_parallel()
    
    # Merge parallel results
    merged_report = await coordinate_and_merge(par_results)
    
    # Show the merged report
    console.print(Panel(merged_report, title="📋 Merged Research Report", border_style="green"))
    
    # Comparison table
    table = Table(title="⏱️ Performance Comparison")
    table.add_column("Metric", style="cyan")
    table.add_column("Sequential", style="red")
    table.add_column("Parallel", style="green")
    
    table.add_row("Total Time", f"{seq_time:.1f}s", f"{par_time:.1f}s")
    table.add_row("Speedup", "1x (baseline)", f"{seq_time/par_time:.1f}x faster!")
    table.add_row("Agents Run", str(len(seq_results)), str(len(par_results)))
    
    console.print(table)
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]asyncio.gather(*tasks)[/cyan] — Run multiple coroutines in parallel\n"
        "2. [cyan]await achat(...)[/cyan] — Non-blocking LLM call\n"
        "3. [cyan]Fan-out/Fan-in[/cyan] — Parallel execution → merge results\n"
        "4. The COORDINATOR pattern merges parallel results\n\n"
        "[bold]WHEN TO USE:[/bold]\n"
        "✅ Multiple independent LLM calls\n"
        "✅ Research tasks that don't depend on each other\n"
        "❌ Steps with dependencies (use DAG instead)\n"
        "❌ When order matters",
        title="💡 Async Agent Orchestration",
        border_style="green",
    ))


if __name__ == "__main__":
    asyncio.run(main())
