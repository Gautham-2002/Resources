# CI/CD & DevOps: From Concepts to Deployment Strategies

## What is DevOps?

**DevOps** is a culture and set of practices that unites **development (Dev)** and **operations (Ops)** so software can be built, tested, and released faster and more reliably.

It is not a single tool or job title. It is about:

- **Collaboration**: Developers and ops share responsibility for production
- **Automation**: Repeatable builds, tests, and deployments instead of manual steps
- **Feedback loops**: Monitoring and incidents inform the next development cycle
- **Small, frequent changes**: Reduce risk per release instead of rare "big bang" deploys

### DevOps vs Traditional IT

| Traditional                            | DevOps                                  |
| -------------------------------------- | --------------------------------------- |
| Dev throws code "over the wall" to Ops | Shared ownership of delivery and uptime |
| Manual server setup and deploys        | Infrastructure as Code (IaC)            |
| Releases are rare and stressful        | Frequent, automated releases            |
| Incidents blamed on individuals        | Blameless postmortems, systemic fixes   |

### The DevOps Lifecycle

```
Plan → Code → Build → Test → Release → Deploy → Operate → Monitor
  ↑___________________________________________________________|
                    (continuous feedback)
```

**CI/CD** is the automation backbone of DevOps—the pipelines that turn a git commit into running software in production.

> See also: [sdlc-methodologies.md](./sdlc-methodologies.md) for how Agile, Scrum, and Kanban fit into the broader software delivery process.

---

## What is CI (Continuous Integration)?

### Definition

**Continuous Integration (CI)** is the practice of merging code changes into a shared branch **frequently** (often multiple times per day), with each merge triggering an **automated build and test pipeline**.

The goal: catch integration bugs, broken builds, and regressions **early**—when they are cheap to fix.

### What Happens in a CI Pipeline

A typical CI run, triggered by a pull request or push to `main`:

```
Developer pushes code
        ↓
   Trigger CI pipeline
        ↓
┌───────────────────────────────────┐
│ 1. Checkout code                  │
│ 2. Install dependencies           │
│ 3. Lint / static analysis         │
│ 4. Compile / build artifacts      │
│ 5. Run unit tests                 │
│ 6. Run integration tests          │
│ 7. Security scan (SAST)           │
│ 8. Report status (pass / fail)    │
└───────────────────────────────────┘
        ↓
  Merge blocked if CI fails
```

### Core CI Principles

1. **Single source of truth**: All code lives in version control (Git)
2. **Automate the build**: One command reproduces the build anywhere
3. **Automate tests**: No manual "smoke test before merge"
4. **Fix broken builds immediately**: A red main branch blocks everyone
5. **Fast feedback**: Pipelines should complete in minutes, not hours

### CI Example: Node.js Project

A minimal GitHub Actions workflow that runs on every pull request:

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"

      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build
```

What this does:

- **`npm ci`**: Clean install from lockfile (reproducible)
- **`lint`**: Catches style and some logic issues
- **`test`**: Unit and integration tests
- **`build`**: Verifies the app compiles for production

### CI Example: Python Project

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check .
      - run: pytest --cov=src
      - run: mypy src/
```

### CI Example: Docker Image Build

CI can also verify that container images build correctly:

```yaml
jobs:
  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Run container smoke test
        run: |
          docker run -d --name app -p 8080:8080 myapp:${{ github.sha }}
          sleep 5
          curl -f http://localhost:8080/health
```

### What CI Is NOT

- **Not CD**: CI validates code; it does not necessarily deploy to production
- **Not optional tests**: A pipeline that only builds without testing is incomplete CI
- **Not "run tests locally sometimes"**: CI must run automatically on every change

---

## CI Tools & Frameworks

