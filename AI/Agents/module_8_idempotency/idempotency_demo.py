"""
=============================================================================
MODULE 8 — DEMO: Idempotency in Agent Actions
=============================================================================
CONCEPT:
    Idempotency means: executing the same action multiple times produces
    the same result as executing it once.
    
    This is CRITICAL for agents because:
    - Network failures cause RETRIES
    - Timeouts trigger RE-EXECUTION
    - Queue consumers may process the same message twice
    
    Without idempotency, retries create DUPLICATE side effects:
    - Two CRM records for the same customer
    - Two charges on the same credit card
    - Two welcome emails to the same user

WHAT THIS DEMO DOES:
    1. Shows a NON-idempotent CRM agent (creates duplicates)
    2. Shows an IDEMPOTENT CRM agent (deduplicates using idempotency keys)
    3. Demonstrates request fingerprinting and result caching

RUN:
    python module_8_idempotency/idempotency_demo.py
=============================================================================
"""

import sys
import os
import hashlib
import json
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from shared.llm import chat

console = Console()


# =============================================================================
# Step 1: NON-Idempotent CRM Agent (The Problem)
# =============================================================================
class NonIdempotentCRM:
    """
    A CRM agent WITHOUT idempotency protection.
    
    Every call creates a NEW record, even if it's the same customer.
    If the agent retries due to a timeout, you get DUPLICATES.
    """
    
    def __init__(self):
        self.records: list[dict] = []
    
    def create_contact(self, name: str, email: str, company: str) -> dict:
        """Create a CRM contact — NO deduplication!"""
        record = {
            "id": f"CRM-{uuid.uuid4().hex[:6].upper()}",
            "name": name,
            "email": email,
            "company": company,
            "created_at": datetime.now().isoformat(),
        }
        self.records.append(record)
        return record


