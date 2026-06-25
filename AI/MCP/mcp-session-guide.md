# MCP: Model Context Protocol
## A Complete Session Guide for Software Engineers

> **Audience:** Mid-level engineers with API knowledge and some AI exposure  
> **Duration:** ~2-3 hours (talk + hands-on)  
> **Format:** Story-driven explanation → Deep dive → Live demo → Productivity guide

---

# PART 1: THE STORY — HOW WE GOT HERE

## Chapter 1: The Rise of LLMs — Text In, Text Out

Cast your mind back to early LLMs. GPT-3, early Claude, early Gemini.

You had one interaction model:

```
User: "What is the capital of France?"
LLM:  "The capital of France is Paris."
```

That's it. Text in. Text out. The LLM was a **brilliant oracle locked in a box.**

It could:
- ✅ Answer questions
- ✅ Write code
- ✅ Summarize documents
- ✅ Translate text

It could NOT:
- ❌ Browse the internet
- ❌ Read your files
- ❌ Query your database
- ❌ Create a GitHub PR
- ❌ Send an email
- ❌ Run your code
- ❌ Know what time it is right now

The LLM was essentially a **very smart book** — full of knowledge, but passive. You had to do everything yourself.

---

## Chapter 2: The Problem Becomes Clear

Developers started building AI applications and quickly hit a wall.

Imagine you're building an AI coding assistant. The user says:

> *"Look at my last 3 commits on the main branch and write a summary for the standup."*

With a vanilla LLM, you'd have to:
1. Manually call GitHub API yourself
2. Format the response
3. Pass it to the LLM as context
4. Get the summary back
5. Return it to the user

You — the developer — became the **glue code** between the LLM and the real world. Every integration was custom. Every app reinvented the wheel.

This didn't scale.

---

## Chapter 3: Tool Calling Arrives — The First Solution

OpenAI introduced **Function Calling** (now called Tool Calling) around mid-2023. Anthropic, Google followed.

The idea: tell the LLM *"hey, you have access to these functions"* and it can decide when to call them.

```json
// You describe tools to the LLM
{
  "tools": [
    {
      "name": "get_github_commits",
      "description": "Fetches recent commits from a GitHub repo",
      "parameters": {
        "repo": "string",
        "branch": "string",
        "limit": "number"
      }
    }
  ]
}
```

The LLM would respond with:
```json
{
  "tool_call": {
    "name": "get_github_commits",
    "arguments": { "repo": "my-app", "branch": "main", "limit": 3 }
  }
}
```

Then **your application code** actually executes the function, returns the result, and the LLM continues.

**This was a huge step forward.** But it still had problems:

| Problem | Description |
|---|---|
| **Tightly coupled** | Each app implements its own tools from scratch |
| **Not reusable** | Your GitHub tool isn't shareable with another app |
| **No standard** | Every provider has different tool-calling formats |
| **Hard to discover** | No ecosystem of pre-built tools |
| **Context management** | You manage all state and results yourself |

Tool calling solved the "can the LLM use tools" problem — but created an **integration fragmentation** problem.

---

## Chapter 4: Enter MCP — The Universal Adapter

In **November 2024**, Anthropic released the **Model Context Protocol (MCP)** as an open standard.

Think of it like this:

> Before USB, every peripheral had its own connector. Keyboards, mice, printers — all different. **USB was the universal standard** that made everything plug-and-play.
>
> **MCP is USB for AI tools.**

MCP defines a **standard protocol** for how AI applications connect to external tools, data sources, and services — regardless of which LLM you're using.

```
Before MCP:
  App A  ──custom──►  GitHub
  App A  ──custom──►  Database  
  App B  ──custom──►  GitHub    (built again from scratch!)
  App B  ──custom──►  Filesystem

After MCP:
  App A  ──MCP──►  GitHub MCP Server
  App B  ──MCP──►  GitHub MCP Server   (same server, reused!)
  App C  ──MCP──►  GitHub MCP Server   (zero extra work!)
```

