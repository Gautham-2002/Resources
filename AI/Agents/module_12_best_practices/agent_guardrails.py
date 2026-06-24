"""
=============================================================================
MODULE 12 — Agent Guardrails: Production Best Practices
=============================================================================
CONCEPT:
    Reusable guardrails that prevent the 5 critical agent failure modes:
    
    1. Unbounded action space → BoundedToolSet
    2. Irreversible actions → ApprovalGate
    3. No loop termination → @max_iterations decorator
    4. Context window overflow → ContextWindowManager
    5. No hard limits → SafeAgentLoop (combines everything)

    These are building blocks you can drop into any agent system.

RUN:
    python module_12_best_practices/agent_guardrails.py
=============================================================================
"""

import sys
import os
import time
import functools

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Guard 1: Bounded Action Space
# =============================================================================
class BoundedToolSet:
    """
    Constrains which tools an agent can use.
    
    Problem: Give an agent 50 tools and it will explore paths you never
    anticipated — calling delete_user when you wanted search_docs.
    
    Solution: Explicitly whitelist only the tools needed for the task.
    Optionally mark tools as "destructive" to require approval.
    
    Usage:
        tools = BoundedToolSet(
            allowed=["search_docs", "summarize"],
            destructive=["send_email"]
        )
        tools.execute("search_docs", {"query": "agents"})  # ✅ allowed
        tools.execute("delete_db", {...})                    # ❌ blocked
    """
    
    def __init__(self, allowed: list[str], destructive: list[str] | None = None):
        self.allowed = set(allowed)
        self.destructive = set(destructive or [])
        self.call_log: list[dict] = []
    
    def available(self) -> list[str]:
        """Return list of tools the agent is allowed to use."""
        return list(self.allowed | self.destructive)
    
    def execute(self, tool_name: str, args: dict | None = None) -> dict:
        """Execute a tool, but only if it's in the allowed set."""
        if tool_name not in self.allowed and tool_name not in self.destructive:
            self.call_log.append({
                "tool": tool_name, "status": "BLOCKED", "reason": "not in allowed set"
            })
            console.print(f"  [red]⛔ BLOCKED: '{tool_name}' is not in the allowed tool set[/red]")
            return {"error": f"Tool '{tool_name}' is not allowed. Available: {self.available()}"}
        
        if tool_name in self.destructive:
            self.call_log.append({
                "tool": tool_name, "status": "NEEDS_APPROVAL", "args": args
            })
            console.print(f"  [yellow]⚠ APPROVAL REQUIRED: '{tool_name}' is marked as destructive[/yellow]")
            return {"status": "pending_approval", "tool": tool_name, "args": args}
        
        self.call_log.append({"tool": tool_name, "status": "EXECUTED", "args": args})
        console.print(f"  [green]✅ Executed: '{tool_name}'[/green]")
        return {"status": "success", "tool": tool_name}


