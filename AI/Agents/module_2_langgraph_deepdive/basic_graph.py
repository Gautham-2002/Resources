"""
=============================================================================
MODULE 2 — DEMO 1: LangGraph Basic Graph
=============================================================================
CONCEPT:
    LangGraph builds agent workflows as GRAPHS with:
    - STATE: A TypedDict that holds all shared data
    - NODES: Functions that read/modify the state
    - EDGES: Connections defining execution order

    Think of it as: a PIPELINE where each step can read and modify
    a shared whiteboard (the state).

WHAT THIS DEMO DOES:
    A content creation pipeline:
    1. RESEARCHER node — gathers information on a topic
    2. ANALYZER node — extracts key insights
    3. WRITER node — produces a polished article

    All three share a STATE with: topic, research, analysis, article

RUN:
    python module_2_langgraph_deepdive/basic_graph.py
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from rich.console import Console
from rich.panel import Panel
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Define the STATE
# =============================================================================
class ContentState(TypedDict):
    """
    The STATE is a TypedDict — a dictionary with typed fields.

    Every node in the graph can READ from and WRITE to this state.
    Think of it as a shared whiteboard that flows through the pipeline.

    KEY INSIGHT: The state is the ONLY way nodes communicate.
    Node A doesn't call Node B directly — it writes to state,
    and Node B reads from state.
    """

    topic: str  # Input: what to write about
    research: str  # Output of researcher node
    analysis: str  # Output of analyzer node
    article: str  # Output of writer node


# =============================================================================
# Step 2: Define the NODES (each is just a function)
# =============================================================================
def researcher(state: ContentState) -> dict:
    """
    RESEARCHER NODE: Gathers information on the topic.

    IMPORTANT PATTERN:
    - Reads: state["topic"]
    - Writes: {"research": ...}

    A node function takes the full state as input
    and returns a PARTIAL dict with only the fields it wants to update.
    """
    console.print(
        "\n[bold cyan]📚 Researcher Node[/bold cyan] — Gathering information..."
    )

    result = chat(
        prompt=f"Research the topic: '{state['topic']}'. Provide 4-5 key facts and findings.",
        system="You are a research agent. Provide concise, factual information.",
        max_tokens=300,
    )

    console.print(f"  [dim]Found research: {result[:100]}...[/dim]")
    return {"research": result}  # Only update the 'research' field


def analyzer(state: ContentState) -> dict:
    """
    ANALYZER NODE: Extracts insights from the research.

    Reads: state["research"] (written by researcher)
    Writes: {"analysis": ...}
    """
    console.print(
        "\n[bold yellow]🔍 Analyzer Node[/bold yellow] — Extracting insights..."
    )

    result = chat(
        prompt=f"Analyze this research and extract 3 key insights:\n{state['research']}",
        system="You are an analytical agent. Extract actionable insights.",
        max_tokens=300,
    )

    console.print(f"  [dim]Analysis: {result[:100]}...[/dim]")
    return {"analysis": result}


def writer(state: ContentState) -> dict:
    """
    WRITER NODE: Produces the final article.

    Reads: state["topic"], state["research"], state["analysis"]
    Writes: {"article": ...}
    """
    console.print("\n[bold green]✍️  Writer Node[/bold green] — Creating article...")

    result = chat(
        prompt=f"""Write a short article about '{state["topic"]}' using this research and analysis:

Research: {state["research"]}

Key Insights: {state["analysis"]}

Write a compelling, concise article (3-4 paragraphs).""",
        system="You are a skilled content writer. Write engaging, informative articles.",
        max_tokens=500,
    )

    console.print(f"  [dim]Article: {result[:100]}...[/dim]")
    return {"article": result}


# =============================================================================
# Step 3: Build the GRAPH
# =============================================================================
def build_content_graph():
    """
    Build the LangGraph workflow.

    This is where the magic happens:
    1. Create a StateGraph with our state type
    2. Add nodes (functions)
    3. Add edges (connections)
    4. Compile into a runnable graph

    Graph structure:
        START → researcher → analyzer → writer → END
    """
    # Create the graph with our state schema
    graph = StateGraph(ContentState)

    # Add nodes — each is a function
    graph.add_node("researcher", researcher)
    graph.add_node("analyzer", analyzer)
    graph.add_node("writer", writer)

    # Add edges — define the flow
    graph.add_edge(START, "researcher")  # START → researcher
    graph.add_edge("researcher", "analyzer")  # researcher → analyzer
    graph.add_edge("analyzer", "writer")  # analyzer → writer
    graph.add_edge("writer", END)  # writer → END

    # Compile — turns the graph definition into a runnable object
    return graph.compile()


# =============================================================================
# Step 4: Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]LangGraph Basic Graph Demo[/bold]\n\n"
            "This demo shows the fundamentals of LangGraph:\n"
            "• STATE — shared data (TypedDict) flowing through the graph\n"
            "• NODES — functions that read/write state\n"
            "• EDGES — connections defining execution order\n\n"
            "Graph: START → Researcher → Analyzer → Writer → END",
            title="📖 What You'll See",
            border_style="yellow",
        )
    )

    # Build the graph
    workflow = build_content_graph()

    # Run with initial state
    console.print(
        Panel(
            "Topic: 'The Impact of AI Agents on Software Development'",
            title="🚀 Starting Workflow",
            border_style="blue",
        )
    )

    result = workflow.invoke(
        {
            "topic": "The Impact of AI Agents on Software Development",
            "research": "",
            "analysis": "",
            "article": "",
        }
    )

    # Display results
    console.print(
        Panel(result["article"], title="📄 Final Article", border_style="green")
    )

    console.print(
        Panel(
            "[bold]KEY CONCEPTS:[/bold]\n"
            "1. [cyan]StateGraph(TypedDict)[/cyan] — Define your state schema\n"
            "2. [cyan]graph.add_node(name, func)[/cyan] — Register node functions\n"
            "3. [cyan]graph.add_edge(from, to)[/cyan] — Connect nodes\n"
            "4. [cyan]graph.compile()[/cyan] — Create runnable workflow\n"
            "5. [cyan]workflow.invoke(state)[/cyan] — Execute with initial state\n\n"
            "Each node returns a PARTIAL state update — only the fields it changes.",
            title="💡 LangGraph Fundamentals",
            border_style="green",
        )
    )