| Tool                       | Type                          | Notes                                                                   |
| -------------------------- | ----------------------------- | ----------------------------------------------------------------------- |
| **GitHub Actions**         | Cloud CI/CD (GitHub-native)   | YAML workflows, huge marketplace of actions, free tier for public repos |
| **GitLab CI/CD**           | Built into GitLab             | `.gitlab-ci.yml`, strong for self-hosted and full DevOps platform       |
| **Jenkins**                | Self-hosted, plugin-based     | Highly customizable, widely used in enterprises; requires maintenance   |
| **CircleCI**               | Cloud CI                      | Fast, Docker-first, good monorepo support                               |
| **Travis CI**              | Cloud CI                      | Historically popular for open source                                    |
| **Azure DevOps Pipelines** | Microsoft ecosystem           | YAML or classic UI, integrates with Azure and GitHub                    |
| **Bitbucket Pipelines**    | Atlassian ecosystem           | Built into Bitbucket                                                    |
| **Buildkite**              | Hybrid (agents you host)      | Flexible for large orgs with custom infra                               |
| **Drone CI**               | Self-hosted, container-native | Lightweight, pipeline-as-code                                           |
| **TeamCity**               | JetBrains, self-hosted        | Strong for Java/Kotlin shops                                            |

### Supporting Tools (Often Used Inside CI)

| Category                   | Examples                                          |
| -------------------------- | ------------------------------------------------- |
| **Linting**                | ESLint, Ruff, golangci-lint, RuboCop              |
| **Testing**                | Jest, Pytest, Go test, JUnit, Cypress, Playwright |
| **Coverage**               | Istanbul/nyc, Coverage.py, Codecov, SonarQube     |
| **Security (SAST)**        | Snyk, Semgrep, Trivy, Dependabot                  |
| **Artifact storage**       | GitHub Packages, Artifactory, Nexus, ECR, GCR     |
| **Monorepo orchestration** | Nx, Turborepo, Bazel                              |

### Choosing a CI Platform

| Factor                   | Consideration                                                       |
| ------------------------ | ------------------------------------------------------------------- |
| **Where is your code?**  | GitHub → Actions is natural; GitLab → GitLab CI                     |
| **Self-hosted vs cloud** | Jenkins/Drone for control; Actions/CircleCI for simplicity          |
| **Compliance**           | Some industries require on-prem runners                             |
| **Cost**                 | Cloud CI bills by minutes; self-hosted bills by infra + maintenance |
| **Ecosystem**            | Match your cloud (AWS CodeBuild, Google Cloud Build, etc.)          |

---

## What is CD (Continuous Delivery / Continuous Deployment)?

CD has two related meanings. Both extend CI; the difference is **how automated the final step to production is**.

### Continuous Delivery

**Continuous Delivery** means every change that passes CI is **automatically prepared for release**—built, tested, and staged—so production deploy is a **manual, low-risk decision** (e.g., click "Deploy" or merge to a release branch).

```
Code → CI (build + test) → Staging deploy → [Human approves] → Production
```

- Production-ready artifacts exist after every green pipeline
- Release timing is a business decision, not a technical bottleneck
- Rollback plans and change windows still possible

### Continuous Deployment

**Continuous Deployment** goes further: every change that passes all automated checks is **automatically deployed to production** with no human gate.

```
Code → CI (build + test) → Production deploy (automatic)
```

- Requires very high test confidence and strong observability
- Used by mature teams (e.g., Netflix, Etsy-style cultures)
- Not every organization needs or wants this

### CD Pipeline Stages (Typical)

```
┌─────────┐   ┌─────────┐   ┌──────────┐   ┌────────────┐   ┌────────────┐
│  Build  │ → │  Test   │ → │  Stage   │ → │  Approve   │ → │ Production │
│ artifact│   │ (full)  │   │  deploy  │   │ (optional) │   │   deploy   │
└─────────┘   └─────────┘   └──────────┘   └────────────┘   └────────────┘
```

Common CD steps beyond CI:

- Build and push Docker image to a registry
- Deploy to staging / preview environment
- Run end-to-end (E2E) tests against staging
- Database migrations (with safeguards)
- Production deploy using a chosen strategy (see below)
- Smoke tests and health checks post-deploy
- Notify team (Slack, PagerDuty)

