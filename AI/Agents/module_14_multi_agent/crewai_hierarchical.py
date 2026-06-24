"""
=============================================================================
MODULE 14 — DEMO 2: CrewAI Hierarchical (True Multi-Agent Orchestration)
=============================================================================
CONCEPT:
    Process.hierarchical — a MANAGER LLM is automatically created.
    
    The manager:
    - Reads all tasks
    - Decides which agent handles which task
    - Decides the order
    - Can re-assign or ask for revisions
    
    The manager IS an orchestrator agent.
    This is TRUE multi-agent orchestration:
    an LLM decides the flow, not your code.
    
    Compare with crewai_sequential.py where YOU defined the order.

RUN:
    python module_14_multi_agent/crewai_hierarchical.py
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel

console = Console()

try:
    from crewai import Agent, Task, Crew, Process
    from crewai_tools import SerperDevTool, ScrapeWebsiteTool
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False


def run_hierarchical_crew(topic: str):
    """
    Process.hierarchical — a MANAGER LLM controls delegation.
    
    The manager reads all tasks, decides which agent does what,
    in what order, and whether to retry. This is true multi-agent 
    orchestration — the LLM decides the flow.
    """
    if not HAS_CREWAI:
        console.print("[red]CrewAI not installed. Run: pip install crewai crewai-tools[/red]")
        return None
    
    search_tool = SerperDevTool()
    scrape_tool = ScrapeWebsiteTool()
    
    researcher = Agent(
        role="Senior Research Analyst",
        goal="Find accurate, up-to-date information on the given topic",
        backstory="You are an expert at finding and verifying information online.",
        tools=[search_tool, scrape_tool],
        verbose=True,
        llm="gpt-4o",
    )
    
    analyst = Agent(
        role="Data Analyst",
        goal="Interpret research findings and extract key insights",
        backstory="You turn raw information into clear, structured insights.",
        tools=[],
        verbose=True,
        llm="gpt-4o",
    )
    
    writer = Agent(
        role="Content Writer",
        goal="Write a compelling, well-structured report",
        backstory="You write clear, professional content for business audiences.",
        tools=[],
        verbose=True,
        llm="gpt-4o",
    )
    
    research_task = Task(
        description=f"Research the current state of {topic}. Find key players, "
                    "recent developments, and market trends.",
        expected_output="A structured list of facts, sources, and key findings.",
        agent=researcher,
    )
    
    analysis_task = Task(
        description="Analyse the research findings. Identify the 3 most important "
                    "insights and explain why they matter.",
        expected_output="A short analysis with 3 key insights and their implications.",
        agent=analyst,
        context=[research_task],
    )
    
    writing_task = Task(
        description="Write a 500-word executive report based on the analysis.",
        expected_output="A professional report with introduction, insights, conclusion.",
        agent=writer,
        context=[research_task, analysis_task],
    )
    
    # -- The critical difference: Process.hierarchical --
    # A manager LLM is automatically created. IT decides:
    # - Which agent handles which task
    # - In what order
    # - Whether to retry
    crew = Crew(
        agents=[researcher, analyst, writer],
        tasks=[research_task, analysis_task, writing_task],
        process=Process.hierarchical,  # manager LLM controls delegation
        manager_llm="gpt-4o",          # the orchestrator model
        verbose=True,
    )
    
    console.print(Panel(
        "[bold]CrewAI — Hierarchical Process[/bold]\n\n"
        "Process.hierarchical = a MANAGER LLM is created.\n"
        "The manager decides:\n"
        "- Which agent handles which task\n"
        "- In what order they run\n"
        "- Whether to retry or reassign\n\n"
        "This is TRUE multi-agent orchestration.",
        border_style="magenta",
    ))
    
    result = crew.kickoff(inputs={"topic": topic})
    return result


if __name__ == "__main__":
    console.print(Panel(
        "[bold]Module 14 — Demo 2: CrewAI Hierarchical[/bold]\n\n"
        "This demo shows Process.hierarchical — TRUE orchestration.\n\n"
        "SEQUENTIAL (previous demo):\n"
        "  → YOU defined order: researcher → analyst → writer\n"
        "  → This is a workflow built from agents\n\n"
        "HIERARCHICAL (this demo):\n"
        "  → A MANAGER LLM decides which agent does what\n"
        "  → It can re-assign, retry, change the order\n"
        "  → The manager IS an orchestrator agent",
        title="📖 Sequential vs Hierarchical",
        border_style="yellow",
    ))
    
    result = run_hierarchical_crew("AI agents in 2025")
    
    if result:
        console.print(Panel(str(result), title="📄 Final Report", border_style="green"))
    
    console.print(Panel(
        "[bold]THE CRITICAL DIFFERENCE:[/bold]\n"
        "1. [cyan]Sequential[/cyan] — YOU defined order. It's a workflow.\n"
        "2. [cyan]Hierarchical[/cyan] — MANAGER LLM decides. It's orchestration.\n\n"
        "[bold]In hierarchical mode:[/bold]\n"
        "• A manager agent is auto-created\n"
        "• It reads all tasks and decides assignment\n"
        "• It can delegate, re-assign, ask for revisions\n"
        "• That manager is the orchestrator",
        title="💡 CrewAI Hierarchical = True Orchestration",
        border_style="green",
    ))