---

# PART 2: WHAT IS MCP — THE DEEP DIVE

## The Official Definition

> **Model Context Protocol (MCP)** is an open protocol that standardizes how applications provide context to LLMs. It creates a universal interface between AI models and external data sources, tools, and services.

## The Architecture: Three Players

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Architecture                      │
│                                                         │
│  ┌──────────────┐         ┌──────────────────────────┐  │
│  │   MCP HOST   │         │      MCP SERVERS         │  │
│  │              │         │                          │  │
│  │  Claude.ai   │◄──MCP──►│  GitHub MCP Server       │  │
│  │  Cursor      │         │  Filesystem MCP Server   │  │
│  │  Your App    │◄──MCP──►│  Postgres MCP Server     │  │
│  │              │         │  Brave Search MCP Server │  │
│  │  [contains   │         │                          │  │
│  │  MCP CLIENT] │         └──────────────────────────┘  │
│  └──────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

### 1. MCP Host
The AI application — Claude Desktop, Cursor, your custom app. It **contains an MCP client** and orchestrates everything.

### 2. MCP Client
Lives inside the host. Manages the connection to one or more MCP servers. Handles the protocol communication.

### 3. MCP Server
A lightweight process that **exposes capabilities** — tools, resources, or prompts — via the MCP protocol. This is where GitHub, filesystem, databases etc. are wrapped.

---

## What Can an MCP Server Expose?

MCP servers can provide three types of things:

### 🔧 Tools (Actions)
Things the LLM can **do** — execute code, write files, call APIs.

```
search_web(query)
create_github_issue(title, body, labels)
run_sql_query(query)
read_file(path)
```

### 📄 Resources (Data)
Things the LLM can **read** — files, database records, API responses.

```
file://path/to/project/README.md
db://postgres/users_table
github://repo/main/src/index.ts
```

### 💬 Prompts (Templates)
Pre-built prompt templates that users can invoke.

```
"Summarize my open PRs"
"Explain this SQL query"
"Code review checklist"
```

---

## How Does It Actually Work? — The Protocol Flow

MCP uses **JSON-RPC 2.0** over different transports:

- **stdio** — local processes (most common for desktop apps)
- **HTTP + SSE** — remote servers over the network

Here's a real flow:

```
1. HOST starts MCP Server as subprocess
   Host: spawns `npx @modelcontextprotocol/server-github`

2. INITIALIZATION HANDSHAKE
   Client → Server: { "method": "initialize", "params": { "protocolVersion": "2024-11-05" } }
   Server → Client: { "result": { "capabilities": { "tools": {}, "resources": {} } } }

3. DISCOVER CAPABILITIES
   Client → Server: { "method": "tools/list" }
   Server → Client: { "result": { "tools": [ 
     { "name": "create_issue", "description": "...", "inputSchema": {...} },
     { "name": "list_commits", "description": "...", "inputSchema": {...} }
   ]}}

4. USER SENDS MESSAGE TO LLM
   User: "Create a GitHub issue for the login bug I just found"

5. LLM DECIDES TO USE A TOOL
   LLM → Host: { "tool_call": { "name": "create_issue", "arguments": {...} } }

6. HOST CALLS MCP SERVER
   Client → Server: { "method": "tools/call", "params": { "name": "create_issue", "arguments": {...} } }

7. SERVER EXECUTES AND RETURNS
   Server → Client: { "result": { "content": [{ "type": "text", "text": "Issue #42 created" }] } }

8. HOST PASSES RESULT BACK TO LLM
   LLM sees the result and generates final response to user
```

---

# PART 3: TOOL CALLING vs MCP — THE CLEAR DISTINCTION

This is where most people get confused. Let's settle it.

## They Solve Different Problems

