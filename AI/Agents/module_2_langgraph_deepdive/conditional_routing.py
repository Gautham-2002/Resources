"""
=============================================================================
MODULE 2 — DEMO 2: LangGraph Conditional Routing
=============================================================================
CONCEPT:
    Conditional edges let you ROUTE execution based on the current state.
    Instead of a fixed path (A → B → C), you get dynamic branching:
    
        A → [if technical] → TechnicalExpert
        A → [if creative]  → CreativeWriter
        A → [if general]   → GeneralAssistant
    
    The routing function examines the state and returns the next node name.

WHAT THIS DEMO DOES:
    A customer support router that:
    1. CLASSIFIER node — classifies the user query type
    2. Routes to one of three SPECIALIST nodes based on classification
    3. RESPONDER node — formats the final response

    Graph:
                            ┌─→ technical_expert ─┐
    START → classifier ─────┤─→ billing_agent    ─├─→ responder → END
                            └─→ general_agent    ─┘

RUN:
    python module_2_langgraph_deepdive/conditional_routing.py
=============================================================================
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Define the STATE
# =============================================================================
class SupportState(TypedDict):
    """State for the customer support router."""
    query: str                  # The customer's question
    classification: str         # "technical" | "billing" | "general"
    specialist_response: str    # Response from the specialist
    final_response: str         # Formatted final response
    route_taken: str            # For logging which route was taken


# =============================================================================
# Step 2: Define the NODES
# =============================================================================
def classifier(state: SupportState) -> dict:
    """
    CLASSIFIER NODE: Determines the type of customer query.
    
    This node's output determines which CONDITIONAL EDGE is taken.
    It sets state["classification"] which the routing function reads.
    """
    console.print("\n[bold cyan]🏷️  Classifier Node[/bold cyan] — Analyzing query type...")
    
    result = chat(
        prompt=f"""Classify this customer query into exactly ONE category.
Reply with ONLY the category name, nothing else.

Categories:
- technical (product bugs, how-to questions, API issues)
- billing (payments, invoices, refunds, pricing)
- general (everything else)

Query: "{state['query']}"

Category:""",
        system="You are a query classifier. Respond with exactly one word: technical, billing, or general.",
        max_tokens=10,
        temperature=0,
    )
    
    # Normalize the classification
    classification = result.strip().lower()
    if classification not in ("technical", "billing", "general"):
        classification = "general"
    
    console.print(f"  📋 Classified as: [bold yellow]{classification}[/bold yellow]")
    return {"classification": classification}


def technical_expert(state: SupportState) -> dict:
    """TECHNICAL EXPERT: Handles technical queries."""
    console.print("\n[bold blue]🔧 Technical Expert Node[/bold blue] — Processing...")
    
    result = chat(
        prompt=f"As a technical support expert, help with: {state['query']}",
        system="You are a senior technical support engineer. Provide clear, step-by-step solutions.",
        max_tokens=300,
    )
    
    return {"specialist_response": result, "route_taken": "technical_expert"}


def billing_agent(state: SupportState) -> dict:
    """BILLING AGENT: Handles billing queries."""
    console.print("\n[bold magenta]💰 Billing Agent Node[/bold magenta] — Processing...")
    
    result = chat(
        prompt=f"As a billing specialist, help with: {state['query']}",
        system="You are a billing specialist. Be precise with amounts and policies.",
        max_tokens=300,
    )
    
    return {"specialist_response": result, "route_taken": "billing_agent"}


def general_agent(state: SupportState) -> dict:
    """GENERAL AGENT: Handles everything else."""
    console.print("\n[bold green]💬 General Agent Node[/bold green] — Processing...")
    
    result = chat(
        prompt=f"As a customer service representative, help with: {state['query']}",
        system="You are a friendly customer service representative. Be helpful and empathetic.",
        max_tokens=300,
    )
    
    return {"specialist_response": result, "route_taken": "general_agent"}


def responder(state: SupportState) -> dict:
    """RESPONDER NODE: Formats the final response."""
    console.print("\n[bold yellow]📤 Responder Node[/bold yellow] — Formatting final response...")
    
    result = chat(
        prompt=f"""Format this specialist response into a polished customer reply.
Add a greeting, the solution, and a closing.

