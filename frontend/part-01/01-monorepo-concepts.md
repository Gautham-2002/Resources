# Part 1.4: Monorepo Concepts & Setup

## What You'll Learn

- What monorepos are and why they exist
- Problems monorepos solve
- Monorepo vs Polyrepo (multiple repos)
- pnpm workspaces fundamentals
- TurboRepo for task orchestration
- Shared packages and code
- Versioning and publishing strategies
- Best practices for monorepo development

---

## Table of Contents

1. [Monorepo Concepts](#monorepo-concepts)
2. [Monorepo vs Polyrepo](#monorepo-vs-polyrepo)
3. [pnpm Workspaces](#pnpm-workspaces)
4. [TurboRepo](#turborepo)
5. [Shared Packages](#shared-packages)
6. [Versioning Strategies](#versioning-strategies)
7. [Publishing Strategies](#publishing-strategies)
8. [Complete Monorepo Setup](#complete-monorepo-setup)
9. [Common Patterns & Best Practices](#common-patterns--best-practices)
10. [Common Pitfalls](#common-pitfalls)
11. [Resources](#resources)

---

## Monorepo Concepts

### What is a Monorepo?

A monorepo is a **single Git repository containing multiple projects** that are managed together.

```
Traditional (Polyrepo):
repo-web/               # Separate Git repo
repo-mobile/            # Separate Git repo  
repo-api/               # Separate Git repo
repo-shared-lib/        # Separate Git repo

Monorepo:
my-company/
├── packages/web/       # Web app
├── packages/mobile/    # Mobile app
├── packages/api/       # API
├── packages/shared/    # Shared library
└── All in one Git repo!
```

### Why Monorepos Exist

**Before monorepos, sharing code was hard:**

```javascript
// Company has web app and mobile app
// Both need: validateEmail() function

// Polyrepo problem:
// 1. Create npm package @company/validators
// 2. Publish to npm registry
// 3. Web app: npm install @company/validators
// 4. Mobile app: npm install @company/validators
// 5. Update validator? 
//    - Publish new version
//    - Update both apps
//    - Complex versioning!

// Monorepo solution:
// packages/validators/
// ├── src/validateEmail.ts
// 
// packages/web/
// ├── import from ../../validators
//
// packages/mobile/
// ├── import from ../../validators
//
// Update validator?
// - Change the file
// - Both apps immediately use new version!
```

### Real-World Examples

**Google:** 20+ billion lines of code in one repo

**Facebook:** 
```
react/
├── packages/react/
├── packages/react-dom/
├── packages/react-native/
├── ... 20+ more packages
```

**Babel:**
```
babel/
├── packages/babel-core/
├── packages/babel-parser/
├── packages/babel-generator/
├── ... 150+ packages!
```

---

## Monorepo vs Polyrepo

### Polyrepo Approach

```
repo-frontend/
├── src/
├── package.json
└── .git/

repo-backend/
├── src/
├── package.json
└── .git/

repo-shared/
├── src/
├── package.json
└── .git/
```

**Advantages:**
- ✅ Clear boundaries
- ✅ Independent deployment
- ✅ Different tech stacks
- ✅ Different release cycles

**Disadvantages:**
- ❌ Sharing code is complex (publish to npm)
- ❌ Cross-repo refactoring is painful
- ❌ Version coordination
- ❌ Duplicate dependencies
- ❌ Multiple package manager configs

### Monorepo Approach

```
my-company/
├── packages/
│   ├── web/
│   ├── mobile/
│   ├── api/
│   └── shared-lib/
├── pnpm-workspace.yaml
└── .git/
```

**Advantages:**
- ✅ Easy code sharing
- ✅ Atomic commits across packages
- ✅ Single dependency tree
- ✅ Simplified refactoring
- ✅ Unified tooling

**Disadvantages:**
- ❌ Larger repo
- ❌ Requires careful management
- ❌ CI complexity
- ❌ Access control harder

### Decision Matrix

| Scenario | Monorepo | Polyrepo |
|----------|----------|----------|
| Tightly coupled services | ✅ | ❌ |
| Independent products | ❌ | ✅ |
| Shared code/libraries | ✅ | ❌ |
| Different tech stacks | ❌ | ✅ |
| 2-3 packages | Either | Either |
| 10+ packages | ✅ | ❌ |
| Frequent cross-package changes | ✅ | ❌ |

---

## pnpm Workspaces

### What are pnpm Workspaces?

pnpm workspaces allow **multiple projects to share one node_modules**.

### Traditional npm/yarn Problem

```
repo-structure:
packages/web/
├── node_modules/
│   ├── react/
│   ├── axios/
│   └── 100+ more
├── package.json

packages/mobile/
├── node_modules/
│   ├── react/        # Duplicate!
│   ├── axios/        # Duplicate!
│   └── 100+ more

Total disk space: 500MB for duplicates!
```

### pnpm Workspace Solution

```
repo-structure:
node_modules/
├── .pnpm/           # All packages stored once
│   ├── react@18.0.0/
│   ├── axios@1.0.0/
│   └── 100+ more
├── react -> .pnpm/react@18.0.0
├── axios -> .pnpm/axios@1.0.0

packages/web/
├── node_modules/     # Just links!
│   ├── react -> ../../../node_modules/react
│   └── axios -> ../../../node_modules/axios
├── package.json

packages/mobile/
├── node_modules/     # Just links!
│   ├── react -> ../../../node_modules/react
│   └── axios -> ../../../node_modules/axios
├── package.json

Total disk space: 200MB (no duplicates!)
```

### pnpm Workspace Setup

#### Step 1: Create Workspace File

```yaml
# pnpm-workspace.yaml
packages:
  - 'packages/*'
  - 'services/*'
```

This tells pnpm: treat all folders in `packages/` and `services/` as packages.

#### Step 2: Root package.json

```json
{
  "name": "my-monorepo",
  "private": true,
  "version": "1.0.0",
  "description": "My monorepo",
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "test": "turbo run test",
    "lint": "turbo run lint"
  },
  "devDependencies": {
    "turbo": "^1.8.0",
    "typescript": "^5.0.0",
    "eslint": "^8.0.0"
  }
}
```

#### Step 3: Individual Package Config

```json
// packages/web/package.json
{
  "name": "@mycompany/web",
  "version": "1.0.0",
  "description": "Web application",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.0.0",
    "axios": "^1.0.0",
    "@mycompany/shared": "workspace:*"  // Reference workspace package!
  }
}
```

Key: `"@mycompany/shared": "workspace:*"` means "use the version from this workspace"

#### Step 4: Install Everything

```bash
# Install all dependencies for all packages
pnpm install

# pnpm installs:
# - Root devDependencies
# - Each package's dependencies
# - All in single node_modules tree!
```

### Referencing Workspace Packages

```json
// packages/web/package.json
{
  "dependencies": {
    "@mycompany/shared": "workspace:*",      // Any version in workspace
    "@mycompany/utils": "workspace:^1.0.0",  // Specific version
    "@mycompany/ui": "workspace:~1.2.0"      // Patch versions
  }
}
```

### Commands in Workspaces

```bash
# Run script in all packages
pnpm -r run build

# Run script in specific package
pnpm --filter @mycompany/web run dev

# Add dependency to specific package
pnpm add lodash --filter @mycompany/web

# Add to multiple packages
pnpm add --filter @mycompany/web --filter @mycompany/mobile axios

# Add shared dependency to root
pnpm add -D --workspace-root prettier
```

---

## TurboRepo

### What is TurboRepo?

TurboRepo is a **task orchestrator for monorepos**. It manages running scripts across multiple packages.

### Why TurboRepo?

```bash
# Without TurboRepo:
cd packages/shared && pnpm build
cd ../web && pnpm build
cd ../mobile && pnpm build
# Manual, error-prone, slow!

# With TurboRepo:
turbo run build
# Automatic dependency ordering, parallel execution, caching!
```

### Installation

```bash
pnpm add -D turbo

# Or use preset
pnpm dlx create-turbo@latest
```

### TurboRepo Configuration

```json
{
  "turbo": {
    "globalDependencies": ["**/.env"],
    "pipeline": {
      "build": {
        "dependsOn": ["^build"],  // Build dependencies first
        "outputs": ["dist/**"]     // Cache these files
      },
      "test": {
        "outputs": ["coverage/**"]
      },
      "dev": {
        "cache": false             // Never cache dev
      },
      "lint": {
        "outputs": []              // No outputs to cache
      }
    }
  }
}
```

### Pipeline Explained

```javascript
{
  "build": {
    "dependsOn": ["^build"],  // ^ means: build dependencies first
    "outputs": ["dist/**"]    // Cache dist/ folder
  }
}
```

**What does `"^build"` mean?**

```
Dependency graph:
shared/
├── no dependencies

web/
├── depends on shared

mobile/
├── depends on shared

Without dependsOn: build could run in any order
├── web builds (fails because shared not built yet)
├── mobile builds (fails)
├── shared builds (too late!)

With "dependsOn": ["^build"]: correct order
├── shared builds first
├── web builds (shared ready)
├── mobile builds (shared ready)
```

### Running TurboRepo Tasks

```bash
# Run build in all packages
turbo run build

# Run build only in web package (and dependencies)
turbo run build --filter @mycompany/web

# Run multiple tasks
turbo run build test lint

# Run in parallel (default)
turbo run build --parallel

# Run single-threaded (for debugging)
turbo run build --no-parallel

# Rebuild, ignoring cache
turbo run build --force

# Only affected packages
turbo run build --affected
```

### Caching

TurboRepo caches task outputs:

```bash
# First run: builds everything
pnpm turbo run build
# Hash: web with inputs A, B, C = output X

# Modify unrelated file
# Second run: restored from cache
pnpm turbo run build
# Hash: web with inputs A, B, C = cache hit! Uses output X

# Modify file in web package
# Third run: rebuilds only web
pnpm turbo run build
# Hash: web with inputs A, B, C' = output Y (cache miss)
```

---

## Shared Packages

### Creating Shared Packages

```
packages/
├── shared/
│   ├── src/
│   │   ├── hooks/
│   │   │   ├── useLocalStorage.ts
│   │   │   ├── useFetch.ts
│   │   │   └── index.ts
│   │   ├── utils/
│   │   │   ├── formatters.ts
│   │   │   ├── validators.ts
│   │   │   └── index.ts
│   │   ├── types/
│   │   │   ├── api.types.ts
│   │   │   └── index.ts
│   │   └── index.ts
│   ├── package.json
│   └── tsconfig.json
```

### Shared Package Configuration

```json
// packages/shared/package.json
{
  "name": "@mycompany/shared",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "exports": {
    ".": {
      "types": "./dist/index.d.ts",
      "import": "./dist/index.js"
    },
    "./hooks": {
      "types": "./dist/hooks/index.d.ts",
      "import": "./dist/hooks/index.js"
    },
    "./utils": {
      "types": "./dist/utils/index.d.ts",
      "import": "./dist/utils/index.js"
    }
  },
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch"
  },
  "dependencies": {
    "react": "^18.0.0"
  }
}
```

### Using Shared Packages

```typescript
// packages/web/src/App.tsx
import { useLocalStorage, useFetch } from '@mycompany/shared/hooks';
import { formatDate, validateEmail } from '@mycompany/shared/utils';
import type { User, ApiResponse } from '@mycompany/shared/types';

// Works instantly! No npm publish needed
```

---

## Versioning Strategies

### Fixed Versioning

All packages have the same version:

```
@mycompany/shared@1.5.0
@mycompany/web@1.5.0
@mycompany/mobile@1.5.0

Release = all packages @ 1.5.0
```

**Pros:** Simple, always aligned

**Cons:** Unrelated changes bump all versions

**Tool:** `changesets` with fixed mode

### Independent Versioning

Each package has its own version:

```
@mycompany/shared@1.5.0
@mycompany/web@2.1.0
@mycompany/mobile@3.0.5

Release = each package @ its own version
```

**Pros:** Accurate versions

**Cons:** Complex dependency management

**Tool:** `changesets` with independent mode

### Monorepo Version Only

Only the root has a version, packages don't:

```json
// Root
{ "version": "2.5.0" }

// Packages
{ "version": "0.0.0" } // Not used
```

**Pros:** Simplified, great for internal packages

**Cons:** Doesn't work for npm publication

---

## Publishing Strategies

### Strategy 1: Internal Monorepo (No Publishing)

Packages are **only used internally**:

```json
// packages/shared/package.json
{
  "private": true,  // Never publish!
  "name": "@mycompany/shared"
}
```

**Use case:** Company-only libraries

```bash
pnpm install
# All packages installed from local workspace
```

### Strategy 2: Publish to npm

Packages are **published to npm registry**:

```json
// packages/ui/package.json
{
  "name": "@mycompany/ui",
  "version": "1.5.0",
  "publishConfig": {
    "registry": "https://registry.npmjs.org"
  }
}
```

**Workflow:**

```bash
# Update version in package.json
# Commit changes
git commit -m "Release @mycompany/ui@1.5.0"

# Publish
pnpm publish --filter @mycompany/ui
```

### Strategy 3: Private npm Registry

```json
{
  "name": "@mycompany/ui",
  "publishConfig": {
    "registry": "https://npm.mycompany.com"
  }
}
```

### Using changesets for Versioning

```bash
pnpm add -D @changesets/cli

pnpm changeset
# Interactive prompts:
# - Which packages changed?
# - Major/minor/patch?
# - Write summary

# Creates .changeset/xyz-123.md
```

---

## Complete Monorepo Setup

### Step-by-Step Setup

#### 1. Create Directory Structure

```bash
mkdir my-monorepo
cd my-monorepo

mkdir -p packages/{shared,web,mobile}
mkdir -p services/{api}
```

#### 2. Create Root Files

```bash
# pnpm-workspace.yaml
cat > pnpm-workspace.yaml << 'EOF'
packages:
  - 'packages/*'
  - 'services/*'
EOF

# Root package.json
cat > package.json << 'EOF'
{
  "name": "my-monorepo",
  "private": true,
  "version": "1.0.0",
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "test": "turbo run test",
    "lint": "turbo run lint"
  },
  "devDependencies": {
    "turbo": "^1.8.0"
  }
}
EOF
```

#### 3. Create Package Structures

```bash
# packages/shared/package.json
cat > packages/shared/package.json << 'EOF'
{
  "name": "@mycompany/shared",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "exports": {
    ".": "./dist/index.js"
  },
  "scripts": {
    "build": "tsc"
  },
  "devDependencies": {
    "typescript": "^5.0.0"
  }
}
EOF

# packages/web/package.json
cat > packages/web/package.json << 'EOF'
{
  "name": "@mycompany/web",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "@mycompany/shared": "workspace:*"
  },
  "devDependencies": {
    "vite": "^4.0.0"
  }
}
EOF
```

#### 4. Create TurboRepo Config

```bash
cat > turbo.json << 'EOF'
{
  "turbo": {
    "pipeline": {
      "build": {
        "dependsOn": ["^build"],
        "outputs": ["dist/**"]
      },
      "dev": {
        "cache": false
      },
      "test": {
        "outputs": ["coverage/**"]
      },
      "lint": {
        "outputs": []
      }
    }
  }
}
EOF
```

#### 5. Initialize Git and Install

```bash
git init
pnpm install
```

---

## Common Patterns & Best Practices

### Pattern 1: Package Organization

```
packages/
├── shared/          # Shared libraries (no dependencies on other packages)
├── ui/              # UI component library
├── hooks/           # Custom hooks library
├── utils/           # Utility functions

services/
├── api/             # Backend API
├── worker/          # Background jobs

apps/
├── web/             # Web application
├── mobile/          # Mobile application
├── admin/           # Admin dashboard
```

### Pattern 2: Clear Dependency Direction

```
web (app)
  ↓ depends on
ui (component library)
  ↓ depends on
shared (utilities)

Not allowed:
shared → ui → web (circular!)
```

### Pattern 3: Turbo Filtering

```bash
# Run only web's build (and dependencies)
pnpm turbo run build --filter @mycompany/web

# Run only affected by recent changes
pnpm turbo run build --affected

# Run with dependency graph visualization
pnpm turbo run build --graph
```

### Pattern 4: Shared Devtools

```json
// Root package.json
{
  "devDependencies": {
    "typescript": "^5.0.0",
    "eslint": "^8.0.0",
    "prettier": "^3.0.0",
    "vitest": "^0.34.0"
  }
}
```

All packages use the same version of tools!

### Pattern 5: Workspace Protocol

```json
{
  "dependencies": {
    "@mycompany/shared": "workspace:*",     // Any version
    "@mycompany/ui": "workspace:^1.0.0",    // Respects semver
    "@mycompany/hooks": "workspace:~1.2.0"  // Within patch
  }
}
```

### Pattern 6: TypeScript Configuration Inheritance

```json
// Root tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "strict": true
  }
}

// packages/web/tsconfig.json
{
  "extends": "../../tsconfig.json",
  "compilerOptions": {
    "outDir": "./dist"
  },
  "include": ["src"]
}
```

---

## Common Pitfalls

### Pitfall 1: Circular Dependencies

```
❌ Bad:
shared → hooks
  ↓
hooks → shared (circular!)

✅ Good:
shared (no dependencies)
  ↑
hooks (depends on shared)
  ↑
ui (depends on hooks and shared)
```

**How to prevent:**
- Clear directory structure
- Dependency diagram
- ESLint rules

### Pitfall 2: Installing Globally

```bash
# ❌ Wrong - installs globally, not in monorepo
npm install react

# ✅ Correct - installs in specific package
pnpm add react --filter @mycompany/web

# ✅ Also correct - installs to root devDependencies
pnpm add -D prettier --workspace-root
```

### Pitfall 3: Ignoring Workspace Protocol

```json
{
  // ❌ Wrong - breaks monorepo benefits
  "dependencies": {
    "@mycompany/shared": "^1.0.0"  // Points to npm!
  }
}

// ✅ Correct - uses workspace version
{
  "dependencies": {
    "@mycompany/shared": "workspace:*"
  }
}
```

### Pitfall 4: Not Using TurboRepo

```bash
# ❌ Manual, error-prone
pnpm --filter @mycompany/shared run build
pnpm --filter @mycompany/web run build

# ✅ TurboRepo handles ordering, caching
turbo run build
```

### Pitfall 5: Publishing All Packages

```json
{
  // ❌ All packages published to npm
  "name": "@mycompany/internal-shared"
  // Wastes effort, pollutes npm
}

// ✅ Mark internal packages as private
{
  "name": "@mycompany/internal-shared",
  "private": true  // Never published
}
```

---

## Resources

- **pnpm Workspaces Documentation:** https://pnpm.io/workspaces
- **TurboRepo Documentation:** https://turbo.build/repo/docs
- **TurboRepo Examples:** https://github.com/vercel/turbo/tree/main/examples
- **Monorepo.tools Guide:** https://monorepo.tools/
- **Changesets:** https://github.com/changesets/changesets
- **Lerna (Alternative):** https://lerna.js.org/

---

**Next:** [Part 2.1: The DOM Problem & React Solution](./02-dom-problems.md) - Understand why React was created and what problems it solves