| Aspect | Tool Calling | MCP |
|---|---|---|
| **What it is** | LLM feature / API capability | Open protocol / standard |
| **Who defines it** | Each AI provider (OpenAI, Anthropic) | Anthropic (open standard) |
| **Where tools run** | In your application code | In separate MCP server processes |
| **Reusability** | Low — reimplemented per app | High — one server, many apps |
| **Discovery** | You define tools per request | Server advertises capabilities |
| **Ecosystem** | No shared ecosystem | Growing library of MCP servers |
| **Portability** | Locked to LLM provider | Works across any MCP-compatible host |

## The Relationship

```
MCP USES tool calling under the hood.
Tool calling is the mechanism.
MCP is the ecosystem and standard built on top of it.
```

Think of it this way:
- **Tool calling** = the ability to make HTTP requests
- **MCP** = REST API conventions (standard methods, status codes, auth patterns)

Tool calling is a raw capability. MCP is the **agreed convention** that makes it universally usable.

## Concrete Example

**Without MCP (raw tool calling):**
```python
# App developer writes this for EVERY app
def handle_tool_call(tool_name, args):
    if tool_name == "search_github":
        return github_client.search(args["query"])  # custom code
    elif tool_name == "read_file":
        return open(args["path"]).read()             # custom code
    elif tool_name == "query_db":
        return db.execute(args["sql"])               # custom code

# Pass tools to LLM manually formatted for this specific provider
response = anthropic.messages.create(
    tools=[{ "name": "search_github", ... }],  # formatted YOUR way
    ...
)
```

**With MCP:**
```json
// mcp_config.json — that's it. No code written.
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-github"]
    },
    "filesystem": {
      "command": "npx", 
      "args": ["@modelcontextprotocol/server-filesystem", "/home/user/projects"]
    },
    "postgres": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
    }
  }
}
```

**The LLM now has all those tools automatically. Zero custom tool code written.**

---

# PART 4: DOCKER MCP GATEWAY

## The Problem MCP Gateway Solves

Running MCP servers locally is great. But what about:
- **Teams** — every developer setting up MCP servers manually?
- **Security** — MCP servers having direct access to your filesystem/DB?
- **Remote access** — using MCP servers from cloud AI agents?
- **Management** — 10 different MCP servers to install and maintain?

**Docker MCP Gateway** (also called Docker MCP Toolkit) solves this.

## What It Is

Docker MCP Gateway is a **containerized reverse proxy and registry** for MCP servers. It:

1. **Packages MCP servers as Docker containers** — isolated, versioned, portable
2. **Provides a single HTTP/SSE endpoint** — your AI client connects to one URL
3. **Manages auth and secrets** — credentials stored securely, not in config files
4. **Enables remote MCP** — access your tools from cloud-hosted AI agents

```
Without Docker MCP Gateway:
  Cursor ──stdio──► GitHub MCP (local process)
  Cursor ──stdio──► Postgres MCP (local process)  
  Cursor ──stdio──► Filesystem MCP (local process)
  [3 processes, manual setup, security concerns]

With Docker MCP Gateway:
  Cursor ──HTTP/SSE──► Docker MCP Gateway :8811
                              │
                              ├──► GitHub MCP Container
                              ├──► Postgres MCP Container
                              └──► Filesystem MCP Container
  [one endpoint, containerized, secure, team-shareable]
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  Docker MCP Gateway                       │
│                                                          │
│  ┌─────────────┐    ┌──────────────────────────────────┐ │
│  │  HTTP/SSE   │    │     MCP Server Registry          │ │
│  │  Endpoint   │───►│  ┌──────────┐  ┌──────────────┐  │ │
│  │  :8811      │    │  │ github   │  │  filesystem  │  │ │
│  └─────────────┘    │  │ container│  │  container   │  │ │
│                     │  └──────────┘  └──────────────┘  │ │
│  ┌─────────────┐    │  ┌──────────┐  ┌──────────────┐  │ │
│  │  Auth &     │    │  │ postgres │  │    brave     │  │ │
│  │  Secrets    │    │  │ container│  │  container   │  │ │
│  └─────────────┘    │  └──────────┘  └──────────────┘  │ │
└──────────────────────────────────────────────────────────┘
```