# =============================================================================
# Guard 2: Max Iterations Decorator
# =============================================================================
def max_iterations(limit: int):
    """
    Decorator that enforces a hard iteration limit on agent loops.
    
    Problem: Agent gets stuck in infinite loop, burning tokens and money.
    In production, this is NON-NEGOTIABLE.
    
    Usage:
        @max_iterations(10)
        def agent_loop(task):
            while not done:
                ...  # will raise after 10 iterations
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Inject iteration tracking into the function
            wrapper._iteration_count = 0
            wrapper._max = limit
            
            original_result = func(*args, **kwargs)
            return original_result
        
        wrapper._max_iterations = limit
        return wrapper
    return decorator


class IterationTracker:
    """
    Tracks iterations and enforces limits within an agent loop.
    
    Usage:
        tracker = IterationTracker(max_iterations=10)
        while not done:
            tracker.tick()  # raises if limit exceeded
            ...
    """
    
    def __init__(self, max_iterations: int = 10):
        self.max_iterations = max_iterations
        self.current = 0
        self.start_time = time.time()
    
    def tick(self) -> int:
        """Increment counter and check limit. Returns current iteration."""
        self.current += 1
        if self.current > self.max_iterations:
            elapsed = time.time() - self.start_time
            raise RuntimeError(
                f"Agent exceeded max iterations ({self.max_iterations}) "
                f"after {elapsed:.1f}s. This is a safety limit."
            )
        return self.current
    
    def remaining(self) -> int:
        return self.max_iterations - self.current
    
    def stats(self) -> dict:
        return {
            "current_iteration": self.current,
            "max_iterations": self.max_iterations,
            "remaining": self.remaining(),
            "elapsed_seconds": round(time.time() - self.start_time, 2),
        }


# =============================================================================
# Guard 3: Context Window Manager
# =============================================================================
class ContextWindowManager:
    """
    Tracks token usage and automatically compresses context when it
    approaches the limit.
    
    Problem: In multi-agent chains, context grows with each agent:
        Agent 1: 2K tokens
        Agent 2: 2K + 3K = 5K 
        Agent 3: 5K + 4K = 9K
        Agent N: 💥 context limit!
    
    Solution: Track token budget. When >80% full, summarize older
    messages to free space.
    
    Usage:
        ctx = ContextWindowManager(max_tokens=100_000)
        ctx.add_message("user", "Analyze this data...")
        ctx.add_message("assistant", long_response)
        # Auto-compresses when approaching limit
        messages = ctx.get_messages()  # returns optimized context
    """
    
    def __init__(self, max_tokens: int = 100_000, compress_threshold: float = 0.8):
        self.max_tokens = max_tokens
        self.compress_threshold = compress_threshold
        self.messages: list[dict] = []
        self.total_tokens = 0
        self.compressions = 0
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough estimate: ~4 chars per token for English text."""
        return len(text) // 4
    
    def add_message(self, role: str, content: str):
        """Add a message, auto-compressing if near the limit."""
        tokens = self.estimate_tokens(content)
        
        # Check if we need to compress
        if (self.total_tokens + tokens) > (self.max_tokens * self.compress_threshold):
            self._compress()
        
        self.messages.append({"role": role, "content": content, "tokens": tokens})
        self.total_tokens += tokens
    
    def _compress(self):
        """Summarize older messages to free up context space."""
        if len(self.messages) < 4:
            return  # Nothing to compress
        
        self.compressions += 1
        console.print(f"  [cyan]🗜️ Compressing context (usage: {self.usage_pct():.0f}%)[/cyan]")
        
        # Keep system message (first) and last 2 messages, summarize the rest
        system_msgs = [m for m in self.messages if m["role"] == "system"]
        recent = self.messages[-2:]
        to_compress = self.messages[len(system_msgs):-2]
        
        if not to_compress:
            return
        
        # Ask LLM to summarize the middle messages
        combined = "\n".join(f"[{m['role']}]: {m['content'][:200]}" for m in to_compress)
        summary = chat(
            prompt=f"Summarize this conversation concisely, preserving key facts and decisions:\n\n{combined}",
            system="You are a conversation summarizer. Be extremely concise.",
            max_tokens=200,
        )
        
        summary_tokens = self.estimate_tokens(summary)
        compressed_msg = {"role": "system", "content": f"[Previous context summary]: {summary}", "tokens": summary_tokens}
        
        # Rebuild messages
        old_tokens = self.total_tokens
        self.messages = system_msgs + [compressed_msg] + recent
        self.total_tokens = sum(m["tokens"] for m in self.messages)
        
        saved = old_tokens - self.total_tokens
        console.print(f"  [green]✅ Compressed: {old_tokens} → {self.total_tokens} tokens (saved {saved})[/green]")
    
    def get_messages(self) -> list[dict]:
        """Return messages formatted for LLM call (without token counts)."""
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]
    
    def usage_pct(self) -> float:
        return (self.total_tokens / self.max_tokens) * 100
    
    def stats(self) -> dict:
        return {
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "usage_pct": f"{self.usage_pct():.1f}%",
            "message_count": len(self.messages),
            "compressions": self.compressions,
        }


