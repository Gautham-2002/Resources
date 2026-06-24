"""
=============================================================================
FRAMEWORK 5: Google ADK (Agent Development Kit)
=============================================================================
Install: pip install google-adk
Docs: https://google.github.io/adk-docs

KEY FEATURES:
    - Official Google framework for building agents
    - Code-first approach (agents defined in Python)
    - Built-in multi-agent orchestration
    - Rich tool ecosystem (Google Search, Code Exec, etc.)
    - Optimized for Gemini models + Vertex AI
    - Built-in evaluation and testing tools

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
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    # =================================================================
    # Define tools as plain Python functions
    # ADK uses function docstrings and type hints for tool schemas
    # =================================================================
    def get_research_findings(topic: str) -> dict:
        """Research a topic and return key findings.

        Args:
            topic: The topic to research.

        Returns:
            A dictionary with research findings.
        """
        return {
            "status": "success",
            "findings": [
                f"Finding 1: {topic} is experiencing rapid growth",
                f"Finding 2: Key players in {topic} include major tech companies",
                f"Finding 3: Challenges in {topic} include scalability and ethics",
                f"Finding 4: Investment in {topic} has increased 300% since 2023",
                f"Finding 5: {topic} is expected to mature by 2027",
            ],
        }

    # =================================================================
    # Define agents using ADK's Agent class
    # =================================================================
    # In ADK, sub-agents are passed to parent agents for orchestration
    analyst_agent = Agent(
        model="gemini-2.0-flash",
        name="analyst_agent",
        description="Analyzes research findings and extracts insights.",
        instruction="""You are a strategic analyst. When given research findings,
        extract 3 key insights with supporting evidence. Be concise and actionable.""",
    )

    writer_agent = Agent(
        model="gemini-2.0-flash",
        name="writer_agent",
        description="Writes professional reports from research and analysis.",
        instruction="""You are a report writer. Create a professional report with
        an executive summary, key findings, and 3 recommendations.""",
    )

    # Root agent orchestrates the sub-agents
    root_agent = Agent(
        model="gemini-2.0-flash",
        name="research_orchestrator",
        description="Orchestrates a research pipeline with specialized sub-agents.",
        instruction="""You are a research orchestrator. When given a topic:
        1. Use the get_research_findings tool to gather data
        2. Delegate analysis to the analyst_agent
        3. Delegate report writing to the writer_agent
        Coordinate the workflow and return the final report.""",
        tools=[get_research_findings],
        sub_agents=[analyst_agent, writer_agent],
    )

    async def run_google_adk(topic: str) -> str:
        """
        Run research pipeline using Google ADK.

        KEY CONCEPTS:
        - Agent: name, model, instruction, tools, sub_agents
        - Runner: manages execution lifecycle
        - Sessions: track conversation state
        - Sub-agents: parent delegates to child agents
        """
        session_service = InMemorySessionService()
        runner = Runner(
            agent=root_agent,
            app_name="research_app",
            session_service=session_service,
        )

        session = await session_service.create_session(
            app_name="research_app",
            user_id="demo_user",
        )

        from google.genai import types

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"Research and write a report about: {topic}")],
        )

        final_response = ""
        async for event in runner.run_async(
            user_id="demo_user",
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response():
                for part in event.content.parts:
                    if part.text:
                        final_response += part.text

        return final_response

    HAS_FRAMEWORK = True

except ImportError:
    HAS_FRAMEWORK = False

    async def run_google_adk(topic: str) -> str:
        return "Google ADK not installed. Run: pip install google-adk"


# =============================================================================
# Run the demo
# =============================================================================
if __name__ == "__main__":
    import asyncio

    console.print(
        Panel(
            "[bold]Framework: Google ADK[/bold]\n\n"
            "Key concepts demonstrated:\n"
            "  • [cyan]Agent(name, model, instruction, tools, sub_agents)[/cyan]\n"
            "  • [cyan]Runner[/cyan] — manages execution lifecycle\n"
            "  • [cyan]sub_agents=[...][/cyan] — built-in multi-agent orchestration\n"
            "  • [cyan]Tools as functions[/cyan] — type hints become tool schema\n\n"
            "Pipeline: Root Agent → (tool call) → Analyst Sub-Agent → Writer Sub-Agent",
            title="📖 Google ADK",
            border_style="yellow",
        )
    )

    if not HAS_FRAMEWORK:
        console.print("[red]⚠ Install first: pip install google-adk[/red]")
        console.print("[yellow]  Also set GOOGLE_API_KEY in your .env file[/yellow]")
    else:
        result = asyncio.run(
            run_google_adk("How AI Agents Are Transforming Software Engineering in 2025")
        )
        console.print(Panel(result, title="📋 Final Report", border_style="green"))

    console.print(
        Panel(
            "[bold]GOOGLE ADK — SUMMARY:[/bold]\n"
            "✅ [green]Official Google[/green] — first-party, production-ready\n"
            "✅ [green]Multi-agent native[/green] — sub_agents built into Agent class\n"
            "✅ [green]Code-first[/green] — agents defined in Python, not config files\n"
            "✅ [green]Google ecosystem[/green] — Vertex AI, Cloud Run, BigQuery\n"
            "✅ [green]Built-in eval[/green] — test and evaluate agents programmatically\n"
            "❌ [red]Gemini-optimized[/red] — best with Google models\n"
            "❌ [red]Newer framework[/red] — smaller community than LangChain",
            title="💡 When to Choose Google ADK",
            border_style="green",
        )
    )