## Quick Setup

```bash
# Install Docker Desktop (includes MCP Toolkit in recent versions)
# OR via Docker Extension

# Start the gateway
docker mcp gateway start

# Add an MCP server
docker mcp server add github
docker mcp server add filesystem

# Configure secrets
docker mcp secret set GITHUB_TOKEN=ghp_yourtoken

# Your endpoint is ready
# http://localhost:8811/sse
```

## When to Use Docker MCP Gateway

| Scenario | Use Gateway? |
|---|---|
| Solo developer, local tools | Not necessary |
| Team sharing MCP servers | ✅ Yes |
| Production AI agents in cloud | ✅ Yes |
| Security-sensitive environments | ✅ Yes |
| CI/CD pipelines with AI | ✅ Yes |

---

# PART 5: THE MCP ECOSYSTEM

## Popular MCP Servers

### Official (by Anthropic)
| Server | What it does |
|---|---|
| `@modelcontextprotocol/server-filesystem` | Read/write local files |
| `@modelcontextprotocol/server-github` | GitHub repos, PRs, issues, commits |
| `@modelcontextprotocol/server-postgres` | Query PostgreSQL databases |
| `@modelcontextprotocol/server-sqlite` | Query SQLite databases |
| `@modelcontextprotocol/server-brave-search` | Web search via Brave API |
| `@modelcontextprotocol/server-memory` | Persistent key-value memory |
| `@modelcontextprotocol/server-puppeteer` | Browser automation |
| `@modelcontextprotocol/server-slack` | Slack messages, channels |
| `@modelcontextprotocol/server-google-maps` | Maps, geocoding, directions |

### Community Favorites
| Server | What it does |
|---|---|
| `mcp-server-fetch` | Fetch any URL, scrape web pages |
| `mcp-server-docker` | Manage Docker containers |
| `mcp-server-kubernetes` | Manage K8s clusters |
| `mcp-obsidian` | Read/write Obsidian vaults |
| `mcp-notion` | Notion pages and databases |
| `mcp-linear` | Linear issues and projects |
| `mcp-jira` | Jira tickets and sprints |
| `mcp-aws` | AWS resources and services |

### Find More
- **Official registry:** https://github.com/modelcontextprotocol/servers
- **Community list:** https://mcphub.io
- **Smithery:** https://smithery.ai

## Popular MCP Clients (Hosts)

| Client | Type | Best For |
|---|---|---|
| **Cursor** | IDE | Coding, code review, repo management |
| **Claude Desktop** | Chat app | General tasks, file work |
| **Claude.ai** | Web | Connected apps in browser |
| **Windsurf** | IDE | Alternative to Cursor |
| **Continue.dev** | VS Code extension | Open source coding assistant |
| **Zed** | IDE | Fast, Rust-based editor |
| **Your custom app** | Custom | Any app using MCP SDK |

---

# PART 6: HANDS-ON DEMO WITH CURSOR

## Prerequisites

```bash
# Node.js 18+ required
node --version

# Install Cursor (cursor.sh)
# Get API keys:
# - GitHub: github.com/settings/tokens (needs repo scope)
# - Brave Search: brave.com/search/api (free tier: 2000 req/month)
```

## Step 1: Configure MCP in Cursor

Open Cursor settings: `Cmd/Ctrl + Shift + P` → "Open MCP Settings"

