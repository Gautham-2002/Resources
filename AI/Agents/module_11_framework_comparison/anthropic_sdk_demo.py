"""
=============================================================================
FRAMEWORK 6: Anthropic Claude SDK — Tool Use and Extended Thinking
=============================================================================
Install: pip install anthropic
Docs: https://docs.anthropic.com/en/docs/agents-and-tools

KEY FEATURES:
    - Direct access to Claude models (Sonnet, Haiku, Opus)
    - Tool use (function calling) with structured definitions
    - Extended thinking for complex reasoning
    - Streaming responses
    - System prompts with caching
    - No abstraction layers — raw API power

THE SAME TASK: Research → Analyze → Report
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from shared.config import get_env

console = Console()

try:
    import anthropic
    import json

    client = anthropic.Anthropic(api_key=get_env("ANTHROPIC_API_KEY"))

    # =================================================================
    # Define tools for Claude (JSON schema format)
    # =================================================================
    TOOLS = [
        {
            "name": "save_research",
            "description": "Save research findings for the analysis step.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "findings": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of research findings",
                    },
                    "quality_score": {
                        "type": "integer",
                        "description": "Quality score 1-10",
                    },
                },
                "required": ["findings"],
            },
        },
        {
            "name": "save_analysis",
            "description": "Save analysis results for the report step.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "insights": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of analysis insights",
                    },
                    "recommendation": {
                        "type": "string",
                        "description": "Key recommendation",
                    },
                },
                "required": ["insights"],
            },
        },
    ]

    def run_anthropic_sdk(topic: str) -> dict:
        """
        Run research pipeline using Anthropic Claude SDK.

        KEY CONCEPTS:
        - Tool use: define tools as JSON schemas
        - Agentic loop: call LLM → check for tool use → provide tool results → repeat
        - System prompts: set agent personality
        """
        research_data = {}
        analysis_data = {}

        # Step 1: Research with tool use
        console.print("  [blue]🔬 Step 1: Research (Claude + tool use)[/blue]")
        messages = [
            {"role": "user", "content": f"Research the topic '{topic}'. Provide 5 key findings. Use the save_research tool to save your findings."}
        ]

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system="You are a research agent. Provide detailed, factual findings.",
            tools=TOOLS,
            messages=messages,
        )

        # Process tool calls (the AGENTIC LOOP pattern)
        for block in response.content:
            if block.type == "tool_use" and block.name == "save_research":
                research_data = block.input
                console.print(f"    [dim]Tool called: save_research with {len(research_data.get('findings', []))} findings[/dim]")

        # Step 2: Analysis
        console.print("  [yellow]🔍 Step 2: Analysis (Claude + tool use)[/yellow]")
        findings_text = "\n".join(research_data.get("findings", ["No findings"]))

        messages = [
            {"role": "user", "content": f"Analyze these research findings and extract 3 key insights. Use save_analysis tool.\n\nFindings:\n{findings_text}"}
        ]

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system="You are an analytical agent. Extract actionable insights.",
            tools=TOOLS,
            messages=messages,
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "save_analysis":
                analysis_data = block.input
                console.print(f"    [dim]Tool called: save_analysis with {len(analysis_data.get('insights', []))} insights[/dim]")

        # Step 3: Report (no tools needed, just generation)
        console.print("  [green]📝 Step 3: Report (Claude direct generation)[/green]")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system="You are a report writer. Write professional, structured reports.",
            messages=[
                {"role": "user", "content": f"""Write a professional report about '{topic}':

Research Findings: {json.dumps(research_data.get('findings', []))}
Analysis Insights: {json.dumps(analysis_data.get('insights', []))}
Recommendation: {analysis_data.get('recommendation', 'N/A')}

Include an executive summary and 3 recommendations."""}
            ],
        )

        report = response.content[0].text

        return {
            "research": research_data,
            "analysis": analysis_data,
            "report": report,
        }

    HAS_FRAMEWORK = True

except ImportError:
    HAS_FRAMEWORK = False

    def run_anthropic_sdk(topic: str) -> dict:
        return {"report": "Anthropic SDK not installed. Run: pip install anthropic"}


# =============================================================================
# Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Framework: Anthropic Claude SDK[/bold]\n\n"
            "Key concepts demonstrated:\n"
            "  • [cyan]client.messages.create(model, tools, messages)[/cyan] — core API\n"
            "  • [cyan]tools=[...][/cyan] — JSON schema tool definitions\n"
            "  • [cyan]Agentic loop[/cyan] — call → tool use → provide result → repeat\n"
            "  • [cyan]block.type == 'tool_use'[/cyan] — detect tool calls in response\n\n"
            "Pipeline: Research (tool use) → Analysis (tool use) → Report (generation)",
            title="📖 Anthropic Claude SDK",
            border_style="yellow",
        )
    )

    if not HAS_FRAMEWORK:
        console.print("[red]⚠ Install first: pip install anthropic[/red]")
        console.print("[yellow]  Also set ANTHROPIC_API_KEY in your .env file[/yellow]")
    else:
        result = run_anthropic_sdk("How AI Agents Are Transforming Software Engineering in 2025")
        console.print(Panel(result["report"], title="📋 Final Report", border_style="green"))

    console.print(
        Panel(
            "[bold]ANTHROPIC CLAUDE SDK — SUMMARY:[/bold]\n"
            "✅ [green]No abstractions[/green] — direct API access, full control\n"
            "✅ [green]Tool use[/green] — structured function calling with JSON schemas\n"
            "✅ [green]Extended thinking[/green] — Claude can 'show its work'\n"
            "✅ [green]Streaming[/green] — real-time response streaming\n"
            "✅ [green]Claude models[/green] — Sonnet, Haiku, Opus\n"
            "❌ [red]No orchestration[/red] — you build multi-agent yourself\n"
            "❌ [red]Claude only[/red] — locked to Anthropic models\n"
            "❌ [red]More boilerplate[/red] — agentic loop is manual",
            title="💡 When to Choose Anthropic SDK",
            border_style="green",
        )
    )
