"""
=============================================================================
FRAMEWORK 1: OpenAI Agents SDK (formerly Swarm)
=============================================================================
Install: pip install openai-agents
Docs: https://github.com/openai/openai-agents-python

KEY FEATURES:
    - Official OpenAI framework (production-ready, replaces Swarm)
    - Built-in handoffs (agent-to-agent delegation)
    - Guardrails for input/output validation
    - Tool use with Python functions
    - Tracing for debugging
    - Uses OpenAI models natively

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
    from agents import Agent, Runner, function_tool

    # =================================================================
    # Define tools
    # =================================================================
    @function_tool
    def get_current_date() -> str:
        """Returns the current date."""
        from datetime import date
        return str(date.today())

    # =================================================================
    # Define agents with handoff capability
    # =================================================================
    report_writer = Agent(
        name="Report Writer",
        instructions="""You are a report writer. You receive research and analysis,
        and write a concise, well-structured final report. Include an executive
        summary and 3 key recommendations.""",
    )

    analyst = Agent(
        name="Analyst",
        instructions="""You are a data analyst. You receive research findings and
        extract 3 key insights with supporting evidence. After analysis, hand off
        to the Report Writer for the final report.""",
        handoffs=[report_writer],
    )

    researcher = Agent(
        name="Researcher",
        instructions="""You are a researcher. When given a topic, research it and
        provide 5 key findings with details. After research, hand off to the
        Analyst for deeper analysis.""",
        handoffs=[analyst],
        tools=[get_current_date],
    )

    def run_openai_agents(topic: str) -> str:
        """Run the multi-agent pipeline using OpenAI Agents SDK."""
        result = Runner.run_sync(
            researcher,
            f"Research this topic thoroughly: {topic}",
        )
        return result.final_output

    HAS_FRAMEWORK = True

except ImportError:
    HAS_FRAMEWORK = False

    def run_openai_agents(topic: str) -> str:
        return "OpenAI Agents SDK not installed. Run: pip install openai-agents"


# =============================================================================
# Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Framework: OpenAI Agents SDK[/bold]\n\n"
            "Key concepts demonstrated:\n"
            "  • [cyan]Agent[/cyan] — defines name, instructions, tools, handoffs\n"
            "  • [cyan]Runner.run_sync[/cyan] — executes the agent synchronously\n"
            "  • [cyan]handoffs=[other_agent][/cyan] — built-in agent-to-agent delegation\n"
            "  • [cyan]@function_tool[/cyan] — register Python functions as tools\n\n"
            "Pipeline: Researcher → (handoff) → Analyst → (handoff) → Report Writer",
            title="📖 OpenAI Agents SDK",
            border_style="yellow",
        )
    )

    if not HAS_FRAMEWORK:
        console.print("[red]⚠ Install first: pip install openai-agents[/red]")
    else:
        result = run_openai_agents("How AI Agents Are Transforming Software Engineering in 2025")
        console.print(Panel(result, title="📋 Final Report", border_style="green"))

    console.print(
        Panel(
            "[bold]OPENAI AGENTS SDK — SUMMARY:[/bold]\n"
            "✅ [green]Official OpenAI[/green] — first-party support, guaranteed compatibility\n"
            "✅ [green]Built-in handoffs[/green] — agent-to-agent delegation is native\n"
            "✅ [green]Tracing built-in[/green] — debug agent chains easily\n"
            "✅ [green]Guardrails[/green] — validate inputs/outputs\n"
            "❌ [red]OpenAI only[/red] — locked to OpenAI models\n"
            "❌ [red]Newer framework[/red] — smaller ecosystem than LangChain",
            title="💡 When to Choose OpenAI Agents SDK",
            border_style="green",
        )
    )
