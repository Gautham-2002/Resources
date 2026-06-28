# Software Development Life Cycle (SDLC)

## What is SDLC?

The **Software Development Life Cycle (SDLC)** is a structured process for planning, building, testing, deploying, and maintaining software. It defines _how_ a team moves from an idea to working software in production—and how they keep it healthy over time.

SDLC is not a single methodology. It is a **framework of phases** that different approaches (Waterfall, Agile, etc.) organize and execute in different ways.

### Why SDLC Matters

- **Predictability**: Clear stages reduce chaos on large projects
- **Quality**: Built-in review, testing, and validation steps
- **Risk management**: Problems surface earlier when phases are explicit
- **Communication**: Stakeholders share a common vocabulary (requirements, sprint, release)
- **Maintainability**: Documentation and handoff are part of the process, not afterthoughts

---

## Core Phases of SDLC

Most methodologies map work to some combination of these phases:

| Phase              | What Happens                                                       |
| ------------------ | ------------------------------------------------------------------ |
| **Planning**       | Define goals, scope, budget, timeline, and stakeholders            |
| **Requirements**   | Gather functional and non-functional needs from users and business |
| **Design**         | Architecture, data models, UI/UX, APIs, and technical decisions    |
| **Implementation** | Write code, integrate systems, configure infrastructure            |
| **Testing**        | Unit, integration, system, UAT, performance, and security testing  |
| **Deployment**     | Release to staging/production, migrations, rollout strategy        |
| **Maintenance**    | Bug fixes, monitoring, updates, scaling, and eventual retirement   |

The difference between methodologies is mainly **how linear vs. iterative** these phases are, and **how much change** is allowed mid-project.

---

## Waterfall

### Overview

Waterfall is a **sequential, phase-gated** model. Each phase must be largely complete before the next begins. Requirements are fixed early; change is expensive.

```
Requirements → Design → Implementation → Testing → Deployment → Maintenance
     ↓            ↓           ↓            ↓           ↓
  (sign-off)  (sign-off)  (sign-off)   (sign-off)  (go-live)
```

### Characteristics

- Heavy upfront documentation (SRS, design specs)
- Clear milestones and contracts
- Testing happens late in the cycle
- Best when requirements are stable and well understood

### Pros

- Simple to explain and manage
- Works well for regulated industries (finance, healthcare, government)
- Easy to estimate cost and timeline when scope is fixed
- Strong audit trail via documentation

### Cons

- Slow feedback—users see working software late
- Hard to accommodate changing requirements
- Defects found late are costly to fix
- Risk of building the wrong thing perfectly

### When to Use

- Fixed-scope projects with legal/compliance constraints
- Hardware-integrated systems with long lead times
- Projects where change is unlikely (e.g., replicating a known process)

---

## Agile

### Overview

