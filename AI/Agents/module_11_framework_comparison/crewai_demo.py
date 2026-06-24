"""
=============================================================================
FRAMEWORK 3: CrewAI — Role-Based Multi-Agent Crews
=============================================================================
Install: pip install crewai
Docs: https://docs.crewai.com

KEY FEATURES:
    - Role-based agent design (agents have roles, goals, backstories)
    - Sequential and hierarchical process modes
    - Built-in task management (tasks with descriptions, expected outputs)
    - Agents collaborate naturally through crew orchestration
    - YAML-based configuration option

THE SAME TASK: Research → Analyze → Report
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

    # =================================================================
    # Define agents with ROLES, GOALS, and BACKSTORIES
    # This is CrewAI's signature pattern — agents are "characters"
    # =================================================================
    researcher = Agent(
        role="Senior Research Analyst",
        goal="Discover and compile comprehensive research findings on the given topic",
        backstory="""You are an experienced research analyst with 15 years of experience
        in technology research. You excel at finding key trends, data points,
        and insights from multiple sources.""",
        verbose=True,
        allow_delegation=False,
    )

    analyst = Agent(
        role="Strategic Analyst",
        goal="Extract actionable insights from research findings",
        backstory="""You are a strategic analyst who specializes in turning raw research
        into actionable business insights. You identify patterns, risks,
        and opportunities that others miss.""",
        verbose=True,
        allow_delegation=False,
    )

    writer = Agent(
        role="Technical Report Writer",
        goal="Write a clear, professional report with executive summary and recommendations",
        backstory="""You are a seasoned technical writer who creates reports that
        executives actually want to read. You combine clarity with depth.""",
        verbose=True,
        allow_delegation=False,
    )

    def run_crewai(topic: str) -> str:
        """
        Run research pipeline using CrewAI.

        KEY CONCEPTS:
        - Agent: has role, goal, backstory (personality-driven)
        - Task: has description, expected_output, agent assignment
        - Crew: orchestrates agents on tasks (sequential or hierarchical)
        """
        # Define tasks
        research_task = Task(
            description=f"Research the topic '{topic}'. Provide 5 key findings with supporting details.",
            expected_output="A numbered list of 5 key research findings with evidence.",
            agent=researcher,
        )

        analysis_task = Task(
            description="Analyze the research findings and extract 3 key strategic insights.",
            expected_output="3 actionable insights with supporting evidence from the research.",
            agent=analyst,
        )

        report_task = Task(
            description=f"Write a professional report about '{topic}' using the research and analysis.",
            expected_output="A structured report with executive summary and 3 recommendations.",
            agent=writer,
        )

        # Create and run the crew
        crew = Crew(
            agents=[researcher, analyst, writer],
            tasks=[research_task, analysis_task, report_task],
            process=Process.sequential,  # Tasks run one after another
            verbose=True,
        )

        result = crew.kickoff()
        return str(result)

    HAS_FRAMEWORK = True

except ImportError:
    HAS_FRAMEWORK = False

    def run_crewai(topic: str) -> str:
        return "CrewAI not installed. Run: pip install crewai"


# =============================================================================
# Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Framework: CrewAI[/bold]\n\n"
            "Key concepts demonstrated:\n"
            "  • [cyan]Agent(role, goal, backstory)[/cyan] — personality-driven agents\n"
            "  • [cyan]Task(description, expected_output, agent)[/cyan] — structured tasks\n"
            "  • [cyan]Crew(agents, tasks, process)[/cyan] — orchestration\n"
            "  • [cyan]Process.sequential[/cyan] — tasks run one after another\n\n"
            "Pipeline: Researcher → Analyst → Writer (as a Crew)",
            title="📖 CrewAI",
            border_style="yellow",
        )
    )

    if not HAS_FRAMEWORK:
        console.print("[red]⚠ Install first: pip install crewai[/red]")
    else:
        result = run_crewai("How AI Agents Are Transforming Software Engineering in 2025")
        console.print(Panel(result, title="📋 Final Report", border_style="green"))

    console.print(
        Panel(
            "[bold]CREWAI — SUMMARY:[/bold]\n"
            "✅ [green]Role-based design[/green] — agents feel like team members\n"
            "✅ [green]Natural delegation[/green] — agents can delegate to each other\n"
            "✅ [green]Expected outputs[/green] — tasks define what success looks like\n"
            "✅ [green]YAML config[/green] — define crews without code\n"
            "❌ [red]Abstraction overhead[/red] — simple tasks feel over-engineered\n"
            "❌ [red]Verbose output[/red] — lots of logging by default\n"
            "❌ [red]Less fine-grained control[/red] — harder to customize exact prompts",
            title="💡 When to Choose CrewAI",
            border_style="green",
        )
    )
