"""
=============================================================================
MODULE 1 — DEMO 2: DAG (Directed Acyclic Graph) Pattern
=============================================================================
CONCEPT:
    A DAG defines steps as NODES and dependencies as EDGES.
    Unlike a state machine, a DAG allows PARALLEL execution of independent steps.
    The execution order is determined by the dependency graph (topological sort).

    "Acyclic" means no loops — once a step is done, you don't go back to it.

WHAT THIS DEMO DOES:
    Simulates a data analysis pipeline agent:

        ┌──────────┐
        │  Fetch   │
        │  Data    │
        └────┬─────┘
             │
        ┌────▼─────┐
        │  Clean   │
        │  Data    │
        └────┬─────┘
             │
      ┌──────┴───────┐      ← These two run IN PARALLEL (independent!)
      │              │
    ┌─▼──────┐  ┌───▼────┐
    │Analyze │  │Analyze │
    │Trends  │  │Outliers│
    └──┬─────┘  └───┬────┘
       │            │
       └──────┬─────┘
              │
        ┌─────▼────┐
        │ Generate │
        │ Report   │
        └──────────┘

RUN:
    python module_1_orchestration_patterns/dag_demo.py
=============================================================================
"""

import sys
import os
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: Build a simple DAG executor
# =============================================================================
class DAGNode:
    """A single node in the DAG."""

    def __init__(self, name: str, func, dependencies: list[str] = None):
        self.name = name
        self.func = func  # The function to execute
        self.dependencies = dependencies or []
        self.result = None
        self.status = "pending"
        self.duration_ms = 0


class DAGExecutor:
    """
    A simple DAG executor that:
    1. Topologically sorts nodes based on dependencies
    2. Executes them in the correct order
    3. Passes outputs from dependencies as inputs to dependents

    KEY INSIGHT: The executor figures out what can run in parallel (independent nodes)
    and what must wait (nodes with unmet dependencies).
    """

    def __init__(self):
        self.nodes: dict[str, DAGNode] = {}
        self.execution_log: list[str] = []

    def add_node(self, name: str, func, dependencies: list[str] = None):
        """Add a node to the DAG."""
        self.nodes[name] = DAGNode(name, func, dependencies)

    def _topological_sort(self) -> list[list[str]]:
        """
        Sort nodes into execution LEVELS.
        Nodes in the same level have no dependencies on each other
        and CAN run in parallel.

        Returns: [[level0_nodes], [level1_nodes], ...]
        """
        in_degree = {name: 0 for name in self.nodes}
        dependents = defaultdict(list)

        for name, node in self.nodes.items():
            for dep in node.dependencies:
                dependents[dep].append(name)
                in_degree[name] += 1

        # Start with nodes that have no dependencies
        levels = []
        current_level = [n for n, d in in_degree.items() if d == 0]

        while current_level:
            levels.append(current_level)
            next_level = []
            for name in current_level:
                for dependent in dependents[name]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_level.append(dependent)
            current_level = next_level

        return levels

    def execute(self) -> dict:
        """Execute the DAG in topological order."""
        levels = self._topological_sort()
        results = {}

        console.print(
            Panel(
                f"Execution plan: {len(levels)} levels, {len(self.nodes)} total nodes",
                title="📊 DAG Executor",
                border_style="blue",
            )
        )

        for level_idx, level in enumerate(levels):
            parallel_note = (
                " [bold yellow](can run in parallel!)[/bold yellow]"
                if len(level) > 1
                else ""
            )
            console.print(
                f"\n[bold]Level {level_idx}:[/bold] {', '.join(level)}{parallel_note}"
            )

            for node_name in level:
                node = self.nodes[node_name]

                # Collect results from dependencies
                dep_results = {dep: results[dep] for dep in node.dependencies}

                console.print(f"  ▶ Running: [cyan]{node_name}[/cyan]")
                start = time.time()

                try:
                    node.result = node.func(dep_results)
                    node.status = "completed"
                    node.duration_ms = (time.time() - start) * 1000
                    results[node_name] = node.result
                    console.print(
                        f"  ✅ [green]{node_name}[/green] completed in {node.duration_ms:.0f}ms"
                    )
                    self.execution_log.append(
                        f"Level {level_idx}: {node_name} ✅ ({node.duration_ms:.0f}ms)"
                    )
                except Exception as e:
                    node.status = "failed"
                    node.duration_ms = (time.time() - start) * 1000
                    console.print(f"  ❌ [red]{node_name}[/red] failed: {e}")
                    self.execution_log.append(
                        f"Level {level_idx}: {node_name} ❌ ({e})"
                    )
                    raise

        return results


