"""
=============================================================================
MODULE 9 — DEMO 3: Rate Limiter — Token Bucket Algorithm
=============================================================================
CONCEPT:
    Rate limiting prevents agents from overwhelming downstream APIs.
    
    Without rate limiting:
    - 100 parallel agents → 100 simultaneous API calls → rate limit ban
    - Cascading failures as agents retry → even MORE load
    
    The Token Bucket algorithm:
    - A bucket holds N tokens (max burst capacity)
    - Tokens are added at a steady rate (e.g., 10/second)
    - Each API call consumes one token
    - If bucket is empty, the call WAITS until a token is available

RUN:
    python module_9_production_patterns/rate_limiter_demo.py
=============================================================================
"""

import sys
import os
import time
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Token Bucket Rate Limiter
# =============================================================================
class TokenBucketRateLimiter:
    """
    Token Bucket rate limiter.
    
    Parameters:
    - rate: tokens added per second
    - capacity: maximum tokens (burst capacity)
    
    Example: rate=2, capacity=5
    - Steady state: 2 calls/second
    - Burst: up to 5 calls instantly (then back to 2/second)
    """
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate            # Tokens per second
        self.capacity = capacity     # Max tokens
        self.tokens = capacity       # Start full
        self.last_refill = time.time()
        self.call_log: list[dict] = []
        self.total_waited: float = 0
    
    def _refill(self):
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now
    
    def acquire(self, tokens: int = 1, wait: bool = True) -> bool:
        """
        Acquire tokens to make an API call.
        
        If wait=True: blocks until tokens are available
        If wait=False: returns False immediately if no tokens
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            self.call_log.append({
                "time": datetime.now().isoformat(),
                "action": "acquired",
                "tokens_remaining": round(self.tokens, 2),
                "waited": 0,
            })
            return True
        elif wait:
            # Calculate wait time
            needed = tokens - self.tokens
            wait_time = needed / self.rate
            
            self.call_log.append({
                "time": datetime.now().isoformat(),
                "action": "waiting",
                "wait_seconds": round(wait_time, 2),
                "tokens_remaining": round(self.tokens, 2),
            })
            console.print(f"    [yellow]⏳ Rate limited — waiting {wait_time:.2f}s for tokens[/yellow]")
            
            time.sleep(wait_time)
            self.total_waited += wait_time
            self._refill()
            self.tokens -= tokens
            return True
        else:
            self.call_log.append({
                "time": datetime.now().isoformat(),
                "action": "rejected",
                "tokens_remaining": round(self.tokens, 2),
            })
            return False
    
    def stats(self) -> dict:
        return {
            "current_tokens": round(self.tokens, 2),
            "capacity": self.capacity,
            "rate": f"{self.rate}/s",
            "total_calls": len([c for c in self.call_log if c["action"] == "acquired"]),
            "total_waited_seconds": round(self.total_waited, 2),
            "total_rejections": len([c for c in self.call_log if c["action"] == "rejected"]),
        }


# =============================================================================
# Step 2: Rate-limited agent function
# =============================================================================
def rate_limited_agent_call(limiter: TokenBucketRateLimiter, task_id: int, prompt: str) -> dict:
    """Make an LLM call through the rate limiter."""
    console.print(f"  [cyan]Agent {task_id}:[/cyan] Requesting token...")
    
    limiter.acquire(wait=True)  # Block until a token is available
    
    start = time.time()
    result = chat(prompt=prompt, system="You are a concise agent.", max_tokens=50)
    duration = time.time() - start
    
    console.print(f"  [green]Agent {task_id}:[/green] Done ({duration:.1f}s) — tokens left: {limiter.tokens:.1f}")
    
    return {"task_id": task_id, "result": result, "duration": duration}


# =============================================================================
# Step 3: Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(Panel(
        "[bold]Rate Limiter Demo — Token Bucket Algorithm[/bold]\n\n"
        "This demo shows:\n"
        "1. Burst: 5 rapid calls using stored tokens\n"
        "2. Throttle: Subsequent calls are rate-limited\n"
        "3. Stats: How many calls waited and for how long\n\n"
        "Config: rate=2 tokens/sec, capacity=3 (burst=3)",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    # Create rate limiter: 2 calls/sec, burst of 3
    limiter = TokenBucketRateLimiter(rate=2, capacity=3)
    
    # ===== Part 1: Burst capacity =====
    console.print("\n[bold yellow]═══ Part 1: Burst Capacity (3 tokens) ═══[/bold yellow]\n")
    
    for i in range(3):
        console.print(f"  Call {i+1}: tokens={limiter.tokens:.1f}")
        limiter.acquire()
        console.print(f"    [green]✅ Acquired (no wait)[/green] — tokens left: {limiter.tokens:.1f}")
    
    # ===== Part 2: Rate-limited calls =====
    console.print("\n[bold yellow]═══ Part 2: Rate-Limited Calls (bucket empty) ═══[/bold yellow]\n")
    
    for i in range(4):
        console.print(f"  Call {i+4}: tokens={limiter.tokens:.1f}")
        limiter.acquire()
        console.print(f"    [green]✅ Acquired — tokens left: {limiter.tokens:.1f}")
    
    # ===== Part 3: Full agent demo with LLM =====
    console.print("\n[bold yellow]═══ Part 3: Rate-Limited Agent Calls ═══[/bold yellow]\n")
    
    limiter2 = TokenBucketRateLimiter(rate=2, capacity=2)
    prompts = [
        "What is Python? Answer in 5 words.",
        "What is JavaScript? Answer in 5 words.",
        "What is Rust? Answer in 5 words.",
        "What is Go? Answer in 5 words.",
    ]
    
    results = []
    for i, prompt in enumerate(prompts):
        r = rate_limited_agent_call(limiter2, i + 1, prompt)
        results.append(r)
    
    # Stats
    stats = limiter2.stats()
    table = Table(title="Rate Limiter Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")
    
    for k, v in stats.items():
        table.add_row(k.replace("_", " ").title(), str(v))
    
    console.print(table)
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]Token Bucket[/cyan] — Tokens fill at a steady rate, calls consume tokens\n"
        "2. [cyan]Burst[/cyan] — Initial tokens allow short bursts above steady rate\n"
        "3. [cyan]Backpressure[/cyan] — When empty, calls WAIT for tokens\n"
        "4. [cyan]Steady State[/cyan] — Calls match the token refill rate\n\n"
        "[bold]PRODUCTION TIPS:[/bold]\n"
        "• Per-provider limits (OpenAI: 60/min, Anthropic: 50/min)\n"
        "• Use Redis for distributed rate limiting across instances\n"
        "• Monitor 429 errors to auto-adjust rate limits",
        title="💡 Rate Limiting for Agents",
        border_style="green",
    ))
