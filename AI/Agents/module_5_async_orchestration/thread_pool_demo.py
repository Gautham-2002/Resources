"""
=============================================================================
MODULE 5 — DEMO 2: Thread Pool for Blocking Calls
=============================================================================
CONCEPT:
    Not all libraries support async. When you need to call BLOCKING (sync)
    functions from async code, use ThreadPoolExecutor.
    
    This wraps blocking calls in threads, so they don't block the event loop.
    
    Pattern:
        loop.run_in_executor(executor, blocking_function, *args)

WHAT THIS DEMO DOES:
    Shows how to run blocking OpenAI calls concurrently using threads
    when you can't use the async client.

RUN:
    python module_5_async_orchestration/thread_pool_demo.py
=============================================================================
"""

import sys
import os
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat  # This is the BLOCKING (sync) version

console = Console()


# =============================================================================
# Step 1: The blocking function we want to parallelize
# =============================================================================
def blocking_agent(task_name: str, prompt: str) -> dict:
    """
    A BLOCKING agent function that uses the sync OpenAI client.
    In many codebases, you'll have sync code you can't easily rewrite.
    """
    start = time.time()
    result = chat(prompt=prompt, system=f"You are a {task_name} agent.", max_tokens=150)
    duration = time.time() - start
    return {"task": task_name, "result": result, "duration": duration}


# =============================================================================
# Step 2: Run blocking functions in a thread pool
# =============================================================================
async def run_with_threadpool():
    """
    Use ThreadPoolExecutor to run BLOCKING functions concurrently.
    
    KEY INSIGHT: This doesn't make them truly async — it uses OS threads.
    But it still achieves parallelism because the blocking calls are I/O-bound
    (waiting for network responses), so threads work well here.
    """
    tasks = [
        ("Summarizer", "Summarize the concept of agent orchestration in 2 sentences."),
        ("Comparator", "Compare LangChain vs LangGraph in 2 sentences."),
        ("Advisor", "Give one key tip for building production agents in 2 sentences."),
        ("Historian", "Name one milestone in AI agent history in 2 sentences."),
    ]
    
    console.print(Panel(
        f"Running {len(tasks)} BLOCKING agents through ThreadPoolExecutor...",
        title="🔧 Thread Pool Execution",
        border_style="blue",
    ))
    
    # Create a thread pool with controlled concurrency
    executor = ThreadPoolExecutor(max_workers=4)
    loop = asyncio.get_event_loop()
    
    total_start = time.time()
    
    # Submit all blocking calls to the thread pool
    futures = [
        loop.run_in_executor(executor, blocking_agent, name, prompt)
        for name, prompt in tasks
    ]
    
    # Wait for all threads to complete
    results = await asyncio.gather(*futures)
    
    total_time = time.time() - total_start
    
    # Also measure sequential for comparison
    console.print("\n[dim]Now running the same tasks SEQUENTIALLY for comparison...[/dim]\n")
    seq_start = time.time()
    for name, prompt in tasks:
        blocking_agent(name, prompt)
    seq_time = time.time() - seq_start
    
    return results, total_time, seq_time


# =============================================================================
# Step 3: Display results
# =============================================================================
async def main():
    console.print(Panel(
        "[bold]Thread Pool Demo[/bold]\n\n"
        "When you have BLOCKING (sync) code that you can't rewrite as async,\n"
        "use ThreadPoolExecutor to achieve parallelism.\n\n"
        "This wraps each blocking call in an OS thread so they run concurrently.",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    results, pool_time, seq_time = await run_with_threadpool()
    
    # Results table
    table = Table(title="Thread Pool Results")
    table.add_column("Agent", style="cyan")
    table.add_column("Duration", style="yellow")
    table.add_column("Result", style="white", width=50)
    
    for r in results:
        table.add_row(r["task"], f"{r['duration']:.1f}s", r["result"][:50] + "...")
    
    console.print(table)
    
    # Comparison
    table2 = Table(title="⏱️ Performance")
    table2.add_column("Method", style="cyan")
    table2.add_column("Time", style="yellow")
    table2.add_row("Sequential (blocking)", f"{seq_time:.1f}s")
    table2.add_row("Thread Pool (parallel)", f"{pool_time:.1f}s")
    table2.add_row("Speedup", f"{seq_time/pool_time:.1f}x faster")
    
    console.print(table2)
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]ThreadPoolExecutor(max_workers=N)[/cyan] — Create a thread pool\n"
        "2. [cyan]loop.run_in_executor(pool, func, *args)[/cyan] — Run blocking func in thread\n"
        "3. [cyan]asyncio.gather(*futures)[/cyan] — Wait for all threads\n\n"
        "[bold]WHEN TO USE:[/bold]\n"
        "✅ Blocking libraries without async support\n"
        "✅ Legacy sync code you can't rewrite\n"
        "❌ CPU-bound work (use ProcessPoolExecutor instead)\n"
        "❌ If an async version exists (use it directly)",
        title="💡 Thread Pool Pattern",
        border_style="green",
    ))


if __name__ == "__main__":
    asyncio.run(main())
