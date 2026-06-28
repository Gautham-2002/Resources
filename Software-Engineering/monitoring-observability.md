# Monitoring & Observability

## What is Monitoring?

**Monitoring** is the practice of watching predefined metrics and signals to detect when something is wrong—and alerting the right people when thresholds are breached.

Think of it as **checking known gauges on a dashboard**: CPU above 90%, error rate above 1%, disk almost full. You decide in advance what to watch and what "bad" looks like.

### What Monitoring Answers

- Is the service **up**?
- Is latency **within SLA**?
- Are we running **out of capacity**?
- Did error rates **spike** after the last deploy?

Monitoring is **reactive by design**: you already know what questions matter, and the system tells you when answers go out of bounds.

---

## What is Observability?

**Observability** is the ability to understand the **internal state** of a system by examining its **outputs**—without needing to predict every failure mode in advance.

The term comes from control theory: if you can infer what's happening inside a black box from what it emits, the system is observable.

### What Observability Answers

- **Why** did latency spike for users in India but not the US?
- **Which** downstream service caused this checkout failure?
- **What** code path did this specific failed request take?
- **When** did this regression start, and what changed?

Observability supports **exploration and debugging** of unknown or complex problems—not just known alerts.

### Monitoring vs Observability

| Aspect       | Monitoring                        | Observability                      |
| ------------ | --------------------------------- | ---------------------------------- |
| **Focus**    | Known failure modes               | Unknown / novel problems           |
| **Approach** | Dashboards + alerts on thresholds | Rich telemetry + ad-hoc queries    |
| **Question** | "Is something broken?"            | "Why is it broken?"                |
| **Data**     | Aggregated metrics, uptime checks | Metrics + logs + traces correlated |
| **Analogy**  | Smoke alarm                       | Security camera + detective work   |

They are complementary. Production systems need **both**: monitoring to catch known issues fast, observability to investigate what monitoring cannot explain.

> See also: [cicd-devops.md](./cicd-devops.md) — observability closes the feedback loop after deployments.

---

## The Three Pillars of Observability

Most modern observability stacks are built around three signal types:

```
                    ┌─────────────────────────────────┐
                    │         Your Application         │
                    └───────────┬─────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ↓                   ↓                   ↓
      ┌──────────┐        ┌──────────┐        ┌──────────┐
      │   LOGS   │        │ METRICS  │        │  TRACES  │
      │          │        │          │        │          │
      │ Events & │        │ Numbers  │        │ Request  │
      │ messages │        │ over time│        │ journeys │
      └──────────┘        └──────────┘        └──────────┘
```

### 1. Logs

**Discrete events** with timestamps and context—what happened, when, and where.

```
2026-06-27T10:15:32Z ERROR [checkout-service] Payment failed
  request_id=abc-123 user_id=456 gateway=stripe error=card_declined
```

**Best for:** Debugging specific failures, audit trails, security investigations  
**Challenge:** High volume and cost at scale; hard to spot trends without aggregation

### 2. Metrics

**Numeric measurements** aggregated over time—counters, gauges, histograms.

```
http_requests_total{method="POST", status="500", path="/checkout"} 42
http_request_duration_seconds_bucket{le="0.5"} 980
cpu_usage_percent{host="api-1"} 73.2
```

**Best for:** Dashboards, alerts, capacity planning, trend analysis  
**Challenge:** Loses individual request detail (aggregation hides outliers)

### 3. Traces

**End-to-end paths** of a single request as it crosses services, queues, and databases.

```
[Browser] → [API Gateway] → [Order Service] → [Payment Service] → [Stripe]
   12ms          45ms              120ms              890ms
```

Each step is a **span**; the full journey is a **trace**, linked by a shared **trace ID**.

**Best for:** Latency breakdown, finding bottlenecks in microservices, understanding dependencies  
**Challenge:** Instrumentation effort; sampling needed at high traffic

### Beyond the Three Pillars