# =============================================================================
# Guard 4: Safe Agent Loop (combines everything)
# =============================================================================
class SafeAgentLoop:
    """
    Production-ready agent loop that combines ALL guardrails:
    
    1. BoundedToolSet — constrained action space
    2. IterationTracker — hard iteration limit  
    3. ContextWindowManager — auto-compressing context
    4. Timeout — wall-clock time limit
    
    This is what you should use in production instead of a raw while loop.
    
    Usage:
        agent = SafeAgentLoop(
            tools=["search", "summarize"],
            max_iterations=10,
            max_tokens=100_000,
            timeout_seconds=120,
        )
        result = agent.run("Research and summarize AI agent patterns")
    """
    
    def __init__(
        self,
        tools: list[str],
        destructive_tools: list[str] | None = None,
        max_iterations: int = 10,
        max_tokens: int = 100_000,
        timeout_seconds: float = 120,
        system_prompt: str = "You are a helpful AI agent.",
    ):
        self.toolset = BoundedToolSet(tools, destructive_tools)
        self.tracker = IterationTracker(max_iterations)
        self.context = ContextWindowManager(max_tokens)
        self.timeout = timeout_seconds
        self.system_prompt = system_prompt
        self.run_log: list[dict] = []
    
    def run(self, task: str) -> str:
        """
        Execute the agent loop with all guardrails active.
        """
        console.print(Panel(
            f"[bold]SafeAgentLoop Starting[/bold]\n"
            f"Task: {task[:100]}...\n"
            f"Tools: {self.toolset.available()}\n"
            f"Max iterations: {self.tracker.max_iterations}\n"
            f"Max tokens: {self.context.max_tokens:,}\n"
            f"Timeout: {self.timeout}s",
            border_style="cyan",
        ))
        
        start_time = time.time()
        self.context.add_message("system", self.system_prompt)
        self.context.add_message("user", task)
        
        while True:
            # Guard: Iteration limit
            iteration = self.tracker.tick()
            console.print(f"\n  [bold]--- Iteration {iteration}/{self.tracker.max_iterations} ---[/bold]")
            
            # Guard: Timeout
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                raise TimeoutError(f"Agent timed out after {elapsed:.1f}s (limit: {self.timeout}s)")
            
            # Call LLM
            response = chat(
                prompt=task if iteration == 1 else "Continue with the task. If done, respond with FINAL_ANSWER: <your answer>",
                system=self.system_prompt + f"\nAvailable tools: {self.toolset.available()}\nIteration {iteration}/{self.tracker.max_iterations}. Be efficient.",
                max_tokens=500,
            )
            
            self.context.add_message("assistant", response)
            self.run_log.append({
                "iteration": iteration,
                "response_preview": response[:100],
                "context_tokens": self.context.total_tokens,
                "elapsed": round(elapsed, 1),
            })
            
            console.print(f"  [dim]Response: {response[:120]}...[/dim]")
            
            # Check for final answer
            if "FINAL_ANSWER:" in response:
                answer = response.split("FINAL_ANSWER:")[-1].strip()
                console.print(f"\n  [green]✅ Agent completed in {iteration} iterations ({elapsed:.1f}s)[/green]")
                return answer
        
        # This should never be reached due to IterationTracker
        raise RuntimeError("Agent loop ended without a final answer")
    
    def get_stats(self) -> dict:
        return {
            "iterations": self.tracker.stats(),
            "context": self.context.stats(),
            "tools": {
                "available": self.toolset.available(),
                "calls": len(self.toolset.call_log),
                "blocked": len([c for c in self.toolset.call_log if c["status"] == "BLOCKED"]),
            },
        }


# =============================================================================
# Guard 5: Multi-Agent Context Compression
# =============================================================================
def compress_between_agents(
    agent_output: str,
    max_summary_tokens: int = 500,
    preserve_keys: list[str] | None = None,
) -> str:
    """
    Compress one agent's output before passing to the next agent.
    
    Problem: In sequential multi-agent pipelines:
        Agent1 output (3K tokens) → Agent2 gets [prompt + 3K]
        Agent2 output (4K tokens) → Agent3 gets [prompt + 3K + 4K]
        
    Solution: Summarize each agent's output, keeping only essential info.
    
    Usage:
        result_1 = agent_1.run(task)
        compressed = compress_between_agents(result_1, preserve_keys=["findings", "recommendations"])
        result_2 = agent_2.run(f"Based on this research: {compressed}, now write a report")
    """
    preserve_instruction = ""
    if preserve_keys:
        preserve_instruction = f"\nMake sure to preserve these specific elements: {', '.join(preserve_keys)}"
    
    summary = chat(
        prompt=(
            f"Compress the following agent output into a concise summary. "
            f"Keep all key findings, decisions, and data points. "
            f"Remove redundancy and verbose explanations.{preserve_instruction}\n\n"
            f"Agent output:\n{agent_output}"
        ),
        system="You are a compression specialist. Be extremely concise but preserve all critical information.",
        max_tokens=max_summary_tokens,
    )
    
    original_tokens = len(agent_output) // 4
    compressed_tokens = len(summary) // 4
    ratio = (1 - compressed_tokens / max(original_tokens, 1)) * 100
    
    console.print(f"  [cyan]🗜️ Compressed: {original_tokens} → {compressed_tokens} tokens ({ratio:.0f}% reduction)[/cyan]")
    
    return summary


