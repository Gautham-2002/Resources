"""
=============================================================================
MODULE 9 — DEMO 1: Retry with Exponential Backoff + Circuit Breaker
=============================================================================
CONCEPT:
    RETRY: When an LLM call fails, don't just give up — retry with increasing
    delays (exponential backoff) to give the service time to recover.
    
    CIRCUIT BREAKER: If a service keeps failing, STOP calling it entirely
    for a cooldown period. This prevents overwhelming a struggling service.
    
    States: CLOSED (normal) → OPEN (blocking) → HALF-OPEN (testing)

RUN:
    python module_9_production_patterns/retry_circuit_breaker.py
=============================================================================
"""

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Retry with Exponential Backoff
# =============================================================================
class RetryWithBackoff:
    """
    Retry a function with exponential backoff and jitter.
    
    Backoff formula: min(base_delay * 2^attempt + jitter, max_delay)
    
    Example delays: 1s → 2s → 4s → 8s → 16s (capped at max_delay)
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.attempt_log: list[dict] = []
    
    def execute(self, func, *args, **kwargs):
        """Execute a function with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                start = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start
                
                self.attempt_log.append({
                    "attempt": attempt + 1,
                    "status": "success",
                    "duration": f"{duration:.2f}s",
                })
                console.print(f"  [green]✅ Attempt {attempt + 1}: Success ({duration:.2f}s)[/green]")
                return result
                
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries:
                    # Calculate delay with exponential backoff
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    if self.jitter:
                        delay += random.uniform(0, delay * 0.1)
                    
                    self.attempt_log.append({
                        "attempt": attempt + 1,
                        "status": "failed",
                        "error": str(e)[:50],
                        "retry_delay": f"{delay:.2f}s",
                    })
                    console.print(f"  [yellow]⚠ Attempt {attempt + 1}: Failed ({e}). Retrying in {delay:.1f}s...[/yellow]")
                    time.sleep(delay)
                else:
                    self.attempt_log.append({
                        "attempt": attempt + 1,
                        "status": "failed (final)",
                        "error": str(e)[:50],
                    })
                    console.print(f"  [red]❌ Attempt {attempt + 1}: Final failure ({e})[/red]")
        
        raise last_error


