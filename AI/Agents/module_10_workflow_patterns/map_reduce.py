"""
=============================================================================
PATTERN 7: Map-Reduce — Process Large Data in Chunks
=============================================================================
CONCEPT:
    When data is too large for a single LLM call, split it into chunks,
    process each chunk independently (MAP), then combine results (REDUCE).

    Document ──→ [Chunk 1] → Agent → Summary 1 ─┐
                 [Chunk 2] → Agent → Summary 2 ─┼→ Reducer → Final Summary
                 [Chunk 3] → Agent → Summary 3 ─┘

WHEN TO USE:
    ✅ Input exceeds LLM context window
    ✅ Processing large datasets / documents
    ✅ Multiple items need the same processing
    ❌ Items are interdependent (use Prompt Chaining)
    ❌ Small input that fits in one call

RUN:
    python module_10_workflow_patterns/map_reduce.py
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


# =============================================================================
# Step 1: Simulate a large dataset (multiple documents)
# =============================================================================
DOCUMENTS = [
    {
        "title": "AI in Healthcare",
        "content": """Artificial intelligence is transforming healthcare through improved diagnostics, 
drug discovery, and personalized treatment plans. Machine learning models can now detect 
diseases from medical images with accuracy matching or exceeding human radiologists. 
AI-powered drug discovery has reduced the time to identify potential drug candidates from 
years to months. Challenges include data privacy concerns, regulatory approval processes, 
and the need for explainable AI in clinical decision-making.""",
    },
    {
        "title": "AI in Finance",
        "content": """The financial sector has embraced AI for fraud detection, algorithmic trading, 
risk assessment, and customer service automation. AI models process millions of transactions 
in real-time to detect fraudulent activities with high precision. Algorithmic trading uses 
deep learning to predict market movements and execute trades. Robo-advisors now manage 
billions in assets, providing personalized investment advice at scale. Key concerns include 
model bias, market manipulation risks, and the need for regulatory frameworks.""",
    },
    {
        "title": "AI in Education",
        "content": """Education is being reshaped by AI through adaptive learning platforms, 
automated grading, and intelligent tutoring systems. AI can personalize learning paths 
based on individual student performance and learning styles. Natural language processing 
enables chatbot tutors that provide 24/7 homework help. AI-powered content generation 
helps teachers create customized curriculum materials. Concerns include over-reliance on 
technology, digital equity gaps, and the changing role of teachers in AI-augmented classrooms.""",
    },
    {
        "title": "AI in Manufacturing",
        "content": """Smart manufacturing leverages AI for predictive maintenance, quality control, 
supply chain optimization, and autonomous robotics. Computer vision systems inspect 
products on assembly lines with greater consistency than human inspectors. Predictive 
maintenance models analyze sensor data to forecast equipment failures before they occur, 
reducing downtime by up to 50%. AI-driven supply chain optimization helps manufacturers 
adapt to demand fluctuations and material shortages in real-time.""",
    },
]


# =============================================================================
# Step 2: MAP — Process each document independently
# =============================================================================
def map_document(doc: dict) -> dict:
    """
    MAP step: Process a single document.
    Each document is summarized independently.
    """
    console.print(f"  [cyan]📄 Mapping:[/cyan] {doc['title']}")

    summary = chat(
        prompt=f"""Summarize this document in 3 bullet points. Extract the key theme, 
main innovation, and primary challenge:

Title: {doc['title']}
Content: {doc['content']}""",
        system="You are a summarization agent. Produce concise, structured summaries.",
        max_tokens=200,
    )

    console.print(f"    [green]✅ Mapped[/green]")
    return {"title": doc["title"], "summary": summary}


# =============================================================================
# Step 3: REDUCE — Combine all map results into a final output
# =============================================================================
def reduce_summaries(mapped_results: list[dict], topic: str) -> str:
    """
    REDUCE step: Combine all individual summaries into one.
    This creates a comprehensive cross-document analysis.
    """
    console.print("\n[bold magenta]🔗 Reducing: Combining all summaries...[/bold magenta]")

    combined = "\n\n".join([
        f"### {r['title']}:\n{r['summary']}" for r in mapped_results
    ])

    result = chat(
        prompt=f"""You have summaries of {len(mapped_results)} documents about '{topic}':

{combined}

Create a unified executive summary that:
1. Identifies common themes across all sectors
2. Highlights unique innovations per sector
3. Notes shared challenges
4. Provides an overall conclusion""",
        system="You are a synthesis agent. Create comprehensive cross-document analyses.",
        max_tokens=500,
    )

    return result


# =============================================================================
# Step 4: Full Map-Reduce Pipeline
# =============================================================================
def run_map_reduce(documents: list[dict], topic: str) -> dict:
    """Execute the full map-reduce pattern."""

    # MAP phase
    console.print(
        Panel(
            f"Processing {len(documents)} documents independently...",
            title="🗺️  MAP Phase",
            border_style="blue",
        )
    )
    mapped = [map_document(doc) for doc in documents]

    # REDUCE phase
    final = reduce_summaries(mapped, topic)

    return {
        "topic": topic,
        "documents_processed": len(documents),
        "mapped_results": mapped,
        "final_summary": final,
    }


if __name__ == "__main__":
    console.print(
        Panel(
            "[bold]Pattern: Map-Reduce[/bold]\n\n"
            "Process 4 documents about AI in different industries:\n"
            "  MAP: Summarize each document independently\n"
            "  REDUCE: Combine into cross-industry analysis",
            title="📖 Map-Reduce",
            border_style="yellow",
        )
    )

    result = run_map_reduce(DOCUMENTS, "AI Adoption Across Industries")

    # Show individual maps
    for m in result["mapped_results"]:
        console.print(
            Panel(m["summary"], title=f"📄 {m['title']}", border_style="cyan")
        )

    # Show reduced result
    console.print(
        Panel(result["final_summary"], title="📋 Cross-Industry Analysis (Reduced)", border_style="green")
    )

    console.print(
        Panel(
            "[bold]KEY TAKEAWAY:[/bold]\n"
            "1. [cyan]MAP[/cyan] — Process each chunk/document independently\n"
            "2. [cyan]REDUCE[/cyan] — Combine all partial results into one\n"
            "3. [cyan]Parallelizable[/cyan] — MAP steps can run in parallel (combine with Fan-out)\n"
            "4. [cyan]Scalable[/cyan] — Works with 4 docs or 4000 docs\n\n"
            "[bold]REAL-WORLD USES:[/bold]\n"
            "• Summarize 100-page reports (chunk by section)\n"
            "• Analyze customer feedback at scale\n"
            "• Process large codebases (file-by-file analysis)\n"
            "• Multi-document Q&A (search → retrieve → synthesize)",
            title="💡 When to Use Map-Reduce",
            border_style="green",
        )
    )
