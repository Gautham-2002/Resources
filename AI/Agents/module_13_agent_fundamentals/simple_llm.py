"""
=============================================================================
MODULE 13 — DEMO 0: Simple LLM Call
=============================================================================
CONCEPT:
    The simplest possible LLM interaction — a single call, no loop,
    no tools, no decisions. Just prompt in, response out.

    This is the foundation everything else builds on.

RUN:
    python module_13_agent_fundamentals/simple_llm.py
=============================================================================
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.llm import chat


# Single call, no loop, no decisions
result = chat("Summarise the French Revolution in 3 sentences.")
print(result)
