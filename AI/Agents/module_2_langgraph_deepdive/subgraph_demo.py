"""
=============================================================================
MODULE 2 — DEMO 3: LangGraph Subgraphs
=============================================================================
CONCEPT:
    Subgraphs let you COMPOSE complex workflows from smaller, reusable graphs.
    
    Think of it like functions in programming:
    - A subgraph encapsulates a complex workflow behind a simple interface
    - The parent graph treats the subgraph as a single node
    - Each subgraph has its OWN internal state
    
    This is essential for building large, modular agent systems.

WHAT THIS DEMO DOES:
    A blog post creation system with TWO subgraphs:
    
    MAIN GRAPH:
        START → planner → [research_subgraph] → [writing_subgraph] → END
    
    RESEARCH SUBGRAPH (internal):
        search → evaluate → compile_findings
    
    WRITING SUBGRAPH (internal):
        draft → review → polish

RUN:
    python module_2_langgraph_deepdive/subgraph_demo.py
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
# Step 1: Define STATES for each graph level
# =============================================================================
class MainState(TypedDict):
    """State for the MAIN (parent) graph."""
    topic: str
    plan: str
    research_findings: str
    final_article: str


class ResearchState(TypedDict):
    """State for the RESEARCH subgraph — has its own internal state."""
    topic: str
    search_results: str
    evaluation: str
    compiled_findings: str


class WritingState(TypedDict):
    """State for the WRITING subgraph — separate internal state."""
    topic: str
    research_findings: str
    draft: str
    review_feedback: str
    polished_article: str


# =============================================================================
# Step 2: RESEARCH SUBGRAPH nodes
# =============================================================================
def search_node(state: ResearchState) -> dict:
    """Search for information on the topic."""
    console.print("    [bold blue]🔍 Search[/bold blue] — Finding information...")
    result = chat(
        prompt=f"Search for key information about: {state['topic']}. List 4-5 important findings.",
        system="You are a research agent. Provide factual, sourced information.",
        max_tokens=300,
    )
    return {"search_results": result}


def evaluate_node(state: ResearchState) -> dict:
    """Evaluate the quality and relevance of search results."""
    console.print("    [bold blue]⚖️  Evaluate[/bold blue] — Assessing quality...")
    result = chat(
        prompt=f"Evaluate these search results for quality and relevance to '{state['topic']}':\n{state['search_results']}\n\nRate each finding and note which are most useful.",
        system="You are a research quality evaluator. Be critical and analytical.",
        max_tokens=200,
    )
    return {"evaluation": result}


def compile_findings_node(state: ResearchState) -> dict:
    """Compile evaluated findings into a research brief."""
    console.print("    [bold blue]📋 Compile[/bold blue] — Creating research brief...")
    result = chat(
        prompt=f"Compile the best findings into a concise research brief:\n\nFindings: {state['search_results']}\n\nEvaluation: {state['evaluation']}",
        system="You are a research compiler. Create concise, well-organized research briefs.",
        max_tokens=300,
    )
    return {"compiled_findings": result}


# =============================================================================
# Step 3: WRITING SUBGRAPH nodes
# =============================================================================
def draft_node(state: WritingState) -> dict:
    """Write the first draft."""
    console.print("    [bold magenta]✏️  Draft[/bold magenta] — Writing first draft...")
    result = chat(
        prompt=f"Write a first draft article about '{state['topic']}' using this research:\n{state['research_findings']}",
        system="You are a content writer. Write engaging first drafts.",
        max_tokens=400,
    )
    return {"draft": result}


def review_node(state: WritingState) -> dict:
    """Review the draft and provide feedback."""
    console.print("    [bold magenta]📝 Review[/bold magenta] — Reviewing draft...")
    result = chat(
        prompt=f"Review this draft article and provide specific improvement suggestions:\n{state['draft']}",
        system="You are an editor. Provide constructive, specific feedback.",
        max_tokens=200,
    )
    return {"review_feedback": result}


def polish_node(state: WritingState) -> dict:
    """Polish the draft based on review feedback."""
    console.print("    [bold magenta]✨ Polish[/bold magenta] — Applying improvements...")
    result = chat(
        prompt=f"Polish this article based on the review feedback:\n\nDraft:\n{state['draft']}\n\nFeedback:\n{state['review_feedback']}\n\nWrite the final polished version.",
        system="You are a senior editor. Create polished, publication-ready content.",
        max_tokens=500,
    )
    return {"polished_article": result}


# =============================================================================
# Step 4: Build the SUBGRAPHS
# =============================================================================
def build_research_subgraph():
    """
    Build the research subgraph.
    
    search → evaluate → compile_findings
    
    This is a COMPLETE graph that can run independently.
    """
    graph = StateGraph(ResearchState)
    graph.add_node("search", search_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("compile", compile_findings_node)
    
    graph.add_edge(START, "search")
    graph.add_edge("search", "evaluate")
    graph.add_edge("evaluate", "compile")
    graph.add_edge("compile", END)
    
    return graph.compile()


def build_writing_subgraph():
    """
    Build the writing subgraph.
    
    draft → review → polish
    """
    graph = StateGraph(WritingState)
    graph.add_node("draft", draft_node)
    graph.add_node("review", review_node)
    graph.add_node("polish", polish_node)
    
    graph.add_edge(START, "draft")
    graph.add_edge("draft", "review")
    graph.add_edge("review", "polish")
    graph.add_edge("polish", END)
    
    return graph.compile()


# =============================================================================
# Step 5: MAIN GRAPH — integrates subgraphs as nodes
# =============================================================================
# Pre-compile the subgraphs
research_workflow = build_research_subgraph()
writing_workflow = build_writing_subgraph()


def planner_node(state: MainState) -> dict:
    """Plan the article structure."""
    console.print("\n[bold cyan]📐 Planner Node[/bold cyan] — Creating article plan...")
    result = chat(
        prompt=f"Create a brief outline for an article about: {state['topic']}. Include 3-4 main sections.",
        system="You are a content planner. Create clear, logical outlines.",
        max_tokens=200,
    )
    return {"plan": result}


def research_subgraph_node(state: MainState) -> dict:
    """
    SUBGRAPH NODE: Runs the entire research subgraph.
    
    KEY PATTERN: 
    - Extract relevant fields from MainState
    - Create ResearchState for the subgraph
    - Run the subgraph
    - Extract results back into MainState
    
    The parent graph doesn't know about search/evaluate/compile —
    it just sees "research" as a single step.
    """
    console.print(Panel("Running Research Subgraph...", title="📚 Research Subgraph", border_style="blue"))
    
    # Map MainState → ResearchState
    research_input = {
        "topic": state["topic"],
        "search_results": "",
        "evaluation": "",
        "compiled_findings": "",
    }
    
    # Run the subgraph
    research_result = research_workflow.invoke(research_input)
    
    # Map ResearchState → MainState
    return {"research_findings": research_result["compiled_findings"]}


def writing_subgraph_node(state: MainState) -> dict:
    """
    SUBGRAPH NODE: Runs the entire writing subgraph.
    """
    console.print(Panel("Running Writing Subgraph...", title="✍️  Writing Subgraph", border_style="magenta"))
    
    # Map MainState → WritingState
    writing_input = {
        "topic": state["topic"],
        "research_findings": state["research_findings"],
        "draft": "",
        "review_feedback": "",
        "polished_article": "",
    }
    
    # Run the subgraph
    writing_result = writing_workflow.invoke(writing_input)
    
    # Map WritingState → MainState
    return {"final_article": writing_result["polished_article"]}


def build_main_graph():
    """
    Build the MAIN graph that orchestrates everything.
    
    planner → research_subgraph → writing_subgraph → END
    
    Each "subgraph node" internally runs an entire sub-workflow,
    but from the main graph's perspective, it's just a single node.
    """
    graph = StateGraph(MainState)
    
    graph.add_node("planner", planner_node)
    graph.add_node("research", research_subgraph_node)
    graph.add_node("writing", writing_subgraph_node)
    
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "research")
    graph.add_edge("research", "writing")
    graph.add_edge("writing", END)
    
    return graph.compile()


# =============================================================================
# Step 6: Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(Panel(
        "[bold]LangGraph Subgraphs Demo[/bold]\n\n"
        "This demo shows how to COMPOSE complex workflows from subgraphs.\n\n"
        "MAIN GRAPH:  planner → [research_subgraph] → [writing_subgraph] → END\n"
        "  RESEARCH:  search → evaluate → compile\n"
        "  WRITING:   draft → review → polish\n\n"
        "Total: 7 steps, but the main graph only has 3 nodes!",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    workflow = build_main_graph()
    
    result = workflow.invoke({
        "topic": "How AI Agents Are Transforming Developer Productivity",
        "plan": "",
        "research_findings": "",
        "final_article": "",
    })
    
    console.print(Panel(result["final_article"], title="📄 Final Published Article", border_style="green"))
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]Subgraphs[/cyan] encapsulate complex workflows as single nodes\n"
        "2. Each subgraph has its [cyan]OWN state type[/cyan] (ResearchState, WritingState)\n"
        "3. The parent maps its state to/from the subgraph state\n"
        "4. Subgraphs can be [cyan]reused[/cyan] in different parent graphs\n"
        "5. This enables [cyan]modular, maintainable[/cyan] agent architectures\n\n"
        "[bold]ANALOGY:[/bold]\n"
        "Subgraphs are like departments in a company:\n"
        "  CEO (main graph) → Research Dept (subgraph) → Writing Dept (subgraph)\n"
        "  Each department has its own internal process, but the CEO just delegates.",
        title="💡 Subgraphs in LangGraph",
        border_style="green",
    ))
