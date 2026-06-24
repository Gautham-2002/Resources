"""
=============================================================================
MODULE 13 — DEMO 2: Fixed Workflow (Developer Controls Flow)
=============================================================================
CONCEPT:
    A workflow = YOU decide the sequence. The LLM fills in content, 
    not structure. No autonomous decision-making about what happens next.
    
    Compare this with agent_loop.py:
    - Agent: LLM decides → search? analyze? done?
    - Workflow: YOUR CODE decides → always step1, then step2, then step3
    
    Both use an LLM, but the CONTROL FLOW is fundamentally different.

RUN:
    python module_13_agent_fundamentals/workflow_example.py
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from shared.llm import chat

console = Console()


# =============================================================================
# A Fixed 3-Step Workflow — YOUR code determines what happens
# =============================================================================
def run_workflow(document: str) -> dict:
    """
    A fixed workflow: Summarize → Extract Entities → Write Report.
    
    Notice: the LLM has NO SAY in what happens next.
    Step 2 always follows step 1. Step 3 always follows step 2.
    The LLM just fills in the content at each step.
    """
    
    console.print(Panel(
        f"[bold]Workflow Starting[/bold]\n"
        f"Steps: Summarize → Extract Entities → Write Report\n"
        f"Input: {document[:100]}...",
        border_style="cyan",
    ))
    
    results = {}
    
    # — Step 1: Summarize (always runs first) —
    console.print("\n  [bold cyan]═══ Step 1: Summarize ═══[/bold cyan]")
    console.print("  [dim]This step is HARDCODED — the LLM doesn't decide to do this[/dim]")
    
    summary = chat(
        prompt=f"Summarize the following document in 3 sentences:\n\n{document}",
        system="You are a document summarizer. Be concise.",
        max_tokens=150,
    )
    results["summary"] = summary
    console.print(f"  [green]✅ Summary: {summary[:200]}[/green]")
    
    # — Step 2: Extract entities (always runs second) —
    console.print("\n  [bold cyan]═══ Step 2: Extract Entities ═══[/bold cyan]")
    console.print("  [dim]This step is HARDCODED — runs regardless of what Step 1 produced[/dim]")
    
    entities = chat(
        prompt=f"Extract all named entities (people, companies, technologies) from this text. List them as bullet points:\n\n{summary}",
        system="You are an entity extraction specialist. Return a bullet list.",
        max_tokens=200,
    )
    results["entities"] = entities
    console.print(f"  [green]✅ Entities: {entities[:200]}[/green]")
    
    # — Step 3: Write report (always runs third) —
    console.print("\n  [bold cyan]═══ Step 3: Write Report ═══[/bold cyan]")
    console.print("  [dim]This step is HARDCODED — always the final step[/dim]")
    
    report = chat(
        prompt=f"Write a brief executive report based on this summary and entities:\n\nSummary: {summary}\n\nKey Entities: {entities}",
        system="You are a report writer. Write a concise executive report with an introduction, key findings, and conclusion.",
        max_tokens=300,
    )
    results["report"] = report
    console.print(f"  [green]✅ Report: {report[:200]}...[/green]")
    
    return results


# =============================================================================
# Demo
# =============================================================================
if __name__ == "__main__":
    console.print(Panel(
        "[bold]Module 13 — Demo 2: Fixed Workflow[/bold]\n\n"
        "This demo shows a WORKFLOW — not an agent.\n"
        "The key difference:\n"
        "- The LLM has NO SAY in what happens next\n"
        "- Step 1 → Step 2 → Step 3 is hardcoded in YOUR code\n"
        "- The LLM just fills in content at each step\n\n"
        "Compare with agent_loop.py where the LLM DECIDES what to do.",
        title="📖 Workflow vs Agent",
        border_style="yellow",
    ))
    
    sample_doc = """
    AI agents are transforming software engineering in 2025. Companies like 
    Anthropic, OpenAI, and Google are building frameworks that allow LLMs to 
    autonomously use tools, make decisions, and complete complex tasks. 
    CrewAI and LangGraph have emerged as leading frameworks for building 
    multi-agent systems. The market is expected to reach $50 billion by 2027.
    Key challenges include context window management, error propagation in 
    multi-agent chains, and the need for robust production guardrails.
    """
    
    results = run_workflow(sample_doc)
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]Workflow[/cyan] — YOUR code controls the sequence\n"
        "2. [cyan]Agent[/cyan] — the LLM controls the sequence\n"
        "3. [cyan]Same LLM[/cyan] — both use the same LLM, but differently\n\n"
        "[bold]When to use a Workflow:[/bold]\n"
        "• Steps are known and fixed before runtime\n"
        "• Customer support pipelines, document processing, batch jobs\n"
        "• You want predictability, auditability, lower cost\n\n"
        "[bold]When to use an Agent:[/bold]\n"
        "• You don't know how many steps or which tools are needed\n"
        "• 'Research this and write a report' — could be 1 search or 7\n"
        "• The decision of what to do next depends on intermediate results",
        title="💡 Workflow vs Agent",
        border_style="green",
    ))
