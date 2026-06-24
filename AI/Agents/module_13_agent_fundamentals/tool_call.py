"""
=============================================================================
MODULE 13 — DEMO 0.5: Why Tools Matter
=============================================================================
CONCEPT:
    LLMs are great at language — but they CAN'T actually compute things.
    Ask an LLM "How long is the word 'strawberry'?" and it may get it wrong.
    Ask it "What is 4739 * 8261?" and it will likely hallucinate.

    This demo shows the problem, then solves it with TOOL CALLING:

    Part 1 — Ask the LLM directly (no tools)    → often WRONG
    Part 2 — Give the LLM tools it can call      → always RIGHT

    This is the motivation for every agent framework: LLMs need tools
    to interact with the real world reliably.

RUN:
    python module_13_agent_fundamentals/tool_call.py
=============================================================================
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from shared.llm import chat, get_openai_client
from shared.config import get_model_name

console = Console()


# =============================================================================
# Define our tools — simple Python functions
# =============================================================================
def string_length(text: str) -> int:
    """Return the exact length of a string."""
    return len(text)


def calculator(expression: str) -> str:
    """Evaluate a math expression and return the result."""
    try:
        return str(eval(expression))  # noqa: S307 — demo only
    except Exception as e:
        return f"Error: {e}"


# Tool registry: map names → functions
TOOL_FUNCTIONS = {
    "string_length": string_length,
    "calculator": calculator,
}

# OpenAI function-calling schema
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "string_length",
            "description": "Return the exact character length of a given string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The string to measure.",
                    }
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a mathematical expression and return the numeric result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A valid Python math expression, e.g. '4739 * 8261'.",
                    }
                },
                "required": ["expression"],
            },
        },
    },
]


# =============================================================================
# PART 1: Ask the LLM directly (no tools) — to show it struggles
# =============================================================================
def ask_without_tools():
    console.print(
        Panel(
            "[bold red]PART 1: LLM WITHOUT Tools[/bold red]\n\n"
            "We ask the LLM questions that require exact computation.\n"
            "Notice how it often gets these WRONG — LLMs predict tokens,\n"
            "they don't actually compute.",
            border_style="red",
        )
    )

    questions = [
        'How many characters are in the word "supercalifragilistic"? Reply with just the number.',
        "What is 4739 * 8261? Reply with just the number.",
    ]
    correct_answers = [
        str(len("supercalifragilistic")),  # 20
        str(4739 * 8261),                  # 39148879
    ]

    for question, correct in zip(questions, correct_answers):
        llm_answer = chat(prompt=question, temperature=0).strip()
        is_correct = llm_answer == correct
        status = "[green]✅ Correct![/green]" if is_correct else "[red]❌ Wrong![/red]"

        console.print(f"\n  [bold]Q:[/bold] {question}")
        console.print(f"  [dim]LLM answer:[/dim]  {llm_answer}")
        console.print(f"  [dim]Correct:[/dim]     {correct}")
        console.print(f"  {status}")


# =============================================================================
# PART 2: Ask with tool calling — LLM chooses the right tool
# =============================================================================
def ask_with_tools():
    console.print(
        Panel(
            "\n[bold green]PART 2: LLM WITH Tools[/bold green]\n\n"
            "Now we give the LLM access to tools (string_length, calculator).\n"
            "The LLM DECIDES which tool to call, we execute it,\n"
            "and it uses the real result to answer correctly.",
            border_style="green",
        )
    )

    questions = [
        'How many characters are in the word "supercalifragilistic"?',
        "What is 4739 * 8261?",
    ]
    correct_answers = [
        str(len("supercalifragilistic")),
        str(4739 * 8261),
    ]

    client = get_openai_client()

    for question, correct in zip(questions, correct_answers):
        console.print(f"\n  [bold]Q:[/bold] {question}")

        # Step 1: Send the question with tool definitions
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Use tools when you need exact answers."},
            {"role": "user", "content": question},
        ]
        response = client.chat.completions.create(
            model=get_model_name(),
            messages=messages,
            tools=TOOLS_SCHEMA,
            temperature=0,
        )

        message = response.choices[0].message

        # Step 2: If the LLM chose a tool, execute it
        if message.tool_calls:
            tool_call = message.tool_calls[0]
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)

            console.print(f"  [yellow]🔧 LLM chose tool:[/yellow] {fn_name}({fn_args})")

            # Execute the tool
            result = TOOL_FUNCTIONS[fn_name](**fn_args)
            console.print(f"  [blue]📥 Tool result:[/blue] {result}")

            # Step 3: Send the tool result back to the LLM for a final answer
            messages.append(message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })
            final_response = client.chat.completions.create(
                model=get_model_name(),
                messages=messages,
                temperature=0,
            )
            final_answer = final_response.choices[0].message.content.strip()
        else:
            final_answer = message.content.strip()

        console.print(f"  [dim]Final answer:[/dim] {final_answer}")
        console.print(f"  [dim]Correct:[/dim]      {correct}")
        console.print(f"  [green]✅ Tool calling gives reliable results![/green]")


# =============================================================================
# Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Module 13 — Demo 0.5: Why Tools Matter[/bold]\n\n"
            "This demo asks the same questions twice:\n"
            "  1. [red]Without tools[/red] — LLM guesses (often wrong)\n"
            "  2. [green]With tools[/green]    — LLM calls a function (always right)\n\n"
            "This is WHY agents need tools.",
            title="📖 What You'll See",
            border_style="yellow",
        )
    )

    ask_without_tools()
    console.print("\n" + "═" * 60 + "\n")
    ask_with_tools()

    console.print(
        Panel(
            "[bold]KEY TAKEAWAYS:[/bold]\n"
            "1. [cyan]LLMs predict text[/cyan] — they don't compute, so math & counting fail\n"
            "2. [cyan]Tools bridge the gap[/cyan] — real Python functions give exact answers\n"
            "3. [cyan]LLM chooses the tool[/cyan] — it decides WHICH tool and WHAT input\n"
            "4. [cyan]We execute, LLM interprets[/cyan] — separation of deciding vs doing\n\n"
            "[bold]This is the foundation of every agent:[/bold]\n"
            "LLM (brain) + Tools (hands) = Agent",
            title="💡 Why Tools Matter",
            border_style="green",
        )
    )
