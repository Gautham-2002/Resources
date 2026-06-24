# Module 2: LangGraph Deep Dive

## Core Primitives of LangGraph

LangGraph is a library for building stateful, multi-step agent workflows as graphs.

### Key Concepts

| Concept | What It Is | Analogy |
|---------|-----------|---------|
| **State** | The shared data that flows through the graph | A whiteboard everyone can read/write |
| **Node** | A function that reads/writes state | A worker at a station |
| **Edge** | A connection between nodes | A conveyor belt |
| **Conditional Edge** | An edge that routes based on state | A switch on the conveyor |
| **Subgraph** | A graph nested inside another graph | A department within a company |

### Demos

1. **Basic Graph** — `python module_2_langgraph_deepdive/basic_graph.py`
   - Build a 3-node graph: research → analyze → write
   - Understand `StateGraph`, `TypedDict`, `add_node`, `add_edge`

2. **Conditional Routing** — `python module_2_langgraph_deepdive/conditional_routing.py`
   - Classify queries → route to specialist agents
   - `add_conditional_edges` with routing functions

3. **Subgraphs** — `python module_2_langgraph_deepdive/subgraph_demo.py`
   - Compose complex workflows from smaller, reusable graphs
   - Main graph delegates to research and writing subgraphs
