"""
=============================================================================
PATTERN 8: Handoff — Agent-to-Agent Delegation
=============================================================================
CONCEPT:
    An agent recognizes it can't handle a task and HANDS OFF to a
    more specialized agent, passing along context and conversation state.

    Unlike the Router (which classifies at the start), Handoff happens
    MID-CONVERSATION when the current agent reaches its limits.

    Triage Agent → "This needs billing expertise" → Billing Agent
                 → "This needs technical help"   → Technical Agent

WHEN TO USE:
    ✅ Agents have different specializations
    ✅ The right specialist isn't known until mid-conversation
    ✅ Context must be preserved across the handoff
    ❌ You know the route upfront (use Router)
    ❌ All agents need to see all input (use Fan-out)

RUN:
    python module_10_workflow_patterns/handoff_pattern.py
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
# Step 1: Define agent registry
# =============================================================================
class AgentRegistry:
    """Registry of available agents for handoff."""

    def __init__(self):
        self.agents: dict[str, dict] = {}

    def register(self, name: str, description: str, system_prompt: str):
        self.agents[name] = {
            "name": name,
            "description": description,
            "system_prompt": system_prompt,
        }

    def get_agent_descriptions(self) -> str:
        return "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.agents.items()
        ])


# =============================================================================
# Step 2: Triage Agent — decides who handles the request
# =============================================================================
class TriageAgent:
    """
    The TRIAGE agent handles initial contact and decides whether
    to handle the request itself or HAND OFF to a specialist.

    KEY INSIGHT: Unlike a Router (which classifies upfront), the Triage
    agent may do some initial processing before deciding to hand off.
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.conversation_history: list[dict] = []

    def process(self, user_message: str) -> dict:
        """Process a message — handle directly or hand off."""
        self.conversation_history.append({"role": "user", "content": user_message})

        agent_list = self.registry.get_agent_descriptions()

        result = chat(
            prompt=f"""You are a triage agent. A user sent this message:

"{user_message}"

You can either:
1. Handle it yourself (for simple greetings or general questions)
2. Hand off to a specialist agent

Available specialists:
{agent_list}

Reply in JSON:
{{"action": "handle" or "handoff", "target_agent": "agent_name or null", "reasoning": "why", "initial_response": "your response or context summary for the next agent"}}""",
            system="You are a triage agent. Decide whether to handle requests or delegate to specialists. Reply with valid JSON only.",
            max_tokens=200,
            temperature=0,
        )

        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            decision = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            decision = {
                "action": "handle",
                "target_agent": None,
                "reasoning": "Could not parse decision",
                "initial_response": "I'll help you with that.",
            }

        return decision


# =============================================================================
# Step 3: Specialist Agent — handles the handoff
# =============================================================================
def specialist_handle(agent_info: dict, user_message: str, context: str) -> str:
    """
    A specialist agent handles the request after receiving the handoff.

    KEY: It receives CONTEXT from the triage agent, so the user
    doesn't have to repeat themselves.
    """
    console.print(f"  [green]🤝 Handoff received by: {agent_info['name']}[/green]")
    console.print(f"  [dim]Context from triage: {context[:80]}...[/dim]")

    return chat(
        prompt=f"""Previous agent context: {context}

User's original request: {user_message}

Handle this request with your expertise. Provide a thorough, helpful response.""",
        system=agent_info["system_prompt"],
        max_tokens=400,
    )


# =============================================================================
# Step 4: Full Handoff Pipeline
# =============================================================================
def run_handoff(user_message: str, registry: AgentRegistry) -> dict:
    """Execute the full handoff pattern."""
    console.print(
        Panel(f"User: {user_message}", title="📨 Incoming Request", border_style="blue")
    )

    triage = TriageAgent(registry)
    decision = triage.process(user_message)

    action = decision.get("action", "handle")
    target = decision.get("target_agent")
    reasoning = decision.get("reasoning", "")
    context = decision.get("initial_response", "")

    console.print(f"  [bold]🏷️  Triage Decision:[/bold] {action}")
    console.print(f"  [dim]Reasoning: {reasoning}[/dim]")

    if action == "handoff" and target and target in registry.agents:
        agent_info = registry.agents[target]
        response = specialist_handle(agent_info, user_message, context)
        handled_by = target
    else:
        response = context or "I can help you with that. How can I assist?"
        handled_by = "triage"

    return {
        "user_message": user_message,
        "triage_decision": action,
        "target_agent": target,
        "reasoning": reasoning,
        "handled_by": handled_by,
        "response": response,
    }


# =============================================================================
# Step 5: Run the demo
# =============================================================================
TEST_MESSAGES = [
    "I was charged twice for my subscription last month, can I get a refund?",
    "How do I configure SSL certificates for my Kubernetes cluster?",
    "Hi, what can you help me with?",
    "Our annual contract is up for renewal and we want to discuss enterprise pricing",
]

if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Pattern: Handoff[/bold]\n\n"
            "A Triage agent receives requests and decides:\n"
            "  • Handle itself (simple queries)\n"
            "  • Hand off to Billing Agent\n"
            "  • Hand off to Technical Agent\n"
            "  • Hand off to Sales Agent\n\n"
            "Context is preserved across the handoff.",
            title="📖 Handoff Pattern",
            border_style="yellow",
        )
    )

    # Set up specialist registry
    registry = AgentRegistry()
    registry.register(
        "billing_agent",
        "Handles billing, payments, refunds, invoices, and subscription issues",
        "You are a billing specialist. Handle payment issues, refunds, and billing questions with empathy and precision.",
    )
    registry.register(
        "technical_agent",
        "Handles technical issues, debugging, configuration, and DevOps questions",
        "You are a senior technical support engineer. Provide detailed technical guidance with specific steps and commands.",
    )
    registry.register(
        "sales_agent",
        "Handles pricing, contracts, enterprise plans, and sales inquiries",
        "You are an enterprise sales agent. Be consultative, understand needs, and provide tailored solutions.",
    )

    results = []
    for msg in TEST_MESSAGES:
        r = run_handoff(msg, registry)
        results.append(r)

    # Summary
    table = Table(title="Handoff Pattern Results")
    table.add_column("User Message", style="white", width=35)
    table.add_column("Decision", style="cyan", width=10)
    table.add_column("Handled By", style="yellow", width=15)
    table.add_column("Response Preview", style="dim", width=30)

    for r in results:
        table.add_row(
            r["user_message"][:35],
            r["triage_decision"],
            r["handled_by"],
            r["response"][:30] + "...",
        )

    console.print(table)

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "1. [cyan]Triage first[/cyan] — initial agent does preliminary assessment\n"
            "2. [cyan]Context transfer[/cyan] — specialist receives triage context\n"
            "3. [cyan]Dynamic routing[/cyan] — decision made mid-conversation\n"
            "4. [cyan]Graceful fallback[/cyan] — triage handles simple cases itself\n\n"
            "[bold]HANDOFF vs ROUTER:[/bold]\n"
            "• Router: classifies input BEFORE processing\n"
            "• Handoff: triage does initial work, then delegates if needed\n"
            "• Handoff preserves conversation context across agents",
            title="💡 When to Use Handoff",
            border_style="green",
        )
    )
