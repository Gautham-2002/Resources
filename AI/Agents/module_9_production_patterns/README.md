# Module 9: Production Patterns

## Making Agent Systems Production-Ready

These patterns are essential for reliable, observable, and well-behaved agent systems.

### Demos

1. **Retry + Circuit Breaker** — `python module_9_production_patterns/retry_circuit_breaker.py`
   - Exponential backoff with jitter
   - Circuit breaker that opens after N failures

2. **Observability** — `python module_9_production_patterns/observability_demo.py`
   - Structured JSON logging with correlation/trace IDs
   - Track agent chains across multiple steps

3. **Rate Limiter** — `python module_9_production_patterns/rate_limiter_demo.py`
   - Token bucket algorithm
   - Prevents agent storms on downstream APIs