# =============================================================================
# Step 2: Idempotent CRM Agent (The Solution)
# =============================================================================
class IdempotentCRM:
    """
    A CRM agent WITH idempotency protection.
    
    Uses three techniques:
    1. Idempotency Key: client-provided unique ID per operation
    2. Request Fingerprint: hash of the request content
    3. Result Cache: returns cached result on duplicate requests
    """
    
    def __init__(self):
        self.records: list[dict] = []
        self._idempotency_cache: dict[str, dict] = {}   # key → result
        self._fingerprint_cache: dict[str, str] = {}     # fingerprint → idempotency_key
    
    def _compute_fingerprint(self, **kwargs) -> str:
        """
        Compute a fingerprint (hash) of the request parameters.
        
        If two requests have the same parameters, they get the same fingerprint.
        This catches duplicates even if the client forgets the idempotency key.
        """
        content = json.dumps(kwargs, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def create_contact(
        self,
        name: str,
        email: str,
        company: str,
        idempotency_key: str | None = None,
    ) -> dict:
        """
        Create a CRM contact with idempotency protection.
        
        If the same idempotency_key or fingerprint is seen again,
        return the CACHED result instead of creating a duplicate.
        """
        # Step 1: Compute request fingerprint
        fingerprint = self._compute_fingerprint(name=name, email=email, company=company)
        
        # Step 2: Check idempotency key cache
        if idempotency_key and idempotency_key in self._idempotency_cache:
            cached = self._idempotency_cache[idempotency_key]
            cached["_cached"] = True
            cached["_reason"] = "idempotency_key match"
            return cached
        
        # Step 3: Check fingerprint cache
        if fingerprint in self._fingerprint_cache:
            existing_key = self._fingerprint_cache[fingerprint]
            cached = self._idempotency_cache[existing_key]
            cached["_cached"] = True
            cached["_reason"] = "fingerprint match"
            return cached
        
        # Step 4: No match — create new record
        key = idempotency_key or str(uuid.uuid4())[:8]
        record = {
            "id": f"CRM-{uuid.uuid4().hex[:6].upper()}",
            "name": name,
            "email": email,
            "company": company,
            "created_at": datetime.now().isoformat(),
            "idempotency_key": key,
            "_cached": False,
        }
        
        self.records.append(record)
        self._idempotency_cache[key] = record
        self._fingerprint_cache[fingerprint] = key
        
        return record


# =============================================================================
# Step 3: Agent that uses the idempotent CRM
# =============================================================================
class CRMAgent:
    """
    An agent that creates CRM contacts using LLM to extract info.
    Demonstrates idempotency in action.
    """
    
    def __init__(self, crm: IdempotentCRM):
        self.crm = crm
    
    def process_inquiry(self, inquiry: str, idempotency_key: str | None = None) -> dict:
        """
        Process a customer inquiry — extract info and create CRM record.
        The idempotency key ensures retries don't create duplicates.
        """
        # Use LLM to extract contact info
        extracted = chat(
            prompt=f"""Extract the contact information from this inquiry. 
Reply with EXACTLY this JSON format:
{{"name": "...", "email": "...", "company": "..."}}

Inquiry: {inquiry}""",
            system="You are a data extraction agent. Extract contact info into JSON.",
            max_tokens=100,
            temperature=0,
        )
        
        try:
            cleaned = extracted.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            info = json.loads(cleaned.strip())
        except json.JSONDecodeError:
            info = {"name": "Unknown", "email": "unknown@example.com", "company": "Unknown"}
        
        # Create contact with idempotency protection
        result = self.crm.create_contact(
            name=info.get("name", "Unknown"),
            email=info.get("email", "unknown@example.com"),
            company=info.get("company", "Unknown"),
            idempotency_key=idempotency_key,
        )
        
        return result


# =============================================================================
# Step 4: Run the demo
# =============================================================================
if __name__ == "__main__":
    console.print(Panel(
        "[bold]Idempotency Demo[/bold]\n\n"
        "This demo shows WHY idempotency matters and HOW to implement it.\n\n"
        "Scenario: An agent creates CRM contacts from customer inquiries.\n"
        "Due to retries, the SAME request might be sent 3 times.\n\n"
        "❌ WITHOUT idempotency: 3 duplicate CRM records\n"
        "✅ WITH idempotency: Only 1 record, retries return cached result",
        title="📖 What You'll See",
        border_style="yellow",
    ))
    
    # ===== Scenario 1: WITHOUT Idempotency =====
    console.print("\n[bold red]═══ Scenario 1: WITHOUT Idempotency (The Problem) ═══[/bold red]\n")
    
    non_idem_crm = NonIdempotentCRM()
    
    # Simulate 3 retries of the same request
    for i in range(3):
        record = non_idem_crm.create_contact(
            name="Alex Johnson",
            email="alex@techcorp.com",
            company="TechCorp",
        )
        console.print(f"  Attempt {i+1}: Created record [cyan]{record['id']}[/cyan]")
    
    console.print(f"\n  [red]💥 Total records: {len(non_idem_crm.records)} (should be 1, got 3 DUPLICATES!)[/red]")
    
    # ===== Scenario 2: WITH Idempotency Key =====
    console.print("\n[bold green]═══ Scenario 2: WITH Idempotency Key (The Solution) ═══[/bold green]\n")
    
    idem_crm = IdempotentCRM()
    idempotency_key = f"req-{uuid.uuid4().hex[:8]}"
    
    for i in range(3):
        record = idem_crm.create_contact(
            name="Alex Johnson",
            email="alex@techcorp.com",
            company="TechCorp",
            idempotency_key=idempotency_key,
        )
        cached_info = "[yellow](CACHED)[/yellow]" if record.get("_cached") else "[green](NEW)[/green]"
        console.print(f"  Attempt {i+1}: {cached_info} Record [cyan]{record['id']}[/cyan]")
    
    console.print(f"\n  [green]✅ Total records: {len(idem_crm.records)} (correctly deduplicated!)[/green]")
    
    # ===== Scenario 3: Fingerprint-based dedup =====
    console.print("\n[bold blue]═══ Scenario 3: Fingerprint-Based Dedup (No Key Provided) ═══[/bold blue]\n")
    
    idem_crm2 = IdempotentCRM()
    
    # Same data but no idempotency key — fingerprint detects the duplicate
    for i in range(3):
        record = idem_crm2.create_contact(
            name="Sarah Chen",
            email="sarah@acme.com",
            company="ACME Inc",
        )
        cached_info = f"[yellow]CACHED ({record.get('_reason', '')})[/yellow]" if record.get("_cached") else "[green]NEW[/green]"
        console.print(f"  Attempt {i+1}: {cached_info} Record [cyan]{record['id']}[/cyan]")
    
    console.print(f"\n  [green]✅ Total records: {len(idem_crm2.records)} (fingerprint caught duplicates!)[/green]")
    
    # ===== Scenario 4: Full agent with LLM =====
    console.print("\n[bold magenta]═══ Scenario 4: Full Agent with LLM + Idempotency ═══[/bold magenta]\n")
    
    idem_crm3 = IdempotentCRM()
    agent = CRMAgent(idem_crm3)
    idem_key = f"inquiry-{uuid.uuid4().hex[:8]}"
    
    inquiry = "Hi, I'm Mike Thompson from GlobalTech, email mike@globaltech.io. We're interested in your AI platform."
    
    for i in range(3):
        result = agent.process_inquiry(inquiry, idempotency_key=idem_key)
        cached_info = "[yellow](CACHED)[/yellow]" if result.get("_cached") else "[green](NEW)[/green]"
        console.print(f"  Attempt {i+1}: {cached_info} → {result.get('name', 'N/A')}")
    
    console.print(f"\n  [green]✅ Total CRM records: {len(idem_crm3.records)}[/green]")
    
    # Summary
    table = Table(title="Idempotency Results")
    table.add_column("Scenario", style="cyan")
    table.add_column("Method", style="yellow")
    table.add_column("Attempts", style="white")
    table.add_column("Records Created", style="green")
    
    table.add_row("No protection", "None", "3", f"[red]3 (duplicates!)[/red]")
    table.add_row("Idempotency Key", "Client-sent key", "3", "[green]1[/green]")
    table.add_row("Fingerprint", "Content hash", "3", "[green]1[/green]")
    table.add_row("Full Agent + LLM", "Key + LLM extraction", "3", "[green]1[/green]")
    
    console.print(table)
    
    console.print(Panel(
        "[bold]KEY CONCEPTS:[/bold]\n"
        "1. [cyan]Idempotency Key[/cyan] — Unique ID per operation, sent by client\n"
        "2. [cyan]Request Fingerprint[/cyan] — Hash of request content for auto-dedup\n"
        "3. [cyan]Result Cache[/cyan] — Store and return cached results on retry\n"
        "4. Always use idempotency when agents write to external systems\n\n"
        "[bold]PRODUCTION TIPS:[/bold]\n"
        "• Store idempotency cache in Redis/DB with TTL (e.g., 24 hours)\n"
        "• Include the idempotency key in API headers (X-Idempotency-Key)\n"
        "• Log all dedup events for auditing",
        title="💡 Idempotency Pattern",
        border_style="green",
    ))