Or edit `~/.cursor/mcp.json` (Mac/Linux) / `%APPDATA%\Cursor\mcp.json` (Windows):

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/yourname/projects"
      ]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your_token_here"
      }
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your_brave_api_key_here"
      }
    },
    "sqlite": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sqlite",
        "--db-path",
        "/Users/yourname/demo/demo.db"
      ]
    }
  }
}
```

Restart Cursor. You should see MCP servers connected in the status bar.

---

## DEMO 1: Filesystem MCP — AI-Powered Project Analysis

### Setup
```bash
# Create a sample project to analyze
mkdir ~/projects/demo-app
cd ~/projects/demo-app
git init
mkdir src tests docs
echo '{"name": "demo-app", "version": "1.0.0"}' > package.json
cat > src/users.js << 'EOF'
function getUser(id) {
  // TODO: add validation
  return db.query(`SELECT * FROM users WHERE id = ${id}`)
}

function createUser(name, email) {
  if (!email) throw new Error("email required")
  return db.query(`INSERT INTO users (name, email) VALUES (${name}, ${email})`)
}
EOF
```

### Demo Prompts in Cursor Chat

```
Prompt 1 — Project Overview:
"Read the contents of my demo-app project directory and give me 
a quick overview of the structure and what this project does."

Prompt 2 — Code Review:
"Read src/users.js and identify any security vulnerabilities 
or bugs. Be specific."

Prompt 3 — Generate Documentation:
"Read src/users.js and create a docs/users.md documentation 
file for these functions including JSDoc comments in the source."

Prompt 4 — Refactor and Save:
"Rewrite src/users.js to fix the SQL injection vulnerabilities 
you found. Use parameterized queries. Save the fixed version."
```

**What you'll see:** Cursor reads files, identifies SQL injection (string interpolation in queries), generates fixed code with parameterized queries, and writes it back — all through MCP filesystem tools.

---

## DEMO 2: GitHub MCP — Real Repository Intelligence

### Setup
```bash
# Use any public GitHub repo you have access to
# Or fork: github.com/modelcontextprotocol/servers
```

### Demo Prompts

```
Prompt 1 — Repo Overview:
"Search for my GitHub repos and list the 5 most recently 
updated ones with their descriptions."

Prompt 2 — PR Review:
"Look at the open pull requests on [your-repo]. Summarize 
what changes each PR is making."

Prompt 3 — Create an Issue from Code Analysis:
"Read the users.js file in my project. Based on the TODO 
comment, create a GitHub issue titled 'Add input validation 
to getUser function' with a detailed description."

Prompt 4 — Commit History:
"Show me the last 10 commits on the main branch of [repo]. 
Write a changelog entry based on these commits."
```

**What you'll see:** Cursor connects to GitHub via MCP, reads your real repos, creates real issues, all without you leaving your editor.

---

## DEMO 3: Brave Search MCP — Real-Time Web Knowledge

### Demo Prompts

```
Prompt 1 — Research with recency:
"Search the web for 'MCP Model Context Protocol tutorial 2024' 
and summarize the top approaches people are using."

Prompt 2 — Combined with filesystem:
"Search for the latest best practices for Node.js error handling 
in 2024, then update the error handling in my users.js file 
based on what you find."

Prompt 3 — Competitor research (fun demo):
"Search for 'top AI coding assistants 2024 comparison' and 
create a docs/competitors.md file with a comparison table."
```

**What you'll see:** The real power — combining web search with filesystem writes. AI that can research AND implement.

---

## DEMO 4: SQLite MCP — Natural Language Database

### Setup
```bash
# Install sqlite3
brew install sqlite3  # Mac
# or: sudo apt install sqlite3 (Ubuntu)

# Create demo database
sqlite3 ~/demo/demo.db << 'EOF'
CREATE TABLE products (
  id INTEGER PRIMARY KEY,
  name TEXT,
  price REAL,
  category TEXT,
  stock INTEGER
);
INSERT INTO products VALUES 
  (1, 'Laptop Pro', 1299.99, 'Electronics', 45),
  (2, 'Wireless Mouse', 29.99, 'Electronics', 230),
  (3, 'Standing Desk', 549.00, 'Furniture', 12),
  (4, 'Notebook Set', 12.99, 'Stationery', 500),
  (5, 'USB Hub', 34.99, 'Electronics', 88),
  (6, 'Ergonomic Chair', 799.00, 'Furniture', 7);
