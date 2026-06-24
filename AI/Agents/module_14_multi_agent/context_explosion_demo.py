"""
=============================================================================
MODULE 14 — DEMO 5: Context Explosion + Solutions
=============================================================================
CONCEPT:
    When agents run in sequence, each one gets a larger prompt:
    
    Agent 1: prompt (2K tokens) → outputs 3K
    Agent 2: prompt (2K) + Agent1 output (3K) = 5K → outputs 4K
    Agent 3: prompt (2K) + Agent1 (3K) + Agent2 (4K) = 9K → outputs 3K
    Agent N: 💥 hit context limit!
    
    This demo shows:
    1. The problem — context growing out of control
    2. The solution — compress between agents

RUN:
    python module_14_multi_agent/context_explosion_demo.py
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


def simulate_context_explosion(num_agents: int = 5):
    """
    Simulate how context grows in a naive multi-agent pipeline.
    Each agent's output is appended to the prompt for the next agent.
    """
    console.print(Panel(
        "[bold red]PROBLEM: Context Explosion (No Compression)[/bold red]\n"
        "Each agent's output is passed ENTIRELY to the next agent.",
        border_style="red",
    ))
    
    context = "Research the current state of AI agents and write a comprehensive report."
    total_tokens = len(context) // 4
    
    table = Table(title="Context Growth — No Compression")
    table.add_column("Agent", style="cyan")
    table.add_column("Input Tokens", style="yellow")
    table.add_column("Output Tokens", style="green")
    table.add_column("Total Context", style="red")
    table.add_column("Status", style="bold")
    
    MAX_CONTEXT = 8000  # Simulate a limit
    
    for i in range(1, num_agents + 1):
        input_tokens = total_tokens
        
        # Each agent generates substantial output
        agent_output = chat(
            prompt=f"Based on this context, provide analysis as Agent {i}:\n\n{context[:2000]}",
            system=f"You are Agent {i} in a multi-agent pipeline. Write a detailed analysis. Include background, findings, implications, and recommendations.",
            max_tokens=400,
        )
        
        output_tokens = len(agent_output) // 4
        
        # Naive approach: append everything
        context = context + "\n\n" + f"Agent {i} output:\n" + agent_output
        total_tokens = len(context) // 4
        
        status = "✅ OK" if total_tokens < MAX_CONTEXT * 0.7 else (
            "⚠️ Warning" if total_tokens < MAX_CONTEXT else "💥 OVERFLOW"
        )
        
        table.add_row(
            f"Agent {i}",
            str(input_tokens),
            str(output_tokens),
            str(total_tokens),
            status,
        )
        
        console.print(f"  Agent {i}: {input_tokens} → +{output_tokens} → {total_tokens} total  {status}")
    
    console.print(table)
    return total_tokens


def simulate_with_compression(num_agents: int = 5):
    """
    Same pipeline, but with compression between agents.
    Each agent's output is summarized before passing to the next.
    """
    console.print(Panel(
        "[bold green]SOLUTION: Compress Between Agents[/bold green]\n"
        "Each agent's output is SUMMARIZED before passing to the next.",
        border_style="green",
    ))
    
    context = "Research the current state of AI agents and write a comprehensive report."
    total_tokens = len(context) // 4
    
    table = Table(title="Context Growth — With Compression")
    table.add_column("Agent", style="cyan")
    table.add_column("Input Tokens", style="yellow")
    table.add_column("Output Tokens", style="green")
    table.add_column("After Compress", style="cyan")
    table.add_column("Total Context", style="green")
    table.add_column("Saved", style="magenta")
    
    for i in range(1, num_agents + 1):
        input_tokens = total_tokens
        
        # Agent generates output
        agent_output = chat(
            prompt=f"Based on this context, provide analysis as Agent {i}:\n\n{context[:2000]}",
            system=f"You are Agent {i} in a multi-agent pipeline. Write a detailed analysis.",
            max_tokens=400,
        )
        
        output_tokens = len(agent_output) // 4
        
        # SOLUTION: Compress before passing to next agent
        compressed = chat(
            prompt=f"Compress this to key facts only (max 3 sentences):\n\n{agent_output}",
            system="Extract only the essential findings. Be extremely concise.",
            max_tokens=100,
        )
        
        compressed_tokens = len(compressed) // 4
        saved = output_tokens - compressed_tokens
        
        context = context + "\n\n" + f"Agent {i} (compressed):\n" + compressed
        total_tokens = len(context) // 4
        
        table.add_row(
            f"Agent {i}",
            str(input_tokens),
            str(output_tokens),
            str(compressed_tokens),
            str(total_tokens),
            f"-{saved} ({(saved/max(output_tokens,1)*100):.0f}%)",
        )
        
        console.print(f"  Agent {i}: {output_tokens} tokens → compressed to {compressed_tokens}  (saved {saved})")
    
    console.print(table)
    return total_tokens


if __name__ == "__main__":
    console.print(Panel(
        "[bold]Module 14 — Demo 5: Context Explosion[/bold]\n\n"
        "This demo shows the #1 multi-agent challenge:\n"
        "Context grows uncontrollably as agents pass output to each other.\n\n"
        "You'll see:\n"
        "1. 🔴 Without compression — tokens explode\n"
        "2. 🟢 With compression — tokens stay manageable",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    # Run without compression
    tokens_no_compress = simulate_context_explosion(4)
    
    console.print("\n" + "=" * 60 + "\n")
    
    # Run with compression
    tokens_with_compress = simulate_with_compression(4)
    
    # Show comparison
    savings = tokens_no_compress - tokens_with_compress
    pct = (savings / max(tokens_no_compress, 1)) * 100
    
    console.print(Panel(
        f"[bold]RESULTS:[/bold]\n"
        f"• Without compression: {tokens_no_compress:,} tokens\n"
        f"• With compression:    {tokens_with_compress:,} tokens\n"
        f"• Savings:             {savings:,} tokens ({pct:.0f}%)\n\n"
        f"[bold]ALL 5 SOLUTIONS:[/bold]\n"
        f"1. [cyan]Summarize between agents[/cyan] — compress output before passing\n"
        f"2. [cyan]Selective context[/cyan] — only pass what next agent needs\n"
        f"3. [cyan]Shared memory (KV store)[/cyan] — agents read/write to shared store instead of prompt stuffing\n"
        f"4. [cyan]Token budgets[/cyan] — enforce max tokens per agent step\n"
        f"5. [cyan]Tiered models[/cyan] — use cheaper models for intermediate steps",
        title="💡 Context Explosion Solutions",
        border_style="green",
    ))