# =============================================================================
# Step 2: Circuit Breaker
# =============================================================================
class CircuitBreaker:
    """
    Circuit Breaker pattern.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is down, requests fail immediately (fast fail)
    - HALF-OPEN: After cooldown, allow ONE test request
    
    Transitions:
    - CLOSED → OPEN: After `failure_threshold` consecutive failures
    - OPEN → HALF-OPEN: After `reset_timeout` seconds
    - HALF-OPEN → CLOSED: If test request succeeds
    - HALF-OPEN → OPEN: If test request fails
    """
    
    def __init__(self, failure_threshold: int = 3, reset_timeout: float = 10.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state_log: list[dict] = []
    
    def _log_state(self, action: str):
        self.state_log.append({
            "state": self.state,
            "action": action,
            "failure_count": self.failure_count,
            "time": time.time(),
        })
    
    def call(self, func, *args, **kwargs):
        """Execute a function through the circuit breaker."""
        
        if self.state == "OPEN":
            # Check if cooldown has elapsed
            if self.last_failure_time and (time.time() - self.last_failure_time) >= self.reset_timeout:
                self.state = "HALF-OPEN"
                self._log_state("cooldown_elapsed → HALF-OPEN")
                console.print(f"  [cyan]🔄 Circuit: OPEN → HALF-OPEN (testing...)[/cyan]")
            else:
                self._log_state("fast_fail")
                remaining = self.reset_timeout - (time.time() - (self.last_failure_time or 0))
                console.print(f"  [red]⛔ Circuit OPEN — Fast failing (cooldown: {remaining:.1f}s left)[/red]")
                raise Exception("Circuit breaker is OPEN — fast fail")
        
        try:
            result = func(*args, **kwargs)
            
            # Success: reset to CLOSED
            if self.state == "HALF-OPEN":
                console.print(f"  [green]✅ Circuit: HALF-OPEN → CLOSED (recovered!)[/green]")
            self.state = "CLOSED"
            self.failure_count = 0
            self._log_state("success")
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                old_state = self.state
                self.state = "OPEN"
                self._log_state(f"threshold_reached → OPEN")
                console.print(f"  [red]🔴 Circuit: {old_state} → OPEN ({self.failure_count} failures)[/red]")
            else:
                self._log_state("failure")
                console.print(f"  [yellow]⚠ Failure {self.failure_count}/{self.failure_threshold}[/yellow]")
            
            raise


# =============================================================================
# Step 3: Demo functions
# =============================================================================
call_counter = {"count": 0}

def unreliable_agent_call(fail_first_n: int = 2) -> str:
    """Simulates an unreliable external service — fails first N times."""
    call_counter["count"] += 1
    if call_counter["count"] <= fail_first_n:
        raise ConnectionError(f"Service unavailable (call #{call_counter['count']})")
    return chat(
        prompt="Say 'I recovered successfully!' in one sentence.",
        system="You are a test agent.",
        max_tokens=30,
    )


def always_failing_call() -> str:
    """Always fails — to demonstrate circuit breaker opening."""
    raise ConnectionError("Service is completely down!")


# =============================================================================
# Step 4: Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(Panel(
        "[bold]Retry + Circuit Breaker Demo[/bold]\n\n"
        "Scenario 1: Retry with exponential backoff (service recovers after 2 failures)\n"
        "Scenario 2: Circuit breaker opens after 3 consecutive failures",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    # ===== Scenario 1: Retry =====
    console.print("\n[bold yellow]═══ Scenario 1: Retry with Exponential Backoff ═══[/bold yellow]\n")
    
    call_counter["count"] = 0
    retry = RetryWithBackoff(max_retries=4, base_delay=0.5)
    
    try:
        result = retry.execute(unreliable_agent_call, fail_first_n=2)
        console.print(f"\n  [green]Final result: {result}[/green]")
    except Exception as e:
        console.print(f"\n  [red]All retries failed: {e}[/red]")
    
    # Show retry log
    table = Table(title="Retry Attempt Log")
    table.add_column("Attempt", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Details", style="white")
    
    for entry in retry.attempt_log:
        status_style = "green" if entry["status"] == "success" else "red"
        details = entry.get("retry_delay", entry.get("error", ""))
        table.add_row(str(entry["attempt"]), f"[{status_style}]{entry['status']}[/{status_style}]", details)
    
    console.print(table)
    
    # ===== Scenario 2: Circuit Breaker =====
    console.print("\n[bold yellow]═══ Scenario 2: Circuit Breaker ═══[/bold yellow]\n")
    
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=3.0)
    
    # Make 5 calls — first 3 fail → circuit opens → calls 4 & 5 are fast-failed
    for i in range(5):
        try:
            console.print(f"\n  [bold]Call {i+1}:[/bold] Circuit state = [cyan]{cb.state}[/cyan]")
            cb.call(always_failing_call)
        except Exception as e:
            console.print(f"    Error: {e}")
    
    # Wait for cooldown
    console.print(f"\n  [dim]Waiting {cb.reset_timeout}s for circuit reset...[/dim]")
    time.sleep(cb.reset_timeout + 0.5)
    
    # After cooldown — circuit should be HALF-OPEN
    console.print(f"\n  [bold]Call 6 (after cooldown):[/bold] Circuit state = [cyan]{cb.state}[/cyan]")
    call_counter["count"] = 0
    try:
        result = cb.call(unreliable_agent_call, fail_first_n=0)
        console.print(f"    [green]Success! Circuit recovered: {result}[/green]")
    except Exception as e:
        console.print(f"    [red]Failed: {e}[/red]")
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]Exponential Backoff[/cyan] — Delays double: 1s → 2s → 4s → 8s\n"
        "2. [cyan]Jitter[/cyan] — Random delay added to prevent thundering herd\n"
        "3. [cyan]Circuit Breaker States[/cyan] — CLOSED → OPEN → HALF-OPEN\n"
        "4. [cyan]Fast Fail[/cyan] — When circuit is OPEN, fail immediately\n"
        "5. [cyan]Self-Healing[/cyan] — HALF-OPEN allows recovery testing",
        title="💡 Retry + Circuit Breaker",
        border_style="green",
    ))