EOF
```

### Demo Prompts

```
Prompt 1 — Natural language query:
"What products do we have in stock? Show me everything 
grouped by category with total inventory value."

Prompt 2 — Business insight:
"Which category has the lowest stock? Should we be worried 
about any products running out soon?"

Prompt 3 — Schema exploration:
"Describe the database schema and suggest 2 additional 
tables we might want to add for a proper e-commerce system."

Prompt 4 — Data manipulation:
"Add 3 new realistic products to the database — one from 
each existing category."
```

**What you'll see:** Non-technical-style questions getting answered with real SQL execution. The LLM writes and runs the SQL — you just ask questions.

---

## DEMO 5: The Power Combo — Chaining Multiple MCP Servers

This is the real showstopper demo.

```
Mega Prompt:
"I need to prepare a status report. Do the following:
1. Search the web for current trends in [your tech stack]
2. Read my project files and identify what we've built so far
3. Check our GitHub for open issues and recent commits
4. Query the database for current product stats
5. Write a comprehensive status.md report combining all of this"
```

**What you'll see:** The LLM orchestrates 4 different MCP servers in sequence — web search → filesystem read → GitHub query → SQL query → filesystem write. This is something that would have taken hours of manual work.

---

# PART 7: BUILDING YOUR OWN MCP SERVER

## When to Build Custom

- Your internal APIs and tools
- Company databases not covered by existing servers
- Domain-specific operations (your CI/CD, your monitoring, etc.)

## Simple Custom Server Example

```typescript
// my-company-mcp-server.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server(
  { name: "company-tools", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// Register your tools
server.setRequestHandler("tools/list", async () => ({
  tools: [
    {
      name: "get_deployment_status",
      description: "Check the deployment status of a service",
      inputSchema: {
        type: "object",
        properties: {
          service: { type: "string", description: "Service name" },
          environment: { type: "string", enum: ["dev", "staging", "prod"] }
        },
        required: ["service", "environment"]
      }
    },
    {
      name: "get_error_logs",
      description: "Fetch recent error logs for a service",
      inputSchema: {
        type: "object",
        properties: {
          service: { type: "string" },
          last_n_hours: { type: "number", default: 1 }
        },
        required: ["service"]
      }
    }
  ]
}));

// Handle tool calls
server.setRequestHandler("tools/call", async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "get_deployment_status") {
    // Your actual implementation here
    const status = await yourDeploymentAPI.getStatus(args.service, args.environment);
    return {
      content: [{ type: "text", text: JSON.stringify(status) }]
    };
  }

  if (name === "get_error_logs") {
    const logs = await yourLoggingSystem.getLogs(args.service, args.last_n_hours);
    return {
      content: [{ type: "text", text: logs.join("\n") }]
    };
  }
});

