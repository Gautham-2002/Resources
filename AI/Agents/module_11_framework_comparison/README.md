# Module 11: Framework Comparison

## Same Task, Different Frameworks

Every demo implements the **same use case**: a multi-step research agent that:
1. Researches a topic
2. Analyzes findings
3. Writes a report

This lets you feel the difference in **developer experience** across frameworks.

### Demos

| Framework | File | Install | Key Differentiator |
|-----------|------|---------|-------------------|
| **OpenAI Agents SDK** | `openai_agents_demo.py` | `pip install openai-agents` | Handoffs, guardrails, tracing |
| **LangChain** | `langchain_demo.py` | `pip install langchain langchain-openai` | Largest ecosystem, chains |
| **CrewAI** | `crewai_demo.py` | `pip install crewai` | Role-based crews, YAML config |
| **Pydantic AI** | `pydantic_ai_demo.py` | `pip install pydantic-ai` | Type-safe, dependency injection |
| **Google ADK** | `google_adk_demo.py` | `pip install google-adk` | Google ecosystem, multi-agent |
| **Anthropic SDK** | `anthropic_sdk_demo.py` | `pip install anthropic` | Claude tool use, streaming |

### Decision Guide: `framework_comparison.md`

A detailed decision matrix covering when to pick each framework based on your requirements.

### Run Any Demo

```bash
python module_11_framework_comparison/openai_agents_demo.py
python module_11_framework_comparison/langchain_demo.py
# ... etc
```

### API Keys Required

| Framework | API Key Env Var |
|-----------|----------------|
| OpenAI Agents SDK | `OPENAI_API_KEY` |
| LangChain | `OPENAI_API_KEY` |
| CrewAI | `OPENAI_API_KEY` |
| Pydantic AI | `OPENAI_API_KEY` |
| Google ADK | `GOOGLE_API_KEY` |
| Anthropic SDK | `ANTHROPIC_API_KEY` |