Specialist response: {state['specialist_response']}""",
        system="You are a response formatter. Create professional, friendly customer replies.",
        max_tokens=300,
    )
    
    return {"final_response": result}


# =============================================================================
# Step 3: Define the ROUTING FUNCTION
# =============================================================================
def route_by_classification(state: SupportState) -> Literal["technical_expert", "billing_agent", "general_agent"]:
    """
    ROUTING FUNCTION: Determines which node to go to next.
    
    THIS IS THE KEY CONCEPT: This function is called by LangGraph
    at the conditional edge. It looks at the state and returns
    the NAME of the next node to execute.
    
    The return value MUST match one of the node names.
    """
    classification = state.get("classification", "general")
    
    route_map = {
        "technical": "technical_expert",
        "billing": "billing_agent",
        "general": "general_agent",
    }
    
    chosen = route_map.get(classification, "general_agent")
    console.print(f"  🔀 [bold]Routing to:[/bold] {chosen}")
    return chosen


# =============================================================================
# Step 4: Build the GRAPH with CONDITIONAL EDGES
# =============================================================================
def build_support_graph():
    """
    Build the conditional routing graph.
    
    KEY DIFFERENCE from basic_graph.py:
    Instead of add_edge("classifier", "next_node"),
    we use add_conditional_edges("classifier", routing_function)
    
    The routing function dynamically chooses the next node!
    """
    graph = StateGraph(SupportState)
    
    # Add all nodes
    graph.add_node("classifier", classifier)
    graph.add_node("technical_expert", technical_expert)
    graph.add_node("billing_agent", billing_agent)
    graph.add_node("general_agent", general_agent)
    graph.add_node("responder", responder)
    
    # START → classifier (always)
    graph.add_edge(START, "classifier")
    
    # classifier → conditional routing based on classification
    # THIS IS WHERE THE MAGIC HAPPENS!
    graph.add_conditional_edges(
        "classifier",               # Source node
        route_by_classification,     # Routing function
        {
            # Mapping: routing_function_return → node_name
            "technical_expert": "technical_expert",
            "billing_agent": "billing_agent",
            "general_agent": "general_agent",
        },
    )
    
    # All specialists → responder
    graph.add_edge("technical_expert", "responder")
    graph.add_edge("billing_agent", "responder")
    graph.add_edge("general_agent", "responder")
    
    # responder → END
    graph.add_edge("responder", END)
    
    return graph.compile()


# =============================================================================
# Step 5: Run the demo with multiple queries
# =============================================================================
if __name__ == "__main__":
    console.print(Panel(
        "[bold]LangGraph Conditional Routing Demo[/bold]\n\n"
        "This demo shows CONDITIONAL EDGES in LangGraph.\n"
        "A classifier node determines query type, then ROUTES to a specialist.\n\n"
        "                    ┌─→ technical_expert ─┐\n"
        "START → classifier ─┤─→ billing_agent    ─├─→ responder → END\n"
        "                    └─→ general_agent    ─┘",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    workflow = build_support_graph()
    
    # Test queries — each should route differently!
    test_queries = [
        "My API keeps returning 503 errors when I make batch requests. How do I fix this?",
        "I was charged twice for my subscription last month. Can I get a refund?",
        "What are your business hours and do you have an office in London?",
    ]
    
    results = []
    for query in test_queries:
        console.print(Panel(f"[bold]Query:[/bold] {query}", title="🎯 New Query", border_style="blue"))
        
        result = workflow.invoke({
            "query": query,
            "classification": "",
            "specialist_response": "",
            "final_response": "",
            "route_taken": "",
        })
        
        results.append(result)
        console.print(Panel(
            f"[bold]Route:[/bold] {result['route_taken']}\n\n{result['final_response']}",
            title="✅ Response",
            border_style="green",
        ))
        console.print("─" * 60)
    
    # Summary table
    table = Table(title="Routing Summary")
    table.add_column("Query", style="white", width=40)
    table.add_column("Classification", style="yellow")
    table.add_column("Route Taken", style="cyan")
    
    for r in results:
        table.add_row(r["query"][:40] + "...", r["classification"], r["route_taken"])
    
    console.print(table)
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]add_conditional_edges(node, func, mapping)[/cyan] — Dynamic routing\n"
        "2. The routing function examines STATE to decide the next node\n"
        "3. Return value must match a node name in the mapping\n"
        "4. Multiple paths CONVERGE back to a common node (responder)\n"
        "5. Type hints (Literal[...]) help catch routing errors early",
        title="💡 Conditional Routing in LangGraph",
        border_style="green",
    ))