### CD Example: Deploy to Kubernetes (GitHub Actions)

```yaml
# Simplified CD job — runs after CI passes on main
jobs:
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to ECR
        run: aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY

      - name: Build and push image
        run: |
          docker build -t $ECR_REGISTRY/myapp:${{ github.sha }} .
          docker push $ECR_REGISTRY/myapp:${{ github.sha }}

      - name: Deploy to EKS
        run: |
          kubectl set image deployment/myapp \
            myapp=$ECR_REGISTRY/myapp:${{ github.sha }}
          kubectl rollout status deployment/myapp
```

### CD Tools & Platforms

| Tool                              | Role                                           |
| --------------------------------- | ---------------------------------------------- |
| **GitHub Actions / GitLab CI**    | CI + CD in one YAML pipeline                   |
| **Argo CD**                       | GitOps — syncs Kubernetes state from Git repos |
| **Flux**                          | GitOps controller for Kubernetes               |
| **Spinnaker**                     | Multi-cloud CD platform (Netflix-origin)       |
| **Harness**                       | Enterprise CD with verification and rollback   |
| **Octopus Deploy**                | Release orchestration, strong for .NET         |
| **AWS CodeDeploy / CodePipeline** | AWS-native deployment automation               |
| **Google Cloud Deploy**           | Managed CD for GKE and Cloud Run               |
| **Heroku / Vercel / Netlify**     | Platform CD for web apps (git push → deploy)   |
| **Terraform / Pulumi**            | Infrastructure changes as part of CD           |

### GitOps

**GitOps** is a CD pattern where **Git is the source of truth** for both application code and deployment config. A controller (e.g., Argo CD) continuously reconciles the cluster to match the repo.

```
Developer merges PR → Git repo updated → Argo CD detects drift → Applies to cluster
```

Benefits: auditable history, easy rollback (`git revert`), consistent environments.

---

## CI/CD Pipeline Anatomy

A full pipeline often looks like this:

```
                    ┌─────────────────────────────────────────┐
                    │              CI Phase                    │
  Git Push/PR  ──→  │  lint → unit tests → build artifact     │
                    └──────────────────┬──────────────────────┘
                                       ↓
                    ┌─────────────────────────────────────────┐
                    │              CD Phase                    │
                    │  push image → deploy staging → E2E      │
                    │       → deploy prod (strategy)          │
                    └──────────────────┬──────────────────────┘
                                       ↓
                    ┌─────────────────────────────────────────┐
                    │           Post-deploy                    │
                    │  health checks → metrics → alerts       │
                    └─────────────────────────────────────────┘
```

### Key Concepts

| Concept            | Meaning                                                          |
| ------------------ | ---------------------------------------------------------------- |
| **Pipeline**       | Automated sequence of stages (build, test, deploy)               |
| **Stage**          | Logical group of steps (e.g., "Test", "Deploy")                  |
| **Job**            | Runnable unit, often parallelized (e.g., test on Node 18 and 20) |
| **Artifact**       | Output of a build (JAR, Docker image, static files)              |
| **Runner / Agent** | Machine that executes pipeline steps                             |
| **Environment**    | Named target (dev, staging, production) with secrets and config  |
| **Gate**           | Approval or condition before proceeding (manual or automated)    |

### Branch Strategies and CI/CD

| Strategy                 | CI/CD Behavior                                                     |
| ------------------------ | ------------------------------------------------------------------ |
| **Trunk-based**          | Every commit to `main` runs full CI; CD deploys from `main`        |
| **GitFlow**              | CI on feature branches; CD from `release/*` or `main`              |
| **Environment branches** | `develop` → staging, `main` → production                           |
| **PR previews**          | CI builds ephemeral env per pull request (Vercel, Netlify pattern) |

---

## Deployment Strategies

How you roll out a new version to production matters as much as how you build it. Different strategies trade off **speed**, **risk**, **cost**, and **complexity**.

### Comparison Overview

