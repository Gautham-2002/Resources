"""
=============================================================================
FRAMEWORK 2: LangChain — Chains, Tools, and the Largest Ecosystem
=============================================================================
Install: pip install langchain langchain-openai
Docs: https://python.langchain.com

KEY FEATURES:
    - Largest ecosystem (1000+ integrations)
    - Chains for composing LLM calls
    - Tool calling with structured output
    - Memory/chat history management
    - Retrieval-augmented generation (RAG) support
    - Multi-model support

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
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    # =================================================================
    # Setup the LLM
    # =================================================================
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=get_env("OPENAI_API_KEY"),
        temperature=0.7,
    )

    parser = StrOutputParser()

    # =================================================================
    # Define the chain steps as prompts
    # =================================================================
    research_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a research agent. Provide concise, factual findings."),
        ("human", "Research the topic: '{topic}'. List 5 key findings."),
    ])

    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an analytical agent. Extract actionable insights."),
        ("human", "Analyze these research findings and extract 3 key insights:\n\n{research}"),
    ])

    report_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a report writer. Write structured, professional reports."),
        ("human", """Write a concise report about '{topic}' using:

Research: {research}
Analysis: {analysis}

Include an executive summary and recommendations."""),
    ])

    # =================================================================
    # Build the chain using LCEL (LangChain Expression Language)
    # =================================================================
    def run_langchain(topic: str) -> dict:
        """
        Run research pipeline using LangChain.

        KEY CONCEPT: LCEL (LangChain Expression Language)
        Uses the | (pipe) operator to chain steps:
            prompt | llm | parser

        This is LangChain's signature pattern for composing workflows.
        """
        # Step 1: Research
        console.print("  [blue]🔬 Step 1: Research (LangChain chain)[/blue]")
        research_chain = research_prompt | llm | parser
        research = research_chain.invoke({"topic": topic})

        # Step 2: Analysis
        console.print("  [yellow]🔍 Step 2: Analysis (LangChain chain)[/yellow]")
        analysis_chain = analysis_prompt | llm | parser
        analysis = analysis_chain.invoke({"research": research})

        # Step 3: Report
        console.print("  [green]📝 Step 3: Report (LangChain chain)[/green]")
        report_chain = report_prompt | llm | parser
        report = report_chain.invoke({
            "topic": topic,
            "research": research,
            "analysis": analysis,
        })

        return {"research": research, "analysis": analysis, "report": report}

    HAS_FRAMEWORK = True

except ImportError:
    HAS_FRAMEWORK = False

    def run_langchain(topic: str) -> dict:
        return {"report": "LangChain not installed. Run: pip install langchain langchain-openai"}


# =============================================================================
# Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Framework: LangChain[/bold]\n\n"
            "Key concepts demonstrated:\n"
            "  • [cyan]ChatPromptTemplate[/cyan] — structured prompt templates\n"
            "  • [cyan]prompt | llm | parser[/cyan] — LCEL pipe syntax for chaining\n"
            "  • [cyan]ChatOpenAI[/cyan] — LLM wrapper with model config\n"
            "  • [cyan]StrOutputParser[/cyan] — parse LLM output to string\n\n"
            "Pipeline: Research chain → Analysis chain → Report chain",
            title="📖 LangChain",
            border_style="yellow",
        )
    )

    if not HAS_FRAMEWORK:
        console.print("[red]⚠ Install first: pip install langchain langchain-openai[/red]")
    else:
        result = run_langchain("How AI Agents Are Transforming Software Engineering in 2025")
        console.print(Panel(result["report"], title="📋 Final Report", border_style="green"))

    console.print(
        Panel(
            "[bold]LANGCHAIN — SUMMARY:[/bold]\n"
            "✅ [green]Largest ecosystem[/green] — 1000+ integrations and tools\n"
            "✅ [green]LCEL pipe syntax[/green] — elegant chain composition\n"
            "✅ [green]Multi-model[/green] — works with any LLM provider\n"
            "✅ [green]RAG support[/green] — best-in-class retrieval augmentation\n"
            "❌ [red]Complex abstractions[/red] — steep learning curve\n"
            "❌ [red]Frequent API changes[/red] — breaking changes between versions\n"
            "❌ [red]Over-abstracted[/red] — simple tasks feel heavy",
            title="💡 When to Choose LangChain",
            border_style="green",
        )
    )