Agile is a **mindset and family of iterative methods** defined by the [Agile Manifesto](https://agilemanifesto.org/) (2001). It values:

- Individuals and interactions over processes and tools
- Working software over comprehensive documentation
- Customer collaboration over contract negotiation
- Responding to change over following a plan

Work is delivered in **short iterations** (typically 1–4 weeks), with frequent feedback and reprioritization.

### Characteristics

- Incremental delivery of working software
- Continuous stakeholder feedback
- Embraces changing requirements
- Cross-functional teams own delivery end-to-end

### Pros

- Faster time to value
- Adapts to market and user feedback
- Reduces risk of large late-stage failures
- Higher team engagement through ownership

### Cons

- Harder to predict final cost/date without discipline
- Requires active product owner involvement
- Can drift without clear vision or architecture guardrails
- "Agile" in name only (cargo cult) often fails

### When to Use

- Product development with uncertain or evolving requirements
- Startups and SaaS products
- Teams that can collaborate closely with users

> **Note:** Scrum and Kanban are the most common _implementations_ of Agile—not separate philosophies from it.

---

## Scrum

### Overview

Scrum is the most widely used Agile framework. Work is organized into **fixed-length sprints** (usually 2 weeks), with defined roles, ceremonies, and artifacts.

### Roles

| Role              | Responsibility                                |
| ----------------- | --------------------------------------------- |
| **Product Owner** | Prioritizes backlog, defines "what" and "why" |
| **Scrum Master**  | Facilitates process, removes blockers         |
| **Developers**    | Design, build, test, and deliver increment    |

### Ceremonies

| Ceremony                 | Purpose                                                 |
| ------------------------ | ------------------------------------------------------- |
| **Sprint Planning**      | Select backlog items for the sprint; define sprint goal |
| **Daily Standup**        | Short sync: progress, plan, blockers (~15 min)          |
| **Sprint Review**        | Demo completed work to stakeholders                     |
| **Sprint Retrospective** | Team reflects and improves process                      |
| **Backlog Refinement**   | Clarify and estimate upcoming items                     |

### Artifacts

- **Product Backlog**: Ordered list of all desired work
- **Sprint Backlog**: Items committed for the current sprint
- **Increment**: Potentially shippable product at sprint end

### Pros

- Strong structure for teams new to Agile
- Regular rhythm and predictable checkpoints
- Built-in improvement loop (retrospectives)

### Cons

- Sprint boundaries can feel rigid for urgent production issues
- Requires trained Scrum Master and engaged Product Owner
- Estimation overhead (story points, velocity)

### When to Use

- Teams building features in batches with regular release cadence
- Organizations that need consistent planning rituals

---

## Kanban

### Overview

Kanban is a **flow-based** method inspired by lean manufacturing. Work moves through a visual board (To Do → In Progress → Done) with **Work In Progress (WIP) limits** to prevent overload.

Unlike Scrum, there are no fixed sprints—items are pulled when capacity allows.

### Key Practices

- Visualize the workflow
- Limit WIP per column
- Manage flow (reduce bottlenecks)
- Make policies explicit (definition of done, entry criteria)
- Improve collaboratively

### Pros

- Flexible—no sprint commitment required
- Excellent for support, ops, and continuous delivery teams
- Surfaces bottlenecks quickly
- Easy to adopt incrementally ("start where you are")

### Cons

- Less natural sprint boundary for planning/review
- Without WIP limits, it becomes "Agile theater" on a board
- Harder to forecast without metrics (cycle time, throughput)

### When to Use

- Bug triage, on-call, and maintenance work
- Teams with unpredictable incoming work
- Mature CI/CD pipelines shipping continuously

---

## Spiral Model

### Overview

The Spiral model combines **iterative development** with **explicit risk analysis**. Each "loop" of the spiral passes through planning, risk assessment, engineering, and evaluation before the next iteration.

```
        ┌─────────────────────────────┐
        │  Evaluate → Plan → Build    │
        │       ↑            ↓        │
        └───────┴── Risk Analysis ────┘
              (repeat with wider scope)
```

### Characteristics

- Risk-driven: high-risk areas are addressed early
- Prototyping is common in early spirals
- Each cycle produces a more complete product

### Pros

- Good for large, complex, or high-risk systems
- Early prototypes validate feasibility
- Flexible scope expansion over time

### Cons

- Expensive—requires risk expertise
- Hard to manage without experienced architects
- Can lack clear end date without discipline

### When to Use

- Large enterprise systems (ERP, defense, aerospace)
- Projects with significant technical or business uncertainty

---

## V-Model (Verification & Validation)

### Overview

The V-Model extends Waterfall by pairing each development phase with a corresponding **testing phase**:

```
Requirements ────────────────────────────── Acceptance Testing
     ↓                                              ↑
System Design ──────────────────────────── System Testing
     ↓                                              ↑
Architecture ───────────────────── Integration Testing
     ↓                                              ↑
Module Design ──────────────── Unit Testing
     ↓                              ↑
        Implementation (coding)
```

### Characteristics

- Testing is planned alongside development, not after
- Each level of design has a matching test level
- Still sequential—little room for mid-project change

### Pros

- Strong quality gates at every layer
- Clear traceability from requirement to test case
- Suitable for safety-critical systems

### Cons

- Same rigidity as Waterfall
- Late user feedback
- Heavy documentation burden

### When to Use

- Medical devices, automotive, avionics
- Systems where failure has severe consequences

---

## Iterative & Incremental Development

### Overview

Build the system in **repeated cycles**, each adding functionality. Early versions may be incomplete but usable (MVP approach).

### Characteristics

- Deliver working subsets early
- Refine based on feedback each iteration
- Foundation for Agile, Spiral, and many hybrid models

### Pros

- Reduces "big bang" release risk
- Users validate direction early
- Teams learn and adjust architecture over time

### Cons

- Requires discipline to avoid endless rework
- Architecture debt if iterations lack design oversight

---

## DevOps & Modern SDLC

DevOps is not a replacement for SDLC—it **extends** it by breaking down the wall between development and operations.

### Core Ideas

| Practice                                | Description                                                       |
| --------------------------------------- | ----------------------------------------------------------------- |
| **CI (Continuous Integration)**         | Merge code frequently; automated builds and tests on every change |
| **CD (Continuous Delivery/Deployment)** | Automate release pipeline to staging/production                   |
| **Infrastructure as Code**              | Version-controlled, repeatable environments                       |
| **Monitoring & Observability**          | Logs, metrics, traces feed back into development                  |
| **Shift-left security**                 | Security and quality checks early in the pipeline                 |

### How It Fits

```
Plan → Code → Build → Test → Release → Deploy → Operate → Monitor
  ↑___________________________________________________________|
                    (feedback loop)
```

Modern teams often combine **Agile/Scrum or Kanban** for planning with **DevOps** for delivery—sometimes called **DevSecOps** when security is integrated throughout.

---

## Comparison at a Glance

| Methodology   | Approach                    | Flexibility | Best For                                     |
| ------------- | --------------------------- | ----------- | -------------------------------------------- |
| **Waterfall** | Sequential phases           | Low         | Fixed scope, compliance, stable requirements |
| **Agile**     | Iterative, collaborative    | High        | Evolving products, user-driven development   |
| **Scrum**     | Time-boxed sprints          | Medium–High | Feature teams with regular releases          |
| **Kanban**    | Continuous flow             | High        | Ops, support, continuous delivery            |
| **Spiral**    | Risk-driven iterations      | Medium      | Large, high-risk, complex systems            |
| **V-Model**   | Sequential + paired testing | Low         | Safety-critical, regulated software          |
| **DevOps**    | Automation + collaboration  | High        | Fast, reliable production delivery           |

---

## Choosing the Right Approach

Ask these questions:

1. **How stable are the requirements?**  
   Stable → Waterfall/V-Model may work. Uncertain → Agile/Kanban.

2. **How critical is time-to-market?**  
   Fast feedback → Agile, Kanban, or CI/CD-heavy workflows.

3. **What is the cost of failure?**  
   High (lives, money, compliance) → V-Model, heavy testing, documentation.

4. **What does the team look like?**  
   Cross-functional product team → Scrum/Agile. Queue-driven work → Kanban.

5. **How mature is your delivery pipeline?**  
   Mature automation → Kanban + continuous deployment. Early stage → Scrum sprints with manual releases.

### Hybrid Models in Practice

Most real organizations blend approaches:

- **Scrum + Kanban (Scrumban)**: Sprints for planning, Kanban board for daily flow
- **Agile + Waterfall (Wagile)**: Waterfall for contracts/milestones, Agile sprints for execution
- **Agile + DevOps**: Sprint planning with automated CI/CD on every merge

There is no universally "best" SDLC—only the one that fits your **constraints, team, and product**.

---

## Key Terms Glossary

| Term                   | Definition                                                                                |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| **MVP**                | Minimum Viable Product—the smallest version that delivers value and validates assumptions |
| **Sprint**             | Fixed time box (usually 2 weeks) in Scrum for completing a set of work                    |
| **Backlog**            | Prioritized list of features, bugs, and technical work                                    |
| **WIP Limit**          | Maximum number of items allowed in a Kanban column at once                                |
| **UAT**                | User Acceptance Testing—validation by end users before release                            |
| **CI/CD**              | Continuous Integration / Continuous Delivery (or Deployment)                              |
| **Technical Debt**     | Shortcuts taken now that require future rework                                            |
| **Definition of Done** | Shared criteria for when a work item is truly complete                                    |

---

## Further Reading

- [Agile Manifesto](https://agilemanifesto.org/)
- [Scrum Guide](https://scrumguides.org/)
- [Kanban Guide](https://kanbanguides.org/)
- [The Phoenix Project](https://itrevolution.com/product/the-phoenix-project/) — novel illustrating DevOps principles
- [Accelerate](https://itrevolution.com/product/accelerate/) — research on high-performing software delivery
