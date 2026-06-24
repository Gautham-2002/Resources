"""
=============================================================================
MODULE 14 — DEMO 3: Multi-Agent with LangGraph (Supervisor Pattern)
=============================================================================
CONCEPT:
    LangGraph is lower-level than CrewAI. You build the graph yourself,
    which means you have full control over whether it's a workflow, 
    an agent, or a multi-agent system.
    
    Supervisor Pattern:
    - A supervisor node runs, reads the task
    - Says "researcher" → researcher runs (its own agent loop)
    - Returns to supervisor → says "coder"
    - And so on until supervisor says "FINISH"
    
    The supervisor's routing IS the orchestration.

RUN:
    python module_14_multi_agent/langgraph_supervisor.py
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
    from typing import TypedDict, Annotated, Literal
    import operator
    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False


def run_supervisor_pattern(task: str):
    """
    LangGraph Supervisor Pattern.
    
    The supervisor runs, reads the task, decides which worker to call.
    Each worker runs (with its own agent loop). Returns to supervisor.
    Supervisor decides next worker or FINISH.
    """
    if not HAS_LANGGRAPH:
        console.print("[red]LangGraph not installed. Run: pip install langgraph langchain-openai[/red]")
        return None
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # -- State Definition --
    class SupervisorState(TypedDict):
        messages: Annotated[list, operator.add]
        next_worker: str
        research_output: str
        analysis_output: str
        final_output: str
    
    # -- Worker Functions (each simulates an agent) --
    def researcher(state: SupervisorState) -> dict:
        console.print("  [cyan]🔬 Researcher agent running...[/cyan]")
        response = llm.invoke([
            SystemMessage(content="You are a research analyst. Find key information about the topic."),
            HumanMessage(content=f"Research this: {state['messages'][-1].content if state['messages'] else 'No task'}"),
        ])
        console.print(f"  [blue]📥 Researcher output: {response.content[:150]}...[/blue]")
        return {
            "messages": [response],
            "research_output": response.content,
        }
    
    def analyst(state: SupervisorState) -> dict:
        console.print("  [purple]📊 Analyst agent running...[/purple]")
        research = state.get("research_output", "No research available")
        response = llm.invoke([
            SystemMessage(content="You are a data analyst. Extract 3 key insights from the research."),
            HumanMessage(content=f"Analyze this research:\n{research[:500]}"),
        ])
        console.print(f"  [blue]📥 Analyst output: {response.content[:150]}...[/blue]")
        return {
            "messages": [response],
            "analysis_output": response.content,
        }
    
    def writer(state: SupervisorState) -> dict:
        console.print("  [green]✍️ Writer agent running...[/green]")
        analysis = state.get("analysis_output", "No analysis available")
        response = llm.invoke([
            SystemMessage(content="You are a content writer. Write a brief executive summary."),
            HumanMessage(content=f"Write a summary based on:\n{analysis[:500]}"),
        ])
        console.print(f"  [blue]📥 Writer output: {response.content[:150]}...[/blue]")
        return {
            "messages": [response],
            "final_output": response.content,
        }
    
    # -- Supervisor: decides which worker to call next --
    workers = ["researcher", "analyst", "writer"]
    
    def supervisor(state: SupervisorState) -> dict:
        console.print("\n  [bold yellow]🎯 Supervisor deciding next worker...[/bold yellow]")
        
        messages_context = "\n".join(
            m.content[:100] for m in state.get("messages", [])[-3:]
        )
        
        response = llm.invoke([
            SystemMessage(content=f"""You are a supervisor managing these workers: {workers}.
Given the conversation so far, decide which worker should act next.
If the task is complete (research done, analysis done, writing done), respond with FINISH.
Respond with ONLY the worker name or FINISH."""),
            HumanMessage(content=f"Task progress:\n{messages_context}\n\nResearch: {'done' if state.get('research_output') else 'not done'}\nAnalysis: {'done' if state.get('analysis_output') else 'not done'}\nWriting: {'done' if state.get('final_output') else 'not done'}"),
        ])
        
        next_worker = response.content.strip().lower()
        console.print(f"  [yellow]Supervisor says: → {next_worker}[/yellow]")
        
        return {"next_worker": next_worker}
    
    # -- Build the graph --
    def route(state: SupervisorState) -> str:
        next_w = state.get("next_worker", "").lower()
        if next_w == "finish" or next_w not in workers:
            return "end"
        return next_w
    
    graph = StateGraph(SupervisorState)
    
    graph.add_node("supervisor", supervisor)
    graph.add_node("researcher", researcher)
    graph.add_node("analyst", analyst)
    graph.add_node("writer", writer)
    
    graph.set_entry_point("supervisor")
    
    graph.add_conditional_edges("supervisor", route, {
        "researcher": "researcher",
        "analyst": "analyst",
        "writer": "writer",
        "end": END,
    })
    
    # Workers always return to supervisor
    for worker in workers:
        graph.add_edge(worker, "supervisor")
    
    app = graph.compile()
    
    console.print(Panel(
        "[bold]LangGraph — Supervisor Pattern[/bold]\n\n"
        "The supervisor runs → decides 'researcher' → researcher runs →\n"
        "returns to supervisor → decides 'analyst' → and so on.\n"
        "The supervisor's routing IS the orchestration.",
        border_style="cyan",
    ))
    
    result = app.invoke({
        "messages": [HumanMessage(content=task)],
        "next_worker": "",
        "research_output": "",
        "analysis_output": "",
        "final_output": "",
    })
    
    return result.get("final_output", "No output")


if __name__ == "__main__":
    console.print(Panel(
        "[bold]Module 14 — Demo 3: LangGraph Supervisor[/bold]\n\n"
        "LangGraph is lower-level than CrewAI.\n"
        "You build the graph yourself.\n\n"
        "Supervisor Pattern:\n"
        "- Supervisor reads the task\n"
        "- Says 'researcher' → researcher runs (own agent loop)\n"
        "- Returns to supervisor → says 'analyst'\n"
        "- Until supervisor says 'FINISH'\n\n"
        "The supervisor's routing IS the orchestration.",
        title="📖 LangGraph Supervisor",
        border_style="yellow",
    ))
    
    result = run_supervisor_pattern("Research AI agents in 2025 and write a brief report")
    
    if result:
        console.print(Panel(str(result)[:500], title="📄 Final Output", border_style="green"))
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]Supervisor node[/cyan] — decides which worker runs next\n"
        "2. [cyan]Workers[/cyan] — each runs its own agent loop\n"
        "3. [cyan]Graph edges[/cyan] — workers return to supervisor after execution\n"
        "4. [cyan]Conditional routing[/cyan] — supervisor output determines next node\n\n"
        "[bold]Compare with CrewAI:[/bold]\n"
        "• CrewAI hierarchical does this automatically with a manager LLM\n"
        "• LangGraph makes you build it explicitly — more control, more code\n"
        "• Both achieve the same thing: LLM-driven orchestration",
        title="💡 LangGraph Supervisor Pattern",
        border_style="green",
    ))
