"""
=============================================================================
PATTERN 5: Evaluator-Optimizer — Generate → Evaluate → Refine Loop
=============================================================================
CONCEPT:
    One agent GENERATES output, another agent EVALUATES it against
    criteria, and if it doesn't pass, the generator REFINES it.
    This loops until the evaluator approves.

    Generator → Evaluator → Pass? → YES → Done
                    ↓ NO
                Generator (with feedback) → Evaluator → ...

WHEN TO USE:
    ✅ Output quality MUST meet specific criteria
    ✅ First-pass LLM output is often not good enough
    ✅ You can define clear evaluation criteria
    ❌ Speed is critical (each loop adds latency)
    ❌ Good enough is good enough (just use Prompt Chaining)

RUN:
    python module_10_workflow_patterns/evaluator_optimizer.py
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
# Step 1: Generator Agent
# =============================================================================
def generator(topic: str, feedback: str | None = None) -> str:
    """
    Generates content. On first call, creates from scratch.
    On subsequent calls, REFINES based on evaluator feedback.
    """
    if feedback:
        prompt = f"""Improve this content about '{topic}' based on this feedback:

FEEDBACK: {feedback}

Write an improved version that addresses ALL the feedback points."""
        console.print("  [yellow]🔄 Refining based on feedback...[/yellow]")
    else:
        prompt = f"Write a concise, high-quality technical summary about: {topic}"
        console.print("  [blue]✍️  Generating initial draft...[/blue]")

    return chat(
        prompt=prompt,
        system="You are a technical writer. Write clear, accurate, well-structured content.",
        max_tokens=400,
    )


# =============================================================================
# Step 2: Evaluator Agent
# =============================================================================
EVALUATION_CRITERIA = [
    "Accuracy: Are all facts correct and claims supported?",
    "Completeness: Does it cover all important aspects?",
    "Clarity: Is the writing clear and well-organized?",
    "Conciseness: Is it free of unnecessary verbosity?",
]


def evaluator(content: str, topic: str) -> dict:
    """
    Evaluates content against predefined criteria.
    Returns a structured evaluation with pass/fail and feedback.
    """
    criteria_text = "\n".join([f"  - {c}" for c in EVALUATION_CRITERIA])

    result = chat(
        prompt=f"""Evaluate this content about '{topic}' against these criteria:

{criteria_text}

Content to evaluate:
{content}

Reply in this JSON format:
{{
    "overall_score": 8,
    "passed": true,
    "criteria_scores": {{"Accuracy": 9, "Completeness": 7, "Clarity": 8, "Conciseness": 8}},
    "feedback": "Specific improvement suggestions if not passed, or 'Approved' if passed"
}}

Score each criterion 1-10. Pass threshold is ALL criteria >= 7. Be strict but fair.""",
        system="You are a quality assurance evaluator. Score content objectively and provide actionable feedback. Reply with valid JSON only.",
        max_tokens=300,
        temperature=0,
    )

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        evaluation = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        evaluation = {
            "overall_score": 7,
            "passed": True,
            "criteria_scores": {},
            "feedback": "Approved (fallback)",
        }

    return evaluation


# =============================================================================
# Step 3: The Evaluator-Optimizer Loop
# =============================================================================
def run_evaluator_optimizer(topic: str, max_iterations: int = 3) -> dict:
    """Run the generate → evaluate → refine loop."""
    iterations = []
    feedback = None

    for i in range(1, max_iterations + 1):
        console.print(f"\n[bold yellow]═══ Iteration {i}/{max_iterations} ═══[/bold yellow]")

        # Generate (or refine)
        content = generator(topic, feedback)

        # Evaluate
        console.print("  [magenta]📊 Evaluating...[/magenta]")
        evaluation = evaluator(content, topic)

        score = evaluation.get("overall_score", 0)
        passed = evaluation.get("passed", False)
        feedback_text = evaluation.get("feedback", "No feedback")

        iterations.append({
            "iteration": i,
            "content": content,
            "score": score,
            "passed": passed,
            "feedback": feedback_text,
            "criteria": evaluation.get("criteria_scores", {}),
        })

        console.print(f"  [bold]Score: {score}/10[/bold] — {'[green]PASSED ✅[/green]' if passed else '[red]NEEDS IMPROVEMENT ❌[/red]'}")

        if passed:
            console.print("  [green]Quality threshold met! Stopping loop.[/green]")
            break
        else:
            console.print(f"  [dim]Feedback: {feedback_text[:100]}...[/dim]")
            feedback = feedback_text

    return {
        "topic": topic,
        "iterations": iterations,
        "final_content": iterations[-1]["content"],
        "final_score": iterations[-1]["score"],
        "total_iterations": len(iterations),
    }


if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Pattern: Evaluator-Optimizer[/bold]\n\n"
            "Generator creates content → Evaluator scores it.\n"
            "If it fails, the Generator refines using the feedback.\n"
            "Loops until quality threshold is met (or max iterations).",
            title="📖 Evaluator-Optimizer",
            border_style="yellow",
        )
    )

    result = run_evaluator_optimizer("Microservices Architecture: Benefits and Trade-offs")

    console.print(
        Panel(result["final_content"], title="📋 Final Content", border_style="green")
    )

    # Show iteration history
    table = Table(title="Iteration History")
    table.add_column("Iter", style="cyan", width=5)
    table.add_column("Score", style="yellow", width=7)
    table.add_column("Status", style="white", width=10)
    table.add_column("Feedback", style="dim", width=50)

    for it in result["iterations"]:
        status = "[green]PASS[/green]" if it["passed"] else "[red]FAIL[/red]"
        table.add_row(str(it["iteration"]), str(it["score"]), status, it["feedback"][:50] + "...")

    console.print(table)

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "1. [cyan]Separate concerns[/cyan] — generator and evaluator are different agents\n"
            "2. [cyan]Feedback loop[/cyan] — evaluator feedback drives improvement\n"
            "3. [cyan]Quality gates[/cyan] — define clear pass/fail criteria\n"
            "4. [cyan]Max iterations[/cyan] — always have an exit condition\n\n"
            "[bold]REAL-WORLD USES:[/bold]\n"
            "• Code review + fix loops\n"
            "• Content quality assurance\n"
            "• Data validation pipelines",
            title="💡 When to Use Evaluator-Optimizer",
            border_style="green",
        )
    )