| Strategy          | Downtime | Risk     | Rollback Speed | Infra Cost | Complexity |
| ----------------- | -------- | -------- | -------------- | ---------- | ---------- |
| **Recreate**      | Yes      | High     | Slow           | Low        | Low        |
| **Rolling**       | No\*     | Medium   | Medium         | Low        | Low        |
| **Blue-Green**    | Minimal  | Low      | Fast           | High (2x)  | Medium     |
| **Canary**        | No       | Low      | Fast           | Medium     | High       |
| **A/B Testing**   | No       | Low      | Fast           | Medium     | High       |
| **Feature Flags** | No       | Very Low | Instant        | Low        | Medium     |

\*Rolling can cause brief issues if health checks are misconfigured.

---

### 1. Recreate (Big Bang)

Stop the old version entirely, then start the new version.

```
[ v1 running ]  →  [ nothing ]  →  [ v2 running ]
```

**How it works:**

- Scale old deployment to zero
- Deploy new version
- Simplest possible approach

**Pros:** Simple, no extra infrastructure  
**Cons:** Downtime during switch; users see errors; risky for production

**When to use:** Dev environments, internal tools, maintenance windows, stateless batch jobs

---

### 2. Rolling Deployment

Replace instances **gradually**—one or a few at a time—until all run the new version.

```
Instance 1: v1 → v2
Instance 2: v1      → v2
Instance 3: v1           → v2
Instance 4: v1                → v2
```

**How it works:**

- Kubernetes `RollingUpdate` is the default `Deployment` strategy
- Load balancer sends traffic only to healthy instances
- `maxUnavailable` and `maxSurge` control pace

**Kubernetes example:**

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1 # at most 1 pod down during update
      maxSurge: 1 # at most 1 extra pod during update
```

**Pros:** No extra hardware; built into K8s and many PaaS platforms  
**Cons:** Mixed versions run simultaneously (compatibility required); slow rollback; bad deploy affects some users before detection

**When to use:** Stateless web APIs, microservices with backward-compatible changes

---

### 3. Blue-Green Deployment

Run **two identical production environments**: Blue (current) and Green (new). Traffic switches atomically from one to the other.

```
                    ┌─────────────┐
         Traffic ──→│ Load        │──→ Blue  (v1)  ← current
                    │ Balancer    │
                    └─────────────┘
                           │
                    (switch traffic)
                           ↓
                    ┌─────────────┐
         Traffic ──→│ Load        │──→ Green (v2)  ← new
                    │ Balancer    │    Blue  (v1)  ← standby / rollback
                    └─────────────┘
```

**How it works:**

1. Deploy v2 to Green (idle environment)
2. Run smoke tests on Green
3. Switch load balancer / DNS to Green
4. Keep Blue running for quick rollback (switch back if issues)

**Pros:** Near-instant rollback; no mixed-version traffic; clear cutover  
**Cons:** Double infrastructure cost; database migrations are tricky (both versions may need to work)

**When to use:** Critical services, regulated releases, when you need confident instant rollback

**Database consideration:** Use backward-compatible migrations (expand-contract pattern) so both Blue and Green can run during transition.

---

### 4. Canary Deployment

Route a **small percentage of traffic** to the new version. If metrics look good, gradually increase until 100%.

```
Traffic ──→ Router ──→ 95% → v1 (stable)
                  └──→  5% → v2 (canary)
```

**Phases:**

```
Phase 1:  5% v2  → monitor error rate, latency, business metrics
Phase 2: 25% v2  → expand if healthy
Phase 3: 50% v2
Phase 4: 100% v2 → full rollout
```

**What to monitor:**

- Error rate and HTTP 5xx
- p95/p99 latency
- Business KPIs (conversion, signups)
- CPU/memory on new pods

**Tools:** Istio, Linkerd, Flagger, Argo Rollouts, AWS App Mesh, LaunchDarkly (with traffic routing)

**Pros:** Limits blast radius; data-driven rollout; catches production-only issues  
**Cons:** Requires good observability; two versions must coexist; complex routing setup

**When to use:** High-traffic production systems, changes with uncertain production impact

**Example with Argo Rollouts:**

```yaml
strategy:
  canary:
    steps:
      - setWeight: 10
      - pause: { duration: 5m }
      - setWeight: 50
      - pause: { duration: 5m }
      - setWeight: 100