// Start the server
const transport = new StdioServerTransport();
await server.connect(transport);
```

```bash
# Install and run
npm install @modelcontextprotocol/sdk
npx ts-node my-company-mcp-server.ts
```

Add to Cursor config:
```json
{
  "mcpServers": {
    "company-tools": {
      "command": "npx",
      "args": ["ts-node", "/path/to/my-company-mcp-server.ts"]
    }
  }
}
```

---

# PART 8: MCP FOR PRODUCTIVITY — REAL-WORLD WORKFLOWS

## Workflow 1: Morning Standup Prep (2 min instead of 10)

```
"Using GitHub MCP, find all commits and PRs I was involved in 
yesterday. Then check my open issues. Write a standup update 
in this format: What I did yesterday / What I'm doing today / 
Any blockers."
```

## Workflow 2: Code Review Acceleration

```
"Read the diff of PR #47 in [repo]. Give me:
- Summary of changes
- Potential bugs or edge cases
- Security concerns
- Suggested review comments with line references"
```

## Workflow 3: Onboarding New Codebase

```
"Read all the files in /projects/legacy-app/src. 
Create a comprehensive docs/architecture.md explaining:
- What the app does
- Key components and their relationships
- Data flow
- Gotchas and non-obvious decisions"
```

## Workflow 4: Bug Investigation

```
"Search the web for '[error message I'm seeing]'. 
Then read my [relevant file]. Then check if there are 
any related GitHub issues in my repo. 
Give me the most likely cause and a fix."
```

## Workflow 5: Database-Driven Feature Development

```
"Query the database schema. I want to add user authentication. 
What tables do I need to add? Generate the SQL migration, 
save it as migrations/002_add_auth.sql, and update the 
docs/schema.md file."
```

## Workflow 6: Automated Release Notes

```
"Get all commits since tag v1.2.0 on the main branch of [repo]. 
Group them into: Features, Bug Fixes, Breaking Changes. 
Create a CHANGELOG.md entry for version v1.3.0."
```

---

## Pro Tips for MCP Productivity

### 1. Be Specific About File Paths
```
❌ "Read my config file"
✅ "Read /projects/myapp/config/database.yml"
```

### 2. Chain Operations Explicitly
```
✅ "First search for X, then based on what you find, 
    update Y file, then create a GitHub issue summarizing the change"
```

### 3. Set Scope Boundaries for Filesystem
```json
// Only give access to specific directories
"args": ["@mcp/server-filesystem", "/projects", "/documents/notes"]
// NOT your entire home directory
```

### 4. Use MCP for Exploration, Not Just Execution
```
"Browse through the src directory and tell me what's there 
before we start changing anything"
```

### 5. Combine Search + Implement
```
"Search for how [library] handles [feature] in their latest version,
then implement it in my code following that pattern"
```

---

# QUICK REFERENCE

## MCP Config Locations

| Client | Config File Location |
|---|---|
| Cursor | `~/.cursor/mcp.json` |
| Claude Desktop (Mac) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Win) | `%APPDATA%\Claude\claude_desktop_config.json` |

## Essential Commands

```bash
# Test if an MCP server works
npx @modelcontextprotocol/inspector npx @modelcontextprotocol/server-filesystem /tmp

# List available official servers
npx @modelcontextprotocol/create-server --help

# Initialize a new MCP server project
npx @modelcontextprotocol/create-server my-server
```

## MCP Inspector (Debug Tool)

The MCP Inspector lets you test any MCP server without an AI client:

```bash
npx @modelcontextprotocol/inspector

# Then in browser: http://localhost:5173
# Connect to your server and test tools manually
```

---

## Key Takeaways

1. **LLMs started as passive oracles** — text in, text out, no real-world access
2. **Tool calling** gave LLMs the ability to act — but every app reimplemented it differently
3. **MCP standardized** the interface — write a server once, use it everywhere
4. **MCP = USB for AI** — universal plug-and-play for AI tools
5. **Docker MCP Gateway** brings security, portability, and team sharing to MCP
6. **The ecosystem is growing fast** — hundreds of servers for common services
7. **Real productivity gains** come from chaining multiple MCP servers together
8. **Build custom servers** for your internal tools — it's just a few lines of TypeScript

---

## Resources

- 📖 **MCP Docs:** https://modelcontextprotocol.io
- 🛠️ **Official Servers:** https://github.com/modelcontextprotocol/servers
- 🔍 **Server Registry:** https://mcphub.io / https://smithery.ai
- 🐛 **MCP Inspector:** `npx @modelcontextprotocol/inspector`
- 📦 **MCP SDK (TypeScript):** `npm install @modelcontextprotocol/sdk`
- 📦 **MCP SDK (Python):** `pip install mcp`
- 🐳 **Docker MCP:** https://docs.docker.com/ai/mcp-catalog-and-toolkit/
- 💬 **Community:** https://discord.gg/anthropic

---

*Session guide prepared for mid-level software engineers | MCP v2024-11-05*