# =============================================================================
# Step 2: Define the agent tasks (each node is an LLM-powered step)
# =============================================================================
SAMPLE_DATA = """
Monthly Sales Data (2024):
Jan: $45,000 | Feb: $52,000 | Mar: $48,000 | Apr: $61,000
May: $55,000 | Jun: $90,000 | Jul: $42,000 | Aug: $58,000
Sep: $63,000 | Oct: $71,000 | Nov: $150,000 | Dec: $180,000
"""


def fetch_data(deps: dict) -> str:
    """Simulate fetching data (no dependencies)."""
    result = chat(
        prompt=f"You received this raw sales data. Acknowledge it and format it as a clean list:\n{SAMPLE_DATA}",
        system="You are a data fetching agent. Format the data cleanly.",
        max_tokens=200,
    )
    return result


def clean_data(deps: dict) -> str:
    """Clean and normalize the fetched data (depends on: fetch_data)."""
    raw_data = deps["fetch_data"]
    result = chat(
        prompt=f"Clean and normalize this data. Identify any anomalies:\n{raw_data}",
        system="You are a data cleaning agent. Normalize and flag anomalies.",
        max_tokens=200,
    )
    return result


def analyze_trends(deps: dict) -> str:
    """Analyze trends in the cleaned data (depends on: clean_data)."""
    clean = deps["clean_data"]
    result = chat(
        prompt=f"Analyze the trends in this cleaned data. Identify growth patterns, seasonality, etc.:\n{clean}",
        system="You are a trend analysis agent. Find patterns in the data.",
        max_tokens=200,
    )
    return result


def analyze_outliers(deps: dict) -> str:
    """Find outliers in the cleaned data (depends on: clean_data, PARALLEL with analyze_trends!)."""
    clean = deps["clean_data"]
    result = chat(
        prompt=f"Identify outliers and anomalies in this data. Which months are unusually high or low?:\n{clean}",
        system="You are an outlier detection agent. Find unusual data points.",
        max_tokens=200,
    )
    return result


def generate_report(deps: dict) -> str:
    """Generate final report (depends on: analyze_trends AND analyze_outliers)."""
    trends = deps["analyze_trends"]
    outliers = deps["analyze_outliers"]
    result = chat(
        prompt=f"Generate a brief executive summary combining these analyses:\n\nTrends:\n{trends}\n\nOutliers:\n{outliers}",
        system="You are a report generation agent. Create concise executive summaries.",
        max_tokens=300,
    )
    return result


# =============================================================================
# Step 3: Build and run the DAG
# =============================================================================
def visualize_dag():
    """Show the DAG structure as a tree."""
    tree = Tree("📊 Data Analysis Pipeline (DAG)")

    fetch = tree.add("1️⃣  fetch_data (no dependencies)")
    clean = fetch.add("2️⃣  clean_data (depends on: fetch)")

    parallel = clean.add("⚡ PARALLEL BRANCH:")
    parallel.add("3a️⃣  analyze_trends (depends on: clean)")
    parallel.add("3b️⃣  analyze_outliers (depends on: clean)")

    parallel.add("4️⃣  generate_report (depends on: trends + outliers)")

    console.print(tree)


if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]DAG Pattern Demo[/bold]\n\n"
            "This demo shows a data analysis pipeline using a DAG.\n"
            "Steps run in DEPENDENCY ORDER — independent steps CAN run in parallel.\n"
            "The key difference from a state machine: the GRAPH determines execution order.",
            title="📖 What You'll See",
            border_style="yellow",
        )
    )

    # Show the DAG structure
    print()
    visualize_dag()
    print()

    # Build the DAG
    dag = DAGExecutor()
    dag.add_node("fetch_data", fetch_data)
    dag.add_node("clean_data", clean_data, dependencies=["fetch_data"])
    dag.add_node("analyze_trends", analyze_trends, dependencies=["clean_data"])
    dag.add_node("analyze_outliers", analyze_outliers, dependencies=["clean_data"])
    dag.add_node(
        "generate_report",
        generate_report,
        dependencies=["analyze_trends", "analyze_outliers"],
    )

    # Execute
    results = dag.execute()

    # Show final report
    console.print(
        Panel(
            results["generate_report"],
            title="📋 Final Report",
            border_style="green",
        )
    )

    # Show execution log
    console.print("\n[bold]Execution Log:[/bold]")
    for entry in dag.execution_log:
        console.print(f"  → {entry}")

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "✅ DAGs allow PARALLEL execution of independent steps\n"
            "✅ Dependencies are explicit — easy to reason about\n"
            "✅ Great for data pipelines and multi-step processing\n"
            "❌ No loops — can't iterate or go back\n"
            "❌ Structure is fixed at design time (like state machines)",
            title="💡 When to Use DAGs",
            border_style="green",
        )
    )
