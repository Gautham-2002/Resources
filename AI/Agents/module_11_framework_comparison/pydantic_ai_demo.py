"""
=============================================================================
FRAMEWORK 4: Pydantic AI — Type-Safe Agents with Dependency Injection
=============================================================================
Install: pip install pydantic-ai
Docs: https://ai.pydantic.dev

KEY FEATURES:
    - Type-safe outputs using Pydantic models
    - Dependency injection (like FastAPI)
    - Tool registration with @agent.tool decorator
    - Model-agnostic (OpenAI, Anthropic, Gemini, Ollama)
    - Structured output validation

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
    from pydantic import BaseModel
    from pydantic_ai import Agent

    # =================================================================
    # Define structured output types (TYPE-SAFE!)
    # This is Pydantic AI's killer feature — validated LLM outputs
    # =================================================================
    class ResearchFindings(BaseModel):
        """Type-safe research output."""
        topic: str
        findings: list[str]
        sources_quality: str

    class AnalysisResult(BaseModel):
        """Type-safe analysis output."""
        insights: list[str]
        risk_assessment: str
        opportunity: str

    class FinalReport(BaseModel):
        """Type-safe final report."""
        executive_summary: str
        key_findings: list[str]
        recommendations: list[str]
        conclusion: str

    # =================================================================
    # Define agents with typed outputs
    # =================================================================
    research_agent = Agent(
        "openai:gpt-4o-mini",
        result_type=ResearchFindings,
        system_prompt="You are a research agent. Provide structured research findings.",
    )

    analysis_agent = Agent(
        "openai:gpt-4o-mini",
        result_type=AnalysisResult,
        system_prompt="You are an analysis agent. Extract structured insights.",
    )

    report_agent = Agent(
        "openai:gpt-4o-mini",
        result_type=FinalReport,
        system_prompt="You are a report writer. Create structured reports.",
    )

    def run_pydantic_ai(topic: str) -> dict:
        """
        Run research pipeline using Pydantic AI.

        KEY CONCEPT: result_type=PydanticModel
        The LLM output is automatically parsed and VALIDATED
        against the Pydantic model. If it doesn't match, retry!
        """
        # Step 1: Research (returns ResearchFindings)
        console.print("  [blue]🔬 Step 1: Research (typed output: ResearchFindings)[/blue]")
        research_result = research_agent.run_sync(
            f"Research the topic: '{topic}'. Provide 5 key findings."
        )
        research: ResearchFindings = research_result.data
        console.print(f"    [dim]Got {len(research.findings)} typed findings[/dim]")

        # Step 2: Analysis (returns AnalysisResult)
        console.print("  [yellow]🔍 Step 2: Analysis (typed output: AnalysisResult)[/yellow]")
        analysis_result = analysis_agent.run_sync(
            f"Analyze these findings about '{topic}':\n" + "\n".join(research.findings)
        )
        analysis: AnalysisResult = analysis_result.data
        console.print(f"    [dim]Got {len(analysis.insights)} typed insights[/dim]")

        # Step 3: Report (returns FinalReport)
        console.print("  [green]📝 Step 3: Report (typed output: FinalReport)[/green]")
        report_result = report_agent.run_sync(
            f"""Write a report about '{topic}'.
Research: {research.findings}
Analysis: {analysis.insights}
Risk: {analysis.risk_assessment}
Opportunity: {analysis.opportunity}"""
        )
        report: FinalReport = report_result.data

        return {
            "research": research.model_dump(),
            "analysis": analysis.model_dump(),
            "report": report.model_dump(),
        }

    HAS_FRAMEWORK = True

except ImportError:
    HAS_FRAMEWORK = False

    def run_pydantic_ai(topic: str) -> dict:
        return {"report": "Pydantic AI not installed. Run: pip install pydantic-ai"}


# =============================================================================
# Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Framework: Pydantic AI[/bold]\n\n"
            "Key concepts demonstrated:\n"
            "  • [cyan]result_type=BaseModel[/cyan] — LLM output is type-validated\n"
            "  • [cyan]Agent('model', result_type)[/cyan] — agent definition\n"
            "  • [cyan]agent.run_sync(prompt)[/cyan] — synchronous execution\n"
            "  • [cyan]result.data[/cyan] — typed, validated output\n\n"
            "Pipeline: Research → Analyze → Report (all with typed outputs)",
            title="📖 Pydantic AI",
            border_style="yellow",
        )
    )

    if not HAS_FRAMEWORK:
        console.print("[red]⚠ Install first: pip install pydantic-ai[/red]")
    else:
        result = run_pydantic_ai("How AI Agents Are Transforming Software Engineering in 2025")

        if isinstance(result.get("report"), dict):
            report = result["report"]
            output = f"""**Executive Summary:** {report.get('executive_summary', 'N/A')}

**Key Findings:**
{chr(10).join('• ' + f for f in report.get('key_findings', []))}

**Recommendations:**
{chr(10).join('• ' + r for r in report.get('recommendations', []))}

**Conclusion:** {report.get('conclusion', 'N/A')}"""
            console.print(Panel(output, title="📋 Final Report (Typed!)", border_style="green"))

    console.print(
        Panel(
            "[bold]PYDANTIC AI — SUMMARY:[/bold]\n"
            "✅ [green]Type-safe outputs[/green] — LLM responses validated by Pydantic\n"
            "✅ [green]Familiar patterns[/green] — feels like FastAPI for LLMs\n"
            "✅ [green]Dependency injection[/green] — clean runtime context management\n"
            "✅ [green]Model-agnostic[/green] — OpenAI, Anthropic, Gemini, Ollama\n"
            "❌ [red]Newer framework[/red] — community is still growing\n"
            "❌ [red]Less orchestration[/red] — no built-in multi-agent support",
            title="💡 When to Choose Pydantic AI",
            border_style="green",
        )
    )