| Signal                         | What It Is                                                     | Use Case                      |
| ------------------------------ | -------------------------------------------------------------- | ----------------------------- |
| **Events**                     | Structured business or system events (deploy, scale, purchase) | Change correlation, analytics |
| **Profiles**                   | CPU/memory flame graphs per function                           | Deep performance tuning       |
| **Real User Monitoring (RUM)** | Browser/mobile performance from actual users                   | Frontend UX, Core Web Vitals  |
| **Synthetic monitoring**       | Scripted probes from external locations                        | Uptime, SLA verification      |

---

## What Gets Monitored and Observed?

### Infrastructure Layer

| What           | Examples                                     | Why It Matters                       |
| -------------- | -------------------------------------------- | ------------------------------------ |
| **Compute**    | CPU, memory, disk I/O, load average          | Capacity, noisy neighbors, OOM kills |
| **Network**    | Bandwidth, packet loss, latency, connections | Connectivity, DDoS, saturation       |
| **Storage**    | Disk usage, IOPS, latency, inode exhaustion  | Prevent outages from full disks      |
| **Containers** | Pod restarts, CPU/memory limits, OOM         | K8s health, misconfigured resources  |
| **Kubernetes** | Node status, pod scheduling, HPA, etcd       | Cluster stability                    |

### Application Layer

| What               | Examples                                         | Why It Matters                       |
| ------------------ | ------------------------------------------------ | ------------------------------------ |
| **Throughput**     | Requests per second, messages consumed           | Load patterns, scaling decisions     |
| **Latency**        | p50, p95, p99 response times                     | User experience, SLA compliance      |
| **Errors**         | HTTP 5xx rate, exception counts, failed jobs     | Reliability, deploy regressions      |
| **Saturation**     | Thread pool usage, queue depth, connection pools | Imminent failure before errors spike |
| **Business logic** | Orders/min, signups, payment success rate        | Product health, revenue impact       |

### Dependency Layer

| What               | Examples                                               |
| ------------------ | ------------------------------------------------------ |
| **Databases**      | Query latency, connections, replication lag, deadlocks |
| **Caches**         | Hit rate, evictions, memory usage (Redis, Memcached)   |
| **Message queues** | Consumer lag, DLQ depth (Kafka, RabbitMQ, SQS)         |
| **External APIs**  | Third-party latency, rate limit errors, timeouts       |
| **Load balancers** | Healthy targets, request distribution                  |

### Security & Compliance

| What                | Examples                                 |
| ------------------- | ---------------------------------------- |
| **Auth failures**   | Failed logins, token rejections          |
| **Access patterns** | Unusual API access, privilege escalation |
| **Vulnerabilities** | CVE alerts on dependencies               |
| **Audit logs**      | Who changed what, when (immutable logs)  |

### User Experience

| What                       | Examples                                 |
| -------------------------- | ---------------------------------------- |
| **Core Web Vitals**        | LCP, FID/INP, CLS (frontend performance) |
| **Apdex / satisfaction**   | % of requests below latency threshold    |
| **Geographic performance** | Latency by region                        |
| **Availability**           | Uptime from external probes (synthetic)  |

---

## Frameworks for What to Measure

### The Four Golden Signals (Google SRE)

For any user-facing service, monitor:

| Signal         | Question                   | Example Metric                  |
| -------------- | -------------------------- | ------------------------------- |
| **Latency**    | How long do requests take? | `http_request_duration_seconds` |
| **Traffic**    | How much demand is there?  | `requests_per_second`           |
| **Errors**     | What is failing?           | `error_rate`, `5xx_count`       |
| **Saturation** | How full is the system?    | `cpu_usage`, `queue_depth`      |

### RED Method (for services)

- **R**ate — requests per second
- **E**rrors — failed requests per second
- **D**uration — time per request (distribution, not just average)

### USE Method (for resources)

- **U**tilization — % time resource is busy
- **S**aturation — queue depth / extra work waiting
- **E**rrors — error count on the resource

---

## How Data Is Collected

Telemetry does not appear magically. Something in or near your system must **emit**, **collect**, **process**, and **store** it.

