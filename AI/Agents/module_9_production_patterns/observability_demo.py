"""
=============================================================================
MODULE 9 — DEMO 2: Observability — Structured Logging + Trace IDs
=============================================================================
CONCEPT:
    When agents call agents call agents, you need to trace the entire chain.
    
    Structured logging with CORRELATION IDs lets you:
    - Track a request across multiple agent calls
    - Debug failures by following the trace
    - Monitor performance of each agent in the chain
    
    This is the agent equivalent of distributed tracing (like Jaeger/Zipkin).

RUN:
    python module_9_production_patterns/observability_demo.py
=============================================================================
"""

import sys
import os
import uuid
import json
import time
from datetime import datetime
from functools import wraps

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Structured Logger with Trace IDs
# =============================================================================
class AgentLogger:
    """
    Structured JSON logger with trace/correlation ID support.
    
    Every log entry includes:
    - trace_id: unique ID for the entire request chain
    - span_id: unique ID for this specific operation
    - parent_span_id: links to the calling operation
    - timestamp, level, agent, message, duration
    
    This creates a TRACE TREE that you can follow:
    
    trace_id: abc123
    ├── span_1: Coordinator (parent: none)
    │   ├── span_2: Researcher (parent: span_1)
    │   └── span_3: Writer (parent: span_1)
    """
    
    def __init__(self):
        self.logs: list[dict] = []
    
    def log(
        self,
        level: str,
        agent: str,
        message: str,
        trace_id: str,
        span_id: str,
        parent_span_id: str | None = None,
        duration_ms: float | None = None,
        metadata: dict | None = None,
    ):
        """Create a structured log entry."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "agent": agent,
            "message": message,
            "duration_ms": duration_ms,
            "metadata": metadata or {},
        }
        self.logs.append(entry)
        
        # Pretty print to console
        color = {"INFO": "green", "WARN": "yellow", "ERROR": "red"}.get(level, "white")
        parent_info = f" (parent: {parent_span_id[:8]})" if parent_span_id else ""
        duration_info = f" [{duration_ms:.0f}ms]" if duration_ms else ""
        console.print(
            f"  [{color}]{level}[/{color}] "
            f"[dim]trace:{trace_id[:8]}|span:{span_id[:8]}{parent_info}[/dim] "
            f"[bold]{agent}[/bold]: {message}{duration_info}"
        )
    
    def get_trace(self, trace_id: str) -> list[dict]:
        """Get all log entries for a specific trace."""
        return [l for l in self.logs if l["trace_id"] == trace_id]


# Global logger
logger = AgentLogger()


# =============================================================================
# Step 2: Traced agent decorator
# =============================================================================
def traced_agent(agent_name: str):
    """
    Decorator that automatically adds tracing to agent functions.
    
    Usage:
        @traced_agent("researcher")
        def research(topic, trace_id, parent_span_id=None):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, trace_id: str, parent_span_id: str | None = None, **kwargs):
            span_id = str(uuid.uuid4())[:12]
            
            logger.log("INFO", agent_name, f"Starting: {func.__name__}", 
                       trace_id=trace_id, span_id=span_id, parent_span_id=parent_span_id)
            
            start = time.time()
            try:
                result = func(*args, trace_id=trace_id, span_id=span_id, **kwargs)
                duration = (time.time() - start) * 1000
                
                logger.log("INFO", agent_name, f"Completed: {func.__name__}",
                          trace_id=trace_id, span_id=span_id, parent_span_id=parent_span_id,
                          duration_ms=duration)
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                logger.log("ERROR", agent_name, f"Failed: {func.__name__} — {e}",
                          trace_id=trace_id, span_id=span_id, parent_span_id=parent_span_id,
                          duration_ms=duration)
                raise
        return wrapper
    return decorator


# =============================================================================
# Step 3: Traced agent chain
# =============================================================================
@traced_agent("Coordinator")
def coordinate(topic: str, trace_id: str, span_id: str) -> str:
    """Coordinator agent that delegates to sub-agents."""
    # Call researcher (child span)
    research_result = research(topic, trace_id=trace_id, parent_span_id=span_id)
    
    # Call writer (child span)
    article = write(topic, research_result, trace_id=trace_id, parent_span_id=span_id)
    
    return article


@traced_agent("Researcher")
def research(topic: str, trace_id: str, span_id: str) -> str:
    """Research agent."""
    result = chat(
        prompt=f"Research '{topic}' and provide 3 key findings.",
        system="You are a research agent.",
        max_tokens=200,
    )
    return result


@traced_agent("Writer")
def write(topic: str, research_data: str, trace_id: str, span_id: str) -> str:
    """Writer agent."""
    result = chat(
        prompt=f"Write a short article about '{topic}' using:\n{research_data}",
        system="You are a writer agent.",
        max_tokens=200,
    )
    return result


# =============================================================================
# Step 4: Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(Panel(
        "[bold]Observability Demo — Structured Logging + Trace IDs[/bold]\n\n"
        "This demo shows how to trace agent chains:\n"
        "  Coordinator → Researcher → Writer\n\n"
        "Each operation gets a span_id that links to its parent,\n"
        "creating a trace tree you can follow for debugging.",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    trace_id = str(uuid.uuid4())[:12]
    console.print(f"\n[bold]Trace ID:[/bold] {trace_id}\n")
    
    result = coordinate("AI Agent Orchestration Best Practices", trace_id=trace_id)
    
    console.print(Panel(result[:300] + "...", title="📄 Result", border_style="green"))
    
    # Show the trace tree
    trace = logger.get_trace(trace_id)
    
    table = Table(title=f"Trace: {trace_id}")
    table.add_column("Time", style="dim", width=12)
    table.add_column("Agent", style="cyan", width=15)
    table.add_column("Message", style="white", width=35)
    table.add_column("Duration", style="yellow", width=10)
    table.add_column("Span", style="dim", width=12)
    table.add_column("Parent", style="dim", width=12)
    
    for entry in trace:
        table.add_row(
            entry["timestamp"][11:23],
            entry["agent"],
            entry["message"][:35],
            f"{entry['duration_ms']:.0f}ms" if entry["duration_ms"] else "",
            entry["span_id"][:8],
            (entry["parent_span_id"][:8] if entry["parent_span_id"] else "—"),
        )
    
    console.print(table)
    
    # Show raw JSON log
    console.print("\n[bold]Raw JSON Log (first entry):[/bold]")
    console.print(json.dumps(trace[0], indent=2, default=str))
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]trace_id[/cyan] — Shared across the entire request chain\n"
        "2. [cyan]span_id[/cyan] — Unique per operation within the trace\n"
        "3. [cyan]parent_span_id[/cyan] — Links child to parent (forms a tree)\n"
        "4. [cyan]@traced_agent[/cyan] — Decorator auto-adds tracing\n"
        "5. Structured JSON logs enable search, filter, and dashboards\n\n"
        "[bold]PRODUCTION:[/bold]\n"
        "• Send logs to ELK/Datadog/CloudWatch\n"
        "• Use OpenTelemetry for standard trace format\n"
        "• Add metrics: latency percentiles, error rates",
        title="💡 Observability for Agents",
        border_style="green",
    ))