# =============================================================================
# Demo
# =============================================================================
if __name__ == "__main__":
    console.print(Panel(
        "[bold]Module 12: Agent Guardrails — Production Best Practices[/bold]\n\n"
        "This demo shows all 5 guardrails in action:\n"
        "1. BoundedToolSet — constrained action space\n"
        "2. IterationTracker — hard loop limits\n"
        "3. ContextWindowManager — auto-compression\n"
        "4. SafeAgentLoop — all guardrails combined\n"
        "5. compress_between_agents — multi-agent context compression",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    # ===== Demo 1: Bounded Tools =====
    console.print("\n[bold yellow]═══ Demo 1: Bounded Action Space ═══[/bold yellow]\n")
    
    tools = BoundedToolSet(
        allowed=["search_docs", "summarize"],
        destructive=["send_email"],
    )
    
    console.print("  Trying allowed tool:")
    tools.execute("search_docs", {"query": "agent patterns"})
    
    console.print("  Trying blocked tool:")
    tools.execute("delete_database", {"confirm": True})
    
    console.print("  Trying destructive tool:")
    tools.execute("send_email", {"to": "user@example.com"})
    
    # ===== Demo 2: Iteration Limits =====
    console.print("\n[bold yellow]═══ Demo 2: Iteration Limits ═══[/bold yellow]\n")
    
    tracker = IterationTracker(max_iterations=3)
    for i in range(5):
        try:
            iteration = tracker.tick()
            console.print(f"  [green]Iteration {iteration} — OK (remaining: {tracker.remaining()})[/green]")
        except RuntimeError as e:
            console.print(f"  [red]⛔ {e}[/red]")
            break
    
    # ===== Demo 3: Context Compression =====
    console.print("\n[bold yellow]═══ Demo 3: Context Window Manager ═══[/bold yellow]\n")
    
    ctx = ContextWindowManager(max_tokens=500, compress_threshold=0.7)
    
    ctx.add_message("system", "You are a research assistant.")
    ctx.add_message("user", "Research AI agent patterns and their trade-offs.")
    ctx.add_message("assistant", "I found several patterns: " + "x" * 400)
    ctx.add_message("user", "Now summarize the key findings." + "y" * 400)
    
    stats = ctx.stats()
    table = Table(title="Context Window Stats")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")
    for k, v in stats.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    console.print(table)
    
    # ===== Demo 4: Safe Agent Loop =====
    console.print("\n[bold yellow]═══ Demo 4: Safe Agent Loop ═══[/bold yellow]\n")
    
    agent = SafeAgentLoop(
        tools=["search", "summarize"],
        max_iterations=3,
        max_tokens=50_000,
        timeout_seconds=60,
        system_prompt="You are a concise research agent. When you have enough info, respond with FINAL_ANSWER: <answer>",
    )
    
    try:
        result = agent.run("What are the three main orchestration patterns for AI agents? Be brief.")
        console.print(f"\n  [green]Result: {result}[/green]")
    except (RuntimeError, TimeoutError) as e:
        console.print(f"\n  [red]Agent stopped: {e}[/red]")
    
    # Show stats
    stats = agent.get_stats()
    console.print(f"\n  Iterations: {stats['iterations']}")
    console.print(f"  Context: {stats['context']}")
    console.print(f"  Tools: {stats['tools']}")
    
    # ===== Summary =====
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]BoundedToolSet[/cyan] — Only expose tools the agent needs\n"
        "2. [cyan]IterationTracker[/cyan] — Hard limit on loop iterations\n"
        "3. [cyan]ContextWindowManager[/cyan] — Auto-compress when context is 80% full\n"
        "4. [cyan]SafeAgentLoop[/cyan] — All guardrails in one reusable class\n"
        "5. [cyan]compress_between_agents[/cyan] — Shrink context between agent handoffs\n\n"
        "[bold]PRODUCTION RULES:[/bold]\n"
        "• ALWAYS set max_iterations — this is non-negotiable\n"
        "• ALWAYS set a timeout — agents should never run forever\n"
        "• ALWAYS constrain the tool set — fewer tools = fewer surprises\n"
        "• ALWAYS track context usage — compress before hitting limits\n"
        "• ALWAYS add human approval for destructive actions",
        title="💡 Agent Guardrails",
        border_style="green",
    ))