### The Observability Pipeline

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Generation  │ →  │  Collection  │ →  │  Processing  │ →  │   Storage    │
│  (emit data) │    │  (agents)    │    │  (parse,     │    │  (TSDB, log  │
│              │    │              │    │   enrich)    │    │   store)     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                   ↓
                    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
                    │   Alerting   │ ←  │  Querying    │ ←  │ Visualization│
                    │  (PagerDuty) │    │  (PromQL,    │    │  (Grafana)   │
                    │              │    │   LogQL)     │    │              │
                    └──────────────┘    └──────────────┘    └──────────────┘
```

### Collection Methods

#### Pull Model (Scraping)

A collector **periodically fetches** metrics from targets that expose an HTTP `/metrics` endpoint.

```
Prometheus ──scrape every 15s──→ app:8080/metrics
              ──scrape──────────→ node-exporter:9100/metrics
```

**Used by:** Prometheus, VictoriaMetrics agent  
**Pros:** Simple, collector controls scrape interval, easy service discovery  
**Cons:** Targets must be reachable; not ideal for short-lived jobs without push gateway

#### Push Model

Applications or agents **send data** to a central receiver when events occur.

```
App ──push──→ OpenTelemetry Collector ──→ backend
Fluent Bit ──push──→ Loki / Elasticsearch
StatsD client ──UDP──→ StatsD / Datadog agent
```

**Used by:** Logs (Fluentd, Fluent Bit), some metrics (StatsD), cloud agents (Datadog, CloudWatch)  
**Pros:** Works for ephemeral workloads, batch jobs, edge devices  
**Cons:** Can overwhelm receiver; need backpressure and batching

#### Agents & Sidecars

A lightweight process runs **on or beside** your application:

| Pattern        | How It Works                                                            |
| -------------- | ----------------------------------------------------------------------- |
| **Host agent** | One agent per VM/node (Datadog agent, node_exporter, Fluent Bit)        |
| **Sidecar**    | Container alongside app pod in Kubernetes (Envoy, OTel collector)       |
| **DaemonSet**  | One collector pod per K8s node (Prometheus node scraper, Fluent Bit)    |
| **eBPF**       | Kernel-level instrumentation without app changes (Pixie, Cilium Hubble) |

#### Application Instrumentation (SDKs)

Code in your app explicitly records telemetry:

```python
# OpenTelemetry example (Python)
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("process_order") as span:
    span.set_attribute("order.id", order_id)
    result = charge_payment(order)
    span.set_attribute("payment.status", result.status)
```

```javascript
// Prometheus client (Node.js) — exposes /metrics
const promClient = require("prom-client");
const httpRequestDuration = new promClient.Histogram({
  name: "http_request_duration_seconds",
  help: "Duration of HTTP requests in seconds",
  labelNames: ["method", "route", "status_code"],
});
```

#### Auto-Instrumentation

Agents inject telemetry without manual code changes:

- **Java**: Java agent (OpenTelemetry, Datadog, New Relic)
- **Python/Node/Go**: OTel auto-instrumentation packages
- **Service mesh**: Istio/Linkerd generate traces and metrics from proxy traffic

#### Log Shipping

Applications write to stdout/stderr (12-factor); infrastructure collects and forwards:

```
App → stdout → container runtime → Fluent Bit (DaemonSet) → Loki / Elasticsearch
```

Structured JSON logs are strongly preferred over unstructured plain text.

### OpenTelemetry (OTel)

**OpenTelemetry** is the vendor-neutral standard for generating and exporting telemetry. One SDK can send data to many backends.

```
┌─────────────────────────────────────────────────────────┐
│              OpenTelemetry SDK (in your app)             │
│         traces + metrics + logs (unified API)            │
└──────────────────────────┬──────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│           OpenTelemetry Collector (optional)             │
│     receive → process (filter, batch) → export           │
└──────┬──────────────┬──────────────┬────────────────────┘
       ↓              ↓              ↓
  Prometheus/     Jaeger/Tempo    Loki/Elasticsearch
  VictoriaMetrics
