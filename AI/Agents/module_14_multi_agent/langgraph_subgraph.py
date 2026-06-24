"""
=============================================================================
MODULE 14 — DEMO 4: LangGraph Subgraph Pattern
=============================================================================
CONCEPT:
    Each agent is a COMPILED GRAPH, composed into a parent graph.
    
    The parent graph has FIXED EDGES (workflow), but each node 
    internally runs a FULL AGENT LOOP.
    
    This is the key insight: orchestration and agents are 
    DIFFERENT LAYERS.
    
    - Outer layer = workflow (fixed edges, deterministic)
    - Inner layer = agents (autonomous loops, dynamic)

RUN:
    python module_14_multi_agent/langgraph_subgraph.py
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel

console = Console()

try:
    from langgraph.graph import StateGraph, END
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from typing import TypedDict, Annotated
    import operator
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False


def build_agent_subgraph(name: str, system_prompt: str):
    """
    Build a single agent as a compiled subgraph.
    
    Each subgraph runs its own internal agent loop:
    think → maybe call tool → think again → done.
    
    But from the parent graph's perspective, it's just a node.
    """
    if not HAS_LANGGRAPH:
        return None
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    class AgentState(TypedDict):
        messages: Annotated[list, operator.add]
        output: str
        iterations: int
    
    def think(state: AgentState) -> dict:
        console.print(f"    [dim]{name}: thinking (iteration {state.get('iterations', 0) + 1})...[/dim]")
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            *state.get("messages", []),
        ])
        return {
            "messages": [response],
            "output": response.content,
            "iterations": state.get("iterations", 0) + 1,
        }
    
    def should_continue(state: AgentState) -> str:
        # Simple: run once (in production, this would check for tool calls)
        return "end"
    
    graph = StateGraph(AgentState)
    graph.add_node("think", think)
    graph.set_entry_point("think")
    graph.add_conditional_edges("think", should_continue, {"end": END})
    
    return graph.compile()


def run_subgraph_pattern(task: str):
    """
    Subgraph Pattern: parent graph has FIXED edges (workflow),
    but each node is a full agent subgraph.
    """
    if not HAS_LANGGRAPH:
        console.print("[red]LangGraph not installed. Run: pip install langgraph langchain-openai[/red]")
        return None
    
    # Build agent subgraphs
    researcher_graph = build_agent_subgraph(
        "Researcher",
        "You are a research analyst. Find key information about the topic. Be concise.",
    )
    analyst_graph = build_agent_subgraph(
        "Analyst",
        "You are a data analyst. Extract 3 key insights from research. Be concise.",
    )
    writer_graph = build_agent_subgraph(
        "Writer",
        "You are a writer. Write a brief executive summary. Be concise.",
    )
    
    # Parent graph with FIXED EDGES (this is the workflow layer)
    class ParentState(TypedDict):
        task: str
        research_output: str
        analysis_output: str
        final_output: str
    
    def research_node(state: ParentState) -> dict:
        console.print("\n  [bold cyan]═══ Node 1: Researcher (subgraph) ═══[/bold cyan]")
        result = researcher_graph.invoke({
            "messages": [HumanMessage(content=f"Research: {state['task']}")],
            "output": "",
            "iterations": 0,
        })
        return {"research_output": result["output"]}
    
    def analysis_node(state: ParentState) -> dict:
        console.print("\n  [bold purple]═══ Node 2: Analyst (subgraph) ═══[/bold purple]")
        result = analyst_graph.invoke({
            "messages": [HumanMessage(content=f"Analyze:\n{state['research_output'][:500]}")],
            "output": "",
            "iterations": 0,
        })
        return {"analysis_output": result["output"]}
    
    def writer_node(state: ParentState) -> dict:
        console.print("\n  [bold green]═══ Node 3: Writer (subgraph) ═══[/bold green]")
        result = writer_graph.invoke({
            "messages": [HumanMessage(content=f"Write summary:\n{state['analysis_output'][:500]}")],
            "output": "",
            "iterations": 0,
        })
        return {"final_output": result["output"]}
    
    parent = StateGraph(ParentState)
    parent.add_node("researcher", research_node)
    parent.add_node("analyst", analysis_node)
    parent.add_node("writer", writer_node)
    
    # FIXED edges — this is a workflow!
    parent.set_entry_point("researcher")
    parent.add_edge("researcher", "analyst")  # always
    parent.add_edge("analyst", "writer")      # always
    parent.add_edge("writer", END)            # always
    
    app = parent.compile()
    
    console.print(Panel(
        "[bold]LangGraph — Subgraph Pattern[/bold]\n\n"
        "Parent graph: researcher → analyst → writer (FIXED edges)\n"
        "Each node: internally runs a FULL agent subgraph\n\n"
        "Outer layer = workflow (deterministic)\n"
        "Inner layer = agents (autonomous)",
        border_style="cyan",
    ))
    
    result = app.invoke({
        "task": task,
        "research_output": "",
        "analysis_output": "",
        "final_output": "",
    })
    
    return result.get("final_output", "No output")


if __name__ == "__main__":
    console.print(Panel(
        "[bold]Module 14 — Demo 4: LangGraph Subgraph[/bold]\n\n"
        "Each agent is a compiled graph, composed into a parent graph.\n\n"
        "KEY INSIGHT:\n"
        "- Parent graph has FIXED edges (workflow): R → A → W\n"
        "- Each node internally runs a FULL agent loop\n"
        "- Orchestration and agents are DIFFERENT LAYERS\n\n"
        "Compare with Supervisor pattern:\n"
        "- Supervisor: LLM decides routing (dynamic)\n"
        "- Subgraph: YOUR CODE decides routing (fixed)",
        title="📖 LangGraph Subgraph",
        border_style="yellow",
    ))
    
    result = run_subgraph_pattern("AI agents in 2025")
    
    if result:
        console.print(Panel(str(result)[:500], title="📄 Final Output", border_style="green"))
    
    console.print(Panel(
        "[bold]KEY INSIGHT:[/bold]\n"
        "Orchestration and agents are DIFFERENT LAYERS:\n\n"
        "• [cyan]Outer layer[/cyan] — workflow (fixed edges, deterministic)\n"
        "• [cyan]Inner layer[/cyan] — agents (autonomous loops, dynamic)\n\n"
        "[bold]LangGraph Patterns Summary:[/bold]\n"
        "• [cyan]Supervisor[/cyan] — LLM decides routing (= orchestration)\n"
        "• [cyan]Subgraph[/cyan] — YOUR CODE decides routing (= workflow)\n"
        "• Both compose agents, but the routing is different",
        title="💡 Orchestration ≠ Agency",
        border_style="green",
    ))