```

---

### 5. A/B Testing (Experiment Deployment)

Similar to canary, but traffic is split to **compare behavior**—not just safety. Used for product experiments.

```
Traffic ──→ Router ──→ 50% → UI variant A
                  └──→ 50% → UI variant B
```

**Difference from canary:**

- **Canary**: primary goal is safe rollout of a new _version_
- **A/B test**: primary goal is measuring which _variant_ performs better (click-through, retention)

Often implemented with feature flags + analytics, not purely infrastructure.

**When to use:** Product experimentation, UI changes, algorithm tuning

---

### 6. Feature Flags (Feature Toggles)

Decouple **deployment** from **release**. Code for a new feature ships to production but is **disabled** until toggled on—for all users or a subset.

```
Deploy v2 (feature OFF) → Enable flag for 5% users → Enable for everyone
```

**Types of flags:**

| Type           | Purpose                              |
| -------------- | ------------------------------------ |
| **Release**    | Hide incomplete features until ready |
| **Experiment** | A/B testing                          |
| **Ops**        | Kill switch for problematic features |
| **Permission** | Premium / beta access                |

**Tools:** LaunchDarkly, Unleash, Flagsmith, ConfigCat, built-in toggles in many frameworks

**Pros:** Instant rollback without redeploy; gradual rollout; trunk-based development friendly  
**Cons:** Code complexity; flag debt if not cleaned up; testing all combinations is hard

**When to use:** Continuous deployment, large teams, long-running features, kill switches for risky code

---

### Choosing a Deployment Strategy

```
                    ┌─────────────────────────────────────┐
                    │ Can you afford 2x production infra? │
                    └──────────────┬──────────────────────┘
                          Yes      │      No
                           ↓       │       ↓
                    Blue-Green     │   Rolling or Canary
                                   │
                    ┌──────────────┴──────────────────────┐
                    │ Need gradual risk reduction +       │
                    │ strong metrics?                     │
                    └──────────────┬──────────────────────┘
                          Yes      │      No
                           ↓       │       ↓
                    Canary         │   Rolling
                                   │
                    ┌──────────────┴──────────────────────┐
                    │ Want to decouple deploy from release? │
                    └──────────────┬──────────────────────┘
                          Yes      │
                           ↓       │
                    Feature Flags  │
