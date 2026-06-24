# Framework Decision Guide

## Quick Decision Matrix

| Requirement | Best Framework |
|-------------|---------------|
| **OpenAI-only + multi-agent handoffs** | OpenAI Agents SDK |
| **Largest ecosystem + integrations** | LangChain |
| **Graph-based stateful workflows** | LangGraph |
| **Role-based team simulation** | CrewAI |
| **Type-safe outputs + FastAPI mindset** | Pydantic AI |
| **Google/Gemini ecosystem** | Google ADK |
| **Direct Claude API + tool use** | Anthropic SDK |

## Detailed Comparison

### Developer Experience

| Aspect | OpenAI SDK | LangChain | CrewAI | Pydantic AI | Google ADK | Anthropic |
|--------|-----------|-----------|--------|-------------|------------|-----------|
| Learning Curve | Low | High | Medium | Low | Medium | Low |
| Boilerplate | Low | Medium | Low | Low | Medium | High |
| Debugging | Great (tracing) | Medium | Medium | Good | Good (eval) | Manual |
| Docs Quality | Good | Extensive | Good | Excellent | Good | Excellent |

### Capabilities

| Feature | OpenAI SDK | LangChain | CrewAI | Pydantic AI | Google ADK | Anthropic |
|---------|-----------|-----------|--------|-------------|------------|-----------|
| Multi-Agent | ✅ Native | Via LangGraph | ✅ Native | ❌ Manual | ✅ Native | ❌ Manual |
| Tool Use | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Typed Output | ❌ | ❌ | ❌ | ✅ Native | ❌ | ❌ |
| Streaming | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| Checkpointing | ❌ | Via LangGraph | ❌ | ❌ | ✅ Session | ❌ |
| Model Agnostic | ❌ OpenAI only | ✅ Any | ✅ Any | ✅ Any | ⚠️ Gemini-first | ❌ Claude only |

### When to Choose

#### OpenAI Agents SDK
- You're already using OpenAI exclusively
- You need agent-to-agent handoffs
- You want built-in tracing/observability
- You need guardrails on agent behavior

#### LangChain
- You need integrations with many tools/services
- You're building RAG pipelines
- You want the LCEL pipe syntax
- You need memory management

#### CrewAI
- You want agents with "personalities" (roles + backstories)
- The task maps naturally to a team of people
- You prefer YAML-based configuration
- You want automatic delegation between agents

#### Pydantic AI
- You need **type-safe, validated** LLM outputs
- You're already comfortable with FastAPI/Pydantic
- You want dependency injection for testing
- You want clean, minimal code

#### Google ADK
- You're in the Google Cloud ecosystem (Vertex AI)
- You need built-in evaluation and testing
- You want sub-agent orchestration out of the box
- You plan to deploy to Cloud Run

#### Anthropic SDK
- You want direct control over the API (no abstractions)
- You're using Claude and want extended thinking
- You need the agentic loop pattern
- You want maximum flexibility with minimal magic

## Architecture Patterns per Framework

```
Simple Chain:      Pydantic AI or LangChain
Multi-Agent:       OpenAI SDK, CrewAI, or Google ADK
Stateful Graph:    LangGraph
Type-Safe Output:  Pydantic AI
RAG Pipeline:      LangChain
Direct API:        Anthropic SDK
```
