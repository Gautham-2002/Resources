"""
=============================================================================
MODULE 13 — DEMO 1: The Agent Loop
=============================================================================
CONCEPT:
    An agent = LLM + tools + a control loop where the LLM DECIDES.

    This demo builds a minimal agent from scratch to show what's really
    happening under the hood:

    1. User gives a task
    2. LLM decides: call a tool? or give final answer?
    3. If tool call → execute it, append result, go to step 2
    4. If final answer → return it

    The key insight: the LLM CHOOSES what to do at each step.
    That's what makes it an agent, not a workflow.

RUN:
    python module_13_agent_fundamentals/agent_loop.py
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Define tools the agent can use
# =============================================================================
def search_web(query: str) -> str:
    """Simulated web search tool."""
    # In production, this would call a real search API
    fake_results = {
        "ai agents": "AI agents are LLM-powered systems that autonomously decide actions. Key frameworks: CrewAI, LangGraph, OpenAI Agents SDK.",
        "crewai": "CrewAI is a framework for building multi-agent systems with role-based agents. Uses Process.sequential and Process.hierarchical.",
        "langgraph": "LangGraph is a low-level graph-based framework for building agent workflows. Supports state machines, DAGs, and dynamic graphs.",
    }
    for key, value in fake_results.items():
        if key in query.lower():
            return value
    return f"Search results for '{query}': General information about the topic."


def calculator(expression: str) -> str:
    """Simple calculator tool."""
    try:
        result = eval(expression)  # noqa: S307 — demo only
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


TOOLS = {
    "search_web": {
        "function": search_web,
        "description": "Search the web for information. Input: a search query string.",
    },
    "calculator": {
        "function": calculator,
        "description": "Calculate a math expression. Input: a valid Python math expression.",
    },
}


# =============================================================================
# Step 2: The Agent Loop
# =============================================================================
def run_agent(task: str, max_iterations: int = 5) -> str:
    """
    A minimal agent loop. This is the core pattern behind every agent framework.

    The LLM decides at each step:
    - Call a tool? → execute it, append result, loop back
    - Final answer? → return it
    """

    tool_descriptions = "\n".join(
        f"- {name}: {info['description']}" for name, info in TOOLS.items()
    )

    system_prompt = f"""You are a helpful agent. You have these tools:

{tool_descriptions}

At each step, respond with EXACTLY one of:
1. TOOL_CALL: tool_name | input
2. FINAL_ANSWER: your final response

Always use TOOL_CALL or FINAL_ANSWER prefix. Be concise."""

    history = [f"Task: {task}"]

    console.print(
        Panel(
            f"[bold]Agent Starting[/bold]\n"
            f"Task: {task}\n"
            f"Available tools: {list(TOOLS.keys())}\n"
            f"Max iterations: {max_iterations}",
            border_style="cyan",
        )
    )

    for iteration in range(1, max_iterations + 1):
        console.print(f"\n  [bold cyan]═══ Turn {iteration} ═══[/bold cyan]")

        # LLM decides what to do
        prompt = "\n".join(history)
        response = chat(
            prompt=prompt,
            system=system_prompt,
            max_tokens=200,
        )

        console.print(f"  [dim]LLM output: {response.strip()}[/dim]")

        if response.strip().startswith("FINAL_ANSWER:"):
            answer = response.split("FINAL_ANSWER:")[-1].strip()
            console.print(f"\n  [green]✅ Agent finished in {iteration} turns[/green]")
            console.print(f"  [green]Answer: {answer}[/green]")
            return answer

        elif "TOOL_CALL:" in response:
            # Parse tool call
            tool_part = response.split("TOOL_CALL:")[-1].strip()
            parts = tool_part.split("|", 1)
            tool_name = parts[0].strip()
            tool_input = parts[1].strip() if len(parts) > 1 else ""

            if tool_name in TOOLS:
                console.print(
                    f"  [yellow]🔧 Calling tool: {tool_name}({tool_input})[/yellow]"
                )
                result = TOOLS[tool_name]["function"](tool_input)
                console.print(f"  [blue]📥 Result: {result}[/blue]")

                # Append to history — this is how the agent "remembers"
                history.append(f"You called {tool_name}({tool_input})")
                history.append(f"Tool result: {result}")
            else:
                history.append(f"Error: Unknown tool '{tool_name}'")
                console.print(f"  [red]❌ Unknown tool: {tool_name}[/red]")
        else:
            # LLM didn't follow format — treat as final answer
            console.print(
                "\n  [yellow]⚠ No TOOL_CALL or FINAL_ANSWER prefix, treating as answer[/yellow]"
            )
            return response.strip()

    console.print(f"\n  [red]⛔ Agent hit max iterations ({max_iterations})[/red]")
    return "Agent did not complete within iteration limit."


# =============================================================================
# Step 3: Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Module 13 — Demo 1: The Agent Loop[/bold]\n\n"
            "This demo shows a minimal agent built from scratch.\n"
            "Watch how the LLM DECIDES what to do at each turn:\n"
            "- It chooses which tool to call\n"
            "- It inspects the result\n"
            "- It decides whether to call another tool or stop\n\n"
            "That autonomous decision loop is what makes it an agent.",
            title="📖 What You'll See",
            border_style="yellow",
        )
    )

    result = run_agent("What is CrewAI and how does it compare to LangGraph?")

    console.print(
        Panel(
            "[bold]KEY CONCEPTS:[/bold]\n"
            "1. [cyan]Agent = LLM + Tools + Loop[/cyan] — the LLM decides what to do\n"
            "2. [cyan]History = Context[/cyan] — each tool result is appended to history\n"
            "3. [cyan]Stateless LLM[/cyan] — the LLM only knows what's in the prompt\n"
            "4. [cyan]max_iterations[/cyan] — always set a hard limit\n\n"
            "[bold]Compare with a Workflow:[/bold]\n"
            "In a workflow, YOU would hardcode: search → analyze → respond.\n"
            "Here, the LLM chose to search twice, then answered. That's the difference.",
            title="💡 The Agent Loop",
            border_style="green",
        )
    )
