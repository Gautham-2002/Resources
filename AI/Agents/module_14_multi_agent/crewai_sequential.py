"""
=============================================================================
MODULE 14 — DEMO 1: Multi-Agent with CrewAI
=============================================================================
CONCEPT:
    CrewAI gives agents roles, goals, and backstories — like assigning 
    team members to a project.
    
    Two critical modes:
    
    Process.sequential — YOU define the order. Tasks always run
    researcher → analyst → writer. This is a WORKFLOW built from agents.
    
    Process.hierarchical — a MANAGER LLM is instantiated. It reads all
    tasks and decides which agent does what, in what order, and whether
    to retry. The manager IS an orchestrator agent. This is TRUE 
    multi-agent orchestration.
    
    That distinction is the key insight.

RUN:
    python module_14_multi_agent/crewai_sequential.py
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


def run_sequential_crew(topic: str):
    """
    Process.sequential — YOU define the order.
    
    Tasks always run: researcher → analyst → writer.
    This is a WORKFLOW built from agents. The order is fixed.
    """
    if not HAS_CREWAI:
        console.print("[red]CrewAI not installed. Run: pip install crewai crewai-tools[/red]")
        return None
    
    # -- Tools --
    search_tool = SerperDevTool()
    scrape_tool = ScrapeWebsiteTool()
    
    # -- Agents (each is an independent loop with its own LLM + tools) --
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
        tools=[],  # no external tools
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
    
    # -- Tasks (context= wires output of one task as input to the next) --
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
        context=[research_task],  # gets researcher's output as context
    )
    
    writing_task = Task(
        description="Write a 500-word executive report based on the analysis.",
        expected_output="A professional report with introduction, insights, conclusion.",
        agent=writer,
        context=[research_task, analysis_task],  # gets both outputs
    )
    
    # -- Crew: Process.sequential = fixed order (workflow) --
    crew = Crew(
        agents=[researcher, analyst, writer],
        tasks=[research_task, analysis_task, writing_task],
        process=Process.sequential,  # order defined by YOU
        verbose=True,
    )
    
    console.print(Panel(
        "[bold]CrewAI — Sequential Process[/bold]\n\n"
        "Process.sequential = YOU defined the order.\n"
        "Tasks ALWAYS run: researcher → analyst → writer.\n"
        "This is a WORKFLOW built from agents.",
        border_style="cyan",
    ))
    
    result = crew.kickoff(inputs={"topic": topic})
    return result


if __name__ == "__main__":
    console.print(Panel(
        "[bold]Module 14 — Demo 1: CrewAI Sequential[/bold]\n\n"
        "This demo shows CrewAI's Process.sequential mode.\n\n"
        "Key insight: This is a WORKFLOW built from agents.\n"
        "- Each agent is its own independent loop (LLM + tools)\n"
        "- But YOU defined the order: researcher → analyst → writer\n"
        "- The agents don't decide what happens next — your code does\n\n"
        "Compare with crewai_hierarchical.py where a MANAGER LLM\n"
        "decides the order — that's true multi-agent orchestration.",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    result = run_sequential_crew("AI agents in 2025")
    
    if result:
        console.print(Panel(str(result), title="📄 Final Report", border_style="green"))
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]Process.sequential[/cyan] — YOU define order: always R → A → W\n"
        "2. [cyan]context=[task][/cyan] — wires one task's output to the next\n"
        "3. [cyan]Each agent[/cyan] — runs its own loop with its own LLM + tools\n"
        "4. [cyan]This is a workflow[/cyan] — agents are the executors, not the decision-makers\n\n"
        "[bold]Next:[/bold] Run crewai_hierarchical.py to see true orchestration.",
        title="💡 CrewAI Sequential = Workflow",
        border_style="green",
    ))