```

---

## Infrastructure as Code (IaC)

DevOps teams define infrastructure in version-controlled files instead of clicking in a cloud console.

| Tool                   | Style                              | Best For                             |
| ---------------------- | ---------------------------------- | ------------------------------------ |
| **Terraform**          | Declarative (HCL)                  | Multi-cloud, widely adopted          |
| **Pulumi**             | Declarative (code: Python, TS, Go) | Developers who prefer real languages |
| **AWS CloudFormation** | Declarative (YAML/JSON)            | AWS-only shops                       |
| **Ansible**            | Procedural automation              | Config management, server setup      |
| **Helm**               | Kubernetes package manager         | K8s app deployments                  |
| **Kustomize**          | K8s config overlays                | Environment-specific K8s manifests   |

IaC changes go through the same PR + CI review as application code.

---

## Observability & Feedback (Closing the Loop)

CD without observability is dangerous—you cannot detect or roll back bad deploys.

| Pillar      | What It Answers          | Tools                         |
| ----------- | ------------------------ | ----------------------------- |
| **Logs**    | What happened?           | ELK, Loki, CloudWatch         |
| **Metrics** | How much / how fast?     | Prometheus, Grafana, Datadog  |
| **Traces**  | Where did latency occur? | Jaeger, Zipkin, OpenTelemetry |

### Practices

- **Health endpoints**: `/health` and `/ready` for load balancers and K8s probes
- **Deployment markers**: Tag metrics with release version to spot regressions
- **Alerts on SLOs**: Alert on user-facing impact, not just CPU
- **Automated rollback**: Flagger/Argo Rollouts can revert on metric thresholds

---

## Security in CI/CD (DevSecOps)

| Practice                | Description                                                          |
| ----------------------- | -------------------------------------------------------------------- |
| **Shift left**          | Run security checks in CI, not only before release                   |
| **Dependency scanning** | Dependabot, Snyk — catch vulnerable packages                         |
| **SAST**                | Static analysis for code vulnerabilities (Semgrep, CodeQL)           |
| **Container scanning**  | Trivy, Grype — scan images before push                               |
| **Secrets management**  | Never commit secrets; use Vault, AWS Secrets Manager, GitHub Secrets |
| **Least privilege**     | CI runners and deploy roles get minimal permissions                  |
| **Signed artifacts**    | Cosign, Notary — verify image integrity                              |

---

## Common Anti-Patterns

| Anti-Pattern               | Problem                   | Fix                                     |
| -------------------------- | ------------------------- | --------------------------------------- |
| **CI without tests**       | False confidence          | Add meaningful automated tests          |
| **Manual deploy steps**    | Error-prone, slow         | Automate with CD pipeline               |
| **Long-lived branches**    | Painful merges            | Trunk-based development + feature flags |
| **No staging environment** | Bugs hit production first | Deploy to staging with E2E tests        |
| **Ignoring flaky tests**   | Team ignores red CI       | Fix or quarantine flakes immediately    |
| **Snowflake servers**      | "Works on my machine"     | IaC + immutable infrastructure          |
| **Big bang releases**      | High risk, hard rollback  | Smaller changes + canary/blue-green     |

---

## Maturity Model (Simplified)

| Level            | CI                                 | CD                                        | Deploy                                 |
| ---------------- | ---------------------------------- | ----------------------------------------- | -------------------------------------- |
| **1 — Basic**    | Manual builds, occasional tests    | Manual deploy scripts                     | Recreate, downtime acceptable          |
| **2 — Standard** | Automated CI on every PR           | Automated staging deploy                  | Rolling updates                        |
| **3 — Advanced** | Full test + security in CI         | Continuous Delivery to prod (manual gate) | Blue-green or canary                   |
| **4 — Elite**    | Fast, reliable pipelines (<15 min) | Continuous Deployment                     | Canary + feature flags + auto-rollback |

---

## Key Terms Glossary

| Term                         | Definition                                                |
| ---------------------------- | --------------------------------------------------------- |
| **Pipeline**                 | Automated workflow from code change to deploy             |
| **Artifact**                 | Build output stored for deployment (image, binary, zip)   |
| **Runner**                   | Machine that executes pipeline jobs                       |
| **GitOps**                   | Git as single source of truth for deployment state        |
| **IaC**                      | Infrastructure defined in code, versioned in Git          |
| **SAST**                     | Static Application Security Testing                       |
| **DAST**                     | Dynamic testing against running application               |
| **Rollback**                 | Revert to previous known-good version                     |
| **SLO/SLA**                  | Service level objectives/agreements — reliability targets |
| **Immutable infrastructure** | Replace servers/containers instead of patching in place   |

---

## Further Reading

- [The Phoenix Project](https://itrevolution.com/product/the-phoenix-project/) — DevOps culture via narrative
- [Accelerate](https://itrevolution.com/product/accelerate/) — Research on what drives delivery performance
- [Continuous Delivery (Humble & Farley)](https://continuousdelivery.com/) — Foundational CD book
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Argo CD](https://argo-cd.readthedocs.io/) — GitOps for Kubernetes
- [Argo Rollouts](https://argo-rollouts.readthedocs.io/) — Canary and blue-green for K8s
- [12-Factor App](https://12factor.net/) — Principles for cloud-native applications
- [DORA Metrics](https://dora.dev/) — Deployment frequency, lead time, MTTR, change failure rate
