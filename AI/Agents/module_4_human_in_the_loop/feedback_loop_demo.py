"""
=============================================================================
MODULE 4 — DEMO 2: Feedback Loop Pattern
=============================================================================
CONCEPT:
    A feedback loop is an iterative HITL pattern where:
    1. Agent produces output
    2. Human provides FEEDBACK (not just approve/reject)
    3. Agent IMPROVES the output based on feedback
    4. Repeat until human is satisfied

    This is more collaborative than an approval gate — the human
    actively shapes the agent's output.

WHAT THIS DEMO DOES:
    A content writing agent that:
    1. Writes an article draft
    2. Shows it to the human
    3. Human provides specific feedback
    4. Agent revises based on feedback
    5. Repeats until human says "done"

RUN:
    python module_4_human_in_the_loop/feedback_loop_demo.py
=============================================================================
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from shared.llm import chat

console = Console()


class FeedbackLoopAgent:
    """
    An agent that iteratively improves output based on human feedback.
    
    Unlike the approval gate (approve/reject/edit), this pattern is
    designed for COLLABORATIVE creation where the human provides
    detailed, iterative feedback.
    """
    
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.iterations: list[dict] = []
    
    def generate(self, topic: str, feedback_history: list[dict] = None) -> str:
        """Generate or improve content based on feedback."""
        if not feedback_history:
            prompt = f"Write a short blog post (3-4 paragraphs) about: {topic}"
        else:
            history = "\n\n".join([
                f"--- Iteration {fh['iteration']} ---\n"
                f"Draft:\n{fh['content'][:200]}...\n"
                f"Feedback: {fh['feedback']}"
                for fh in feedback_history[-2:]  # Last 2 iterations for context
            ])
            latest_feedback = feedback_history[-1]["feedback"]
            prompt = f"""Improve the blog post about '{topic}'.

Recent history:
{history}

Latest feedback to address: {latest_feedback}

Write the IMPROVED version. Address ALL the feedback points."""
        
        return chat(
            prompt=prompt,
            system="You are a skilled content writer. Take feedback seriously and make specific improvements.",
            max_tokens=500,
        )
    
    def get_feedback(self, content: str, iteration: int) -> dict:
        """
        THE FEEDBACK POINT: Show content and collect detailed feedback.
        
        Returns: {"action": "continue"|"done", "feedback": str}
        """
        console.print(Panel(
            content,
            title=f"📝 Draft — Iteration {iteration}",
            border_style="cyan",
        ))
        
        console.print(f"\n[bold]Iteration {iteration}/{self.max_iterations}[/bold]")
        console.print("Type [green]'done'[/green] to accept, or provide feedback to improve:\n")
        
        feedback = Prompt.ask("Your feedback")
        
        if feedback.lower().strip() == "done":
            return {"action": "done", "feedback": ""}
        else:
            return {"action": "continue", "feedback": feedback}
    
    def run(self, topic: str):
        """
        Main feedback loop.
        
        Flow: generate → [FEEDBACK] → improve → [FEEDBACK] → ... → done
        
        The key insight: each iteration BUILDS on previous feedback,
        so the output gets progressively better.
        """
        console.print(Panel(
            f"[bold]Topic:[/bold] {topic}",
            title="🔄 Feedback Loop Agent",
            border_style="blue",
        ))
        
        feedback_history = []
        
        for iteration in range(1, self.max_iterations + 1):
            # Generate/improve content
            console.print(f"\n[cyan]{'✏️  Writing initial draft...' if iteration == 1 else '🔄 Revising based on your feedback...'}[/cyan]\n")
            content = self.generate(topic, feedback_history if feedback_history else None)
            
            # Get human feedback
            feedback = self.get_feedback(content, iteration)
            
            feedback_history.append({
                "iteration": iteration,
                "content": content,
                "feedback": feedback.get("feedback", "Approved"),
            })
            
            if feedback["action"] == "done":
                console.print(Panel(
                    content,
                    title="✅ Final Approved Version",
                    border_style="green",
                ))
                return {
                    "status": "approved",
                    "iterations": iteration,
                    "final_content": content,
                    "feedback_history": feedback_history,
                }
        
        console.print("\n[yellow]⚠ Max iterations reached.[/yellow]")
        return {
            "status": "max_iterations",
            "iterations": self.max_iterations,
            "final_content": content,
            "feedback_history": feedback_history,
        }


if __name__ == "__main__":
    console.print(Panel(
        "[bold]Feedback Loop Demo[/bold]\n\n"
        "This demo shows ITERATIVE human-agent collaboration.\n"
        "The agent writes, you give feedback, agent improves.\n"
        "Repeat until you're satisfied (type 'done').\n\n"
        "Unlike approval gates, this is about COLLABORATION, not just gatekeeping.",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    agent = FeedbackLoopAgent(max_iterations=5)
    result = agent.run("Why Every Developer Should Learn About AI Agents in 2025")
    
    console.print(f"\n[bold]Total iterations:[/bold] {result['iterations']}")
    
    console.print(Panel(
        "[bold]KEY TAKEAWAY:[/bold]\n"
        "✅ Feedback loops enable COLLABORATIVE content creation\n"
        "✅ Each iteration builds on previous feedback\n"
        "✅ The human shapes the output without doing the writing\n"
        "✅ Great for: content creation, code review, design iteration\n\n"
        "[bold]APPROVAL GATE vs FEEDBACK LOOP:[/bold]\n"
        "  Approval Gate: Yes/No decision on a finished product\n"
        "  Feedback Loop: Iterative refinement through collaboration",
        title="💡 Feedback Loop Pattern",
        border_style="green",
    ))