```

OTel is becoming the default—instrument once, switch backends without rewriting app code.

---

## Tools by Category

### Metrics

| Tool                        | Type                         | Notes                                        |
| --------------------------- | ---------------------------- | -------------------------------------------- |
| **Prometheus**              | Open-source TSDB + scraper   | De facto K8s standard; PromQL query language |
| **VictoriaMetrics**         | Prometheus-compatible TSDB   | Faster, more storage-efficient at scale      |
| **Thanos / Cortex**         | Long-term Prometheus storage | Global view, multi-cluster                   |
| **InfluxDB**                | Time-series database         | IoT, custom metrics, TICK stack              |
| **Graphite**                | Older TSDB                   | Still seen in legacy setups                  |
| **AWS CloudWatch Metrics**  | AWS-native                   | EC2, Lambda, RDS metrics built-in            |
| **Google Cloud Monitoring** | GCP-native                   | Formerly Stackdriver                         |
| **Azure Monitor**           | Azure-native                 | VMs, App Service, AKS                        |
| **Datadog**                 | SaaS full-stack              | Metrics + logs + traces + APM in one         |
| **New Relic**               | SaaS                         | Strong APM and browser monitoring            |

### Logs

| Tool                             | Type                    | Notes                                            |
| -------------------------------- | ----------------------- | ------------------------------------------------ |
| **Elasticsearch + Kibana (ELK)** | Self-hosted stack       | Elasticsearch stores; Logstash/Beats ingest      |
| **Grafana Loki**                 | Log aggregation         | Indexes labels, not full text—pairs with Grafana |
| **Fluentd / Fluent Bit**         | Log collectors/shippers | Fluent Bit is lightweight for K8s                |
| **Splunk**                       | Enterprise SaaS/on-prem | Powerful search, expensive at scale              |
| **AWS CloudWatch Logs**          | AWS-native              | Lambda, ECS, EC2 log groups                      |
| **Google Cloud Logging**         | GCP-native              | Integrated with GKE                              |
| **Papertrail / Logtail**         | Simple SaaS             | Smaller teams                                    |

### Traces & APM

| Tool              | Type                | Notes                                      |
| ----------------- | ------------------- | ------------------------------------------ |
| **Jaeger**        | Open-source tracing | CNCF project; UI for trace search          |
| **Zipkin**        | Open-source tracing | Simpler, older than Jaeger                 |
| **Grafana Tempo** | Trace backend       | Integrates with Grafana, Loki, Prometheus  |
| **AWS X-Ray**     | AWS-native tracing  | Lambda, API Gateway, ECS                   |
| **Honeycomb**     | SaaS observability  | Excellent for high-cardinality exploration |
| **Datadog APM**   | SaaS                | Auto-instrumentation, service maps         |
| **Dynatrace**     | Enterprise SaaS     | AI-assisted root cause analysis            |

### Visualization & Dashboards

This is where data becomes human-readable—graphs, tables, heatmaps, and service maps.

| Tool                      | Visualizes                     | Notes                                                      |
| ------------------------- | ------------------------------ | ---------------------------------------------------------- |
| **Grafana**               | Metrics, logs, traces, alerts  | Most popular open-source dashboard tool; multi-data-source |
| **Kibana**                | Elasticsearch logs + metrics   | Primary UI for ELK stack                                   |
| **Prometheus UI**         | Prometheus metrics only        | Built-in, basic; Grafana preferred for production          |
| **Jaeger UI**             | Traces                         | Trace timeline and dependency view                         |
| **Datadog Dashboards**    | Full-stack SaaS                | Pre-built integrations, no self-hosting                    |
| **CloudWatch Dashboards** | AWS metrics and logs           | Native AWS widgets                                         |
| **Honeycomb**             | High-cardinality events/traces | Query-driven exploration UI                                |

### Alerting & Incident Management

| Tool                           | Role                                                 |
| ------------------------------ | ---------------------------------------------------- |
| **Prometheus Alertmanager**    | Routes Prometheus alerts; grouping, silencing, dedup |
| **Grafana Alerting**           | Unified alerts across data sources                   |
| **PagerDuty**                  | On-call scheduling, escalation, incident response    |
| **Opsgenie**                   | Atlassian on-call (Jira/Confluence integration)      |
| **VictorOps / Splunk On-Call** | Incident management                                  |
| **Slack / Microsoft Teams**    | Alert notification channels                          |

### Synthetic & Uptime Monitoring

| Tool                   | Role                                        |
| ---------------------- | ------------------------------------------- |
| **Pingdom**            | External uptime checks                      |
| **UptimeRobot**        | Simple HTTP/TCP monitoring                  |
| **Datadog Synthetics** | Browser and API tests from global locations |
| **Grafana k6**         | Load testing + synthetic checks             |

---

## Where Visualization Happens: Grafana Deep Dive

**Grafana** is the most widely used open-source visualization layer. It does **not** store your data—it **queries** backends and renders dashboards.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Grafana Server                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Dashboards  │  │   Alerts    │  │  Explore (ad-hoc)   │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         └────────────────┼─────────────────────┘             │
│                          ↓                                   │
│                   Data Source Plugins                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
     ┌─────────┬───────────┼───────────┬──────────┐
     ↓         ↓           ↓           ↓          ↓
 Prometheus   Loki      Tempo/Jaeger  Elasticsearch  CloudWatch
 (metrics)   (logs)      (traces)       (logs)        (metrics)
```

