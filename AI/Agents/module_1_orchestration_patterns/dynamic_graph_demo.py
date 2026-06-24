"""
=============================================================================
MODULE 1 — DEMO 3: Dynamic Graph Pattern
=============================================================================
CONCEPT:
    Unlike State Machines (fixed states) or DAGs (fixed dependencies),
    a Dynamic Graph is built AT RUNTIME by the LLM itself.

    The agent decides at each step what to do next — search, analyze,
    ask a follow-up question, or conclude. The graph SHAPE is unpredictable.

    Think of it as: the LLM is not just executing the workflow,
    it's DESIGNING the workflow as it goes.

WHAT THIS DEMO DOES:
    A research agent that:
    1. Takes a research question
    2. At each step, the LLM decides: SEARCH, ANALYZE, SYNTHESIZE, or CONCLUDE
    3. The agent dynamically builds its own workflow graph
    4. The execution path is different every time!

RUN:
    python module_1_orchestration_patterns/dynamic_graph_demo.py
=============================================================================
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Define possible actions the agent can take
# =============================================================================
ACTIONS = {
    "SEARCH": "Search for more information on a subtopic",
    "ANALYZE": "Analyze and reason about gathered information",
    "SYNTHESIZE": "Combine multiple findings into a coherent view",
    "CONCLUDE": "Generate the final answer and stop",
}


def decide_next_action(question: str, history: list[dict]) -> dict:
    """
    Ask the LLM to decide what to do next.

    THIS IS THE KEY DIFFERENCE: The LLM CHOOSES the next node in the graph.
    In a state machine, transitions are pre-coded.
    In a DAG, dependencies are pre-defined.
    Here, the LLM decides dynamically.
    """
    history_text = (
        "\n".join(
            [
                f"Step {h['step']}: [{h['action']}] {h['result'][:100]}..."
                for h in history
            ]
        )
        if history
        else "No steps taken yet."
    )

    response = chat(
        prompt=f"""Research Question: {question}

        Work done so far:
        {history_text}
        
        Based on what you've done so far, what should you do NEXT?
        You MUST respond with EXACTLY this JSON format:
        {{"action": "SEARCH|ANALYZE|SYNTHESIZE|CONCLUDE", "reasoning": "why this action", "details": "specific focus for this action"}}
        
        Rules:
        - Use SEARCH if you need more information on a subtopic
        - Use ANALYZE if you have enough data to reason about
        - Use SYNTHESIZE if you have multiple analyses to combine
        - Use CONCLUDE if you have enough to answer the question (you MUST conclude within 5 steps)
        - You have done {len(history)} steps so far. Max is 5.
        """,
        system="You are a research planning agent. You decide the next step in a dynamic research workflow. Always respond with valid JSON only.",
        max_tokens=200,
    )

    try:
        # Try to parse the JSON from the response
        # Handle case where LLM wraps JSON in markdown code blocks
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        return {
            "action": "CONCLUDE",
            "reasoning": "Could not parse response",
            "details": response,
        }


def execute_action(
    action: str, details: str, question: str, history: list[dict]
) -> str:
    """Execute the chosen action using the LLM."""

    history_text = (
        "\n".join(
            [f"Step {h['step']}: [{h['action']}] {h['result'][:150]}" for h in history]
        )
        if history
        else "No previous work."
    )

    prompts = {
        "SEARCH": f"Research this subtopic for the question '{question}': {details}\n\nProvide 3-4 key findings. Be concise and factual.",
        "ANALYZE": f"Analyze the following research findings about '{question}':\n{history_text}\n\nFocus on: {details}\nProvide analytical insights.",
        "SYNTHESIZE": f"Synthesize all findings about '{question}':\n{history_text}\n\nCombine into a coherent narrative. Focus on: {details}",
        "CONCLUDE": f"Based on all your research about '{question}':\n{history_text}\n\nProvide a final, comprehensive answer.",
    }

    systems = {
        "SEARCH": "You are a research agent. Find relevant information on the given subtopic.",
        "ANALYZE": "You are an analytical agent. Provide deep analysis of the given information.",
        "SYNTHESIZE": "You are a synthesis agent. Combine multiple pieces of information coherently.",
        "CONCLUDE": "You are a report agent. Provide a clear, well-structured final answer.",
    }

    return chat(
        prompt=prompts.get(action, prompts["CONCLUDE"]),
        system=systems.get(action, systems["CONCLUDE"]),
        max_tokens=300,
    )


# =============================================================================
# Step 2: The Dynamic Graph executor
# =============================================================================
class DynamicGraphAgent:
    """
    An agent that builds its execution graph dynamically.

    At each step:
    1. The LLM looks at what's been done so far
    2. Decides what action to take next (SEARCH/ANALYZE/SYNTHESIZE/CONCLUDE)
    3. Executes that action
    4. Repeats until CONCLUDE or max steps reached

    The result is a DIFFERENT execution graph every time, even for the same question!
    """

    def __init__(self, question: str, max_steps: int = 5):
        self.question = question
        self.max_steps = max_steps
        self.history: list[dict] = []
        self.graph_edges: list[tuple[str, str]] = []  # Track the dynamic graph

    def run(self) -> dict:
        """Execute the dynamic research workflow."""
        console.print(
            Panel(
                f"[bold]Question:[/bold] {self.question}",
                title="🌐 Dynamic Graph Research Agent",
                border_style="blue",
            )
        )

        final_answer = ""

        for step in range(1, self.max_steps + 1):
            console.print(
                f"\n[bold yellow]─── Step {step}/{self.max_steps} ───[/bold yellow]"
            )

            # THE KEY MOMENT: LLM decides what to do next
            decision = decide_next_action(self.question, self.history)
            action = decision.get("action", "CONCLUDE")
            reasoning = decision.get("reasoning", "")
            details = decision.get("details", "")

            # Track the graph edge
            prev_action = self.history[-1]["action"] if self.history else "START"
            self.graph_edges.append((f"{prev_action}_{step - 1}", f"{action}_{step}"))

            console.print(f"  🧠 [bold]Decision:[/bold] {action}")
            console.print(f"  💭 [dim]Reasoning:[/dim] {reasoning}")
            console.print(f"  🎯 [dim]Focus:[/dim] {details}")

            # Execute the chosen action
            result = execute_action(action, details, self.question, self.history)

            self.history.append(
                {
                    "step": step,
                    "action": action,
                    "reasoning": reasoning,
                    "details": details,
                    "result": result,
                }
            )

            console.print(f"  📝 [green]Result:[/green] {result[:150]}...")

            if action == "CONCLUDE":
                final_answer = result
                break

        # If we hit max steps without concluding, force a conclusion
        if not final_answer:
            console.print(
                "\n[yellow]⚠ Max steps reached, forcing conclusion...[/yellow]"
            )
            final_answer = execute_action("CONCLUDE", "", self.question, self.history)

        return {
            "question": self.question,
            "answer": final_answer,
            "steps_taken": len(self.history),
            "execution_path": [h["action"] for h in self.history],
            "graph_edges": self.graph_edges,
            "history": self.history,
        }


# =============================================================================
# Step 3: Visualize the dynamic execution path
# =============================================================================
def display_results(result: dict):
    """Show the dynamic graph execution results."""

    # Show the execution path — this is DIFFERENT every time!
    path_str = " → ".join(["START"] + [f"{a}" for a in result["execution_path"]])
    console.print(
        Panel(
            f"[bold]Dynamic Path:[/bold] {path_str}\n"
            f"[bold]Steps:[/bold] {result['steps_taken']}",
            title="🗺️ Execution Graph (Built at Runtime!)",
            border_style="magenta",
        )
    )

    # Show the final answer
    console.print(
        Panel(
            result["answer"],
            title="📋 Final Answer",
            border_style="green",
        )
    )

    # Show detailed step table
    table = Table(title="Dynamic Execution History")
    table.add_column("Step", style="cyan", width=5)
    table.add_column("Action", style="yellow", width=12)
    table.add_column("Reasoning", style="dim", width=30)
    table.add_column("Result Preview", style="white", width=50)

    for h in result["history"]:
        table.add_row(
            str(h["step"]),
            h["action"],
            h["reasoning"][:30],
            h["result"][:50] + "...",
        )

    console.print(table)


# =============================================================================
# Step 4: Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Dynamic Graph Pattern Demo[/bold]\n\n"
            "This demo shows a research agent that BUILDS ITS OWN WORKFLOW at runtime.\n"
            "The LLM decides at each step: SEARCH, ANALYZE, SYNTHESIZE, or CONCLUDE.\n"
            "Run it twice — you'll see DIFFERENT execution paths each time!",
            title="📖 What You'll See",
            border_style="yellow",
        )
    )

    # Run the research agent
    agent = DynamicGraphAgent(
        question="What are the key differences between microservices and monolithic architectures, and when should you choose each?",
        max_steps=5,
    )
    result = agent.run()
    display_results(result)

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "✅ Maximum flexibility — the LLM designs the workflow at runtime\n"
            "✅ Can handle novel, unpredictable tasks\n"
            "✅ Each execution can take a different path\n"
            "❌ Hard to predict cost/time (variable number of steps)\n"
            "❌ Harder to debug and audit\n"
            "❌ Risk of infinite loops without guardrails (max_steps)",
            title="💡 When to Use Dynamic Graphs",
            border_style="green",
        )
    )