### What a Grafana Dashboard Contains

| Element        | Purpose                | Example                               |
| -------------- | ---------------------- | ------------------------------------- |
| **Panel**      | Single visualization   | Line graph of p99 latency             |
| **Row**        | Groups related panels  | "API Overview" section                |
| **Variable**   | Dynamic filters        | `$environment`, `$service`, `$region` |
| **Annotation** | Mark events on graphs  | Deploy markers, incidents             |
| **Threshold**  | Visual alerts on panel | Red when error rate > 1%              |

### Common Panel Types

| Panel Type       | Best For                                          |
| ---------------- | ------------------------------------------------- |
| **Time series**  | Metrics over time (CPU, RPS, latency)             |
| **Stat / Gauge** | Single number (current error rate, uptime %)      |
| **Bar chart**    | Comparisons (errors by endpoint)                  |
| **Table**        | Top-N lists (slowest queries, noisiest endpoints) |
| **Heatmap**      | Latency distribution over time                    |
| **Logs panel**   | Live log stream from Loki                         |
| **Traces panel** | Trace list linked from metrics (exemplars)        |

### Example PromQL Queries (Grafana + Prometheus)

```promql
# Request rate (per second)
rate(http_requests_total{service="api"}[5m])

# Error rate as percentage
sum(rate(http_requests_total{status=~"5.."}[5m]))
  / sum(rate(http_requests_total[5m])) * 100

# p99 latency
histogram_quantile(0.99,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
)
```

### Correlating Signals in Grafana

Modern Grafana ties pillars together in one UI:

1. See latency spike on a **metrics** panel
2. Click an **exemplar** dot on the graph → jump to the **trace**
3. From the trace → open related **logs** with matching `trace_id`

This "metrics → traces → logs" flow is the practical definition of observability in action.

### Other Visualization Surfaces

| Surface            | Tool                       | Typical Use                              |
| ------------------ | -------------------------- | ---------------------------------------- |
| **Log search UI**  | Kibana, Grafana Explore    | Full-text search, log patterns           |
| **Trace UI**       | Jaeger, Tempo, Datadog APM | Flame graphs, service dependency maps    |
| **Service map**    | Datadog, Kiali (Istio)     | Auto-generated topology of microservices |
| **Cloud consoles** | AWS/GCP/Azure portals      | Quick native dashboards without Grafana  |
| **Terminal**       | `promtool`, `logcli`       | Debugging queries from CLI               |

---

## SLIs, SLOs, and SLAs

| Term                | Definition                     | Example                          |
| ------------------- | ------------------------------ | -------------------------------- |
| **SLI** (Indicator) | A measurable aspect of service | p99 latency, availability %      |
| **SLO** (Objective) | Target for an SLI              | 99.9% of requests < 500ms        |
| **SLA** (Agreement) | Contract with consequences     | 99.9% uptime or customer credits |
| **Error budget**    | Allowed unreliability          | 0.1% downtime ≈ 43 min/month     |

**Alert on SLO burn rate**, not raw CPU—alerts tied to user impact reduce noise.

```promql
# Example: 30-day availability SLO (simplified)
sum(rate(http_requests_total{status!~"5.."}[30d]))
  / sum(rate(http_requests_total[30d]))
```

---

## End-to-End Example Stacks

### Stack 1: Cloud-Native Open Source (Popular in Kubernetes)

```
Apps (OTel SDK) → OTel Collector → Prometheus (metrics)
                                 → Tempo (traces)
                                 → Loki (logs)
                                        ↓
                                   Grafana (dashboards + alerts)
                                        ↓
                                 Alertmanager → PagerDuty
```

### Stack 2: AWS-Native

```
App → CloudWatch Logs / X-Ray / Embedded Metrics
                    ↓
           CloudWatch Dashboards + Alarms
                    ↓
              SNS → PagerDuty / Slack
```

### Stack 3: SaaS All-in-One

```
App → Datadog Agent (or OTel → Datadog)
                    ↓
     Datadog (metrics + logs + traces + dashboards + alerts)
                    ↓
              PagerDuty / Slack
```

### Stack 4: ELK Traditional

```
App logs → Filebeat → Logstash → Elasticsearch
Metrics → Metricbeat ──────────────→ Elasticsearch
                                        ↓
                                    Kibana (dashboards)
```

---

## What Good Observability Looks Like

### Instrumentation Checklist

- [ ] Every service exposes **health** (`/health`, `/ready`) endpoints
- [ ] HTTP/gRPC requests emit **RED metrics** (rate, errors, duration)
- [ ] Logs are **structured JSON** with `trace_id`, `request_id`, `service`
- [ ] Traces propagate **context** across service boundaries (W3C Trace Context)
- [ ] Deployments tagged in metrics/logs (**version** or **git sha** label)
- [ ] Dashboards exist for **golden signals** per service
- [ ] Alerts fire on **SLO burn**, not just infrastructure thresholds
- [ ] Runbooks linked from alert notifications

### Anti-Patterns

| Anti-Pattern               | Problem                                | Fix                                                 |
| -------------------------- | -------------------------------------- | --------------------------------------------------- |
| **Alert fatigue**          | Too many low-value alerts ignored      | Alert on symptoms (user impact), not every CPU blip |
| **Unstructured logs**      | Cannot search or correlate             | JSON logs with consistent fields                    |
| **Missing trace context**  | Dead ends when debugging microservices | Propagate trace IDs across all calls                |
| **Dashboards nobody uses** | Wasted effort                          | Build from real incident questions                  |
| **No retention policy**    | Runaway storage costs                  | Tiered retention (hot 7d, warm 30d, cold 1y)        |
| **Monitoring only infra**  | App can be "green" while users fail    | Add app-level and business metrics                  |

---

## Key Terms Glossary

| Term            | Definition                                                     |
| --------------- | -------------------------------------------------------------- |
| **TSDB**        | Time-series database—optimized for timestamped numeric data    |
| **Cardinality** | Number of unique time series (high cardinality = expensive)    |
| **Exemplar**    | Link from a metric data point to a specific trace              |
| **Scrape**      | Prometheus pulling metrics from a target endpoint              |
| **Span**        | Single operation within a distributed trace                    |
| **Trace ID**    | Unique identifier linking all spans for one request            |
| **DaemonSet**   | K8s workload with one pod per node (common for log collectors) |
| **RUM**         | Real User Monitoring—browser-side performance data             |
| **Synthetic**   | Scripted probes simulating user behavior                       |
| **PromQL**      | Prometheus query language                                      |
| **LogQL**       | Loki query language                                            |

---

## Further Reading

- [Google SRE Book — Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Grafana Loki](https://grafana.com/docs/loki/latest/)
- [The Three Pillars of Observability (Cindy Sridharan)](https://www.oreilly.com/library/view/distributed-systems-observability/9781492033431/)
- [DORA Metrics](https://dora.dev/) — Reliability as a delivery capability
- [cicd-devops.md](./cicd-devops.md) — How observability fits into deployment and rollback
