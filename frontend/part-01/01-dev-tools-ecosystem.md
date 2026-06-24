# Part 1.3: Developer Tools & Ecosystem

## What You'll Learn

- ESLint and code linting
- Prettier and code formatting
- TypeScript integration with build tools
- Husky and pre-commit hooks
- EditorConfig and cross-editor consistency
- Development environment best practices
- Tools integration strategies

---

## Table of Contents

1. [ESLint - Static Code Analysis](#eslint---static-code-analysis)
2. [Prettier - Code Formatting](#prettier---code-formatting)
3. [ESLint + Prettier Integration](#eslint--prettier-integration)
4. [TypeScript Integration](#typescript-integration)
5. [Git Hooks with Husky](#git-hooks-with-husky)
6. [EditorConfig](#editorconfig)
7. [Complete Tooling Setup](#complete-tooling-setup)
8. [Common Patterns & Best Practices](#common-patterns--best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Resources](#resources)

---

## ESLint - Static Code Analysis

### What is ESLint?

ESLint analyzes your code for errors and style issues **before runtime**.

### Why ESLint Matters

```javascript
// ❌ Without ESLint - Bug not caught until runtime
function getUserData(userId) {
  const response = await fetch(`/api/users/${userId}`);
  // Forgot await!
  return respoonse.json(); // Typo! Should be 'response'
}

// ✅ With ESLint - Errors caught immediately
// Error: 'respoonse' is not defined (ESLint)
// Error: Missing await on promise (ESLint)
```

### Installation & Setup

```bash
# Install ESLint
pnpm add -D eslint

# Initialize config
pnpm eslint --init
# Or use modern flat config

# Create eslint.config.js (modern)
export default [
  {
    ignores: ['dist', 'node_modules'],
    files: ['**/*.js', '**/*.jsx', '**/*.ts', '**/*.tsx'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module'
    },
    rules: {
      'no-unused-vars': 'error',
      'no-console': 'warn'
    }
  }
];
```

### Common ESLint Rules

```javascript
// eslint.config.js
export default [
  {
    rules: {
      // Errors to catch
      'no-unused-vars': 'error',
      'no-undef': 'error',
      'no-console': 'warn',
      'eqeqeq': ['error', 'always'], // Use === not ==
      
      // Best practices
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'prefer-const': 'error',
      'no-var': 'error',
      
      // Code quality
      'complexity': ['warn', 10], // Functions too complex
      'max-lines': ['warn', 300], // Files too long
      'no-nested-ternary': 'warn',
    }
  }
];
```

### ESLint for React

```bash
pnpm add -D eslint-plugin-react eslint-plugin-react-hooks
```

```javascript
// eslint.config.js
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  {
    plugins: {
      react,
      'react-hooks': reactHooks
    },
    rules: {
      // React-specific rules
      'react/prop-types': 'off', // Using TypeScript
      'react/react-in-jsx-scope': 'off', // React 17+
      'react/jsx-uses-react': 'off', // React 17+
      
      // Hooks rules (CRITICAL!)
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn'
    }
  }
];
```

### ESLint for TypeScript

```bash
pnpm add -D @typescript-eslint/parser @typescript-eslint/eslint-plugin
```

```javascript
// eslint.config.js
import ts from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';

export default [
  {
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: './tsconfig.json'
      }
    },
    plugins: {
      '@typescript-eslint': ts
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': 'error',
      '@typescript-eslint/explicit-function-return-types': 'warn',
      '@typescript-eslint/no-floating-promises': 'error'
    }
  }
];
```

### Running ESLint

```bash
# Check all files
pnpm eslint .

# Check specific file
pnpm eslint src/App.tsx

# Fix automatically
pnpm eslint . --fix

# Check only changed files (with Git)
pnpm eslint $(git diff --name-only --diff-filter=ACMRTUX)
```

---

## Prettier - Code Formatting

### What is Prettier?

Prettier automatically formats your code with **no configuration arguments**. It removes style debates.

### ESLint vs Prettier

```javascript
// ESLint says:
// ✓ Don't use var (use const)
// ✓ Don't use ==, use ===
// ✓ Add missing semicolons
// ✓ Code quality issues

// Prettier says:
// ✓ Indent with 2 spaces (or 4)
// ✓ Use single quotes (or double)
// ✓ Line length 80 characters (or 100)
// ✓ Format this code to look nice

// They complement each other!
```

### Installation & Setup

```bash
pnpm add -D prettier
```

```javascript
// .prettierrc.js (Optional - good defaults)
export default {
  semi: true,           // Add semicolons
  singleQuote: true,    // Use single quotes
  trailingComma: 'es5', // Trailing commas where valid in ES5
  tabWidth: 2,          // 2 spaces
  useTabs: false,       // Use spaces
  printWidth: 100,      // Wrap at 100 chars
  arrowParens: 'always', // Always wrap arrow function params
  bracketSpacing: true,  // { foo } not {foo}
  jsxSingleQuote: false, // JSX uses double quotes
  jsxBracketSameLine: false, // Close tag on new line
};
```

### .prettierignore

```
# .prettierignore
node_modules
dist
build
coverage
.next
pnpm-lock.yaml
```

### Running Prettier

```bash
# Check formatting
pnpm prettier --check .

# Format all files
pnpm prettier --write .

# Format specific file
pnpm prettier --write src/App.tsx

# Check specific pattern
pnpm prettier --check src/**/*.tsx
```

---

## ESLint + Prettier Integration

### The Conflict

ESLint and Prettier can have conflicting rules:

```javascript
// ESLint says: Use single quotes
const name = 'John';

// Prettier says: Use double quotes
const name = "John";

// Fight!
```

### The Solution: eslint-config-prettier

```bash
pnpm add -D eslint-config-prettier
```

```javascript
// eslint.config.js
export default [
  {
    // ... other configs
  },
  {
    // Must be last!
    extends: ['prettier'] // Disables ESLint formatting rules
  }
];
```

**How it works:**
1. ESLint checks logic and best practices
2. Prettier handles all formatting
3. No conflicts!

### Setup Script

```json
{
  "scripts": {
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check ."
  }
}
```

---

## TypeScript Integration

### TypeScript with Vite

Vite handles TypeScript automatically! No extra configuration needed:

```typescript
// src/App.tsx
import React from 'react';

interface Props {
  name: string;
  age: number;
}

export function App({ name, age }: Props) {
  return <div>{name} ({age})</div>;
}
```

Vite:
1. Detects `.ts` / `.tsx` file
2. Uses esbuild to transform TypeScript → JavaScript
3. Serves to browser
4. Strips type annotations

### TypeScript Configuration

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    // Strictness
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noImplicitThis": true,
    "alwaysStrict": true,

    // Module resolution
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    
    // Path aliases
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"],
      "@hooks/*": ["src/hooks/*"],
      "@utils/*": ["src/utils/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

### TypeScript + ESLint

```bash
pnpm add -D @typescript-eslint/parser @typescript-eslint/eslint-plugin
```

```javascript
// eslint.config.js
import ts from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';

export default [
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: './tsconfig.json',
        ecmaFeatures: { jsx: true }
      }
    },
    plugins: {
      '@typescript-eslint': ts
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-types': 'warn',
      '@typescript-eslint/no-unused-vars': 'error'
    }
  }
];
```

---

## Git Hooks with Husky

### Why Git Hooks?

Catch issues before committing:

```bash
# Without hooks
git commit -m "Add feature"  # Even if ESLint fails!

# With hooks
git commit -m "Add feature"  # Run ESLint, abort if fails
# Fix issues
git commit -m "Add feature"  # Success!
```

### Installation

```bash
pnpm add -D husky lint-staged

pnpm husky install
```

### Create Pre-commit Hook

```bash
pnpm husky add .husky/pre-commit "pnpm lint-staged"
```

### Configure lint-staged

```javascript
// package.json
{
  "lint-staged": {
    "*.{js,jsx,ts,tsx}": "eslint --fix",
    "*.{js,jsx,ts,tsx,json,md}": "prettier --write"
  }
}
```

### How It Works

```bash
# User runs:
git commit

# Git triggers pre-commit hook
# Hook runs: pnpm lint-staged

# lint-staged:
# 1. Gets list of staged files
# 2. Runs ESLint on *.ts/*.tsx files
# 3. Runs Prettier on other files
# 4. Only checks changed files (fast!)

# If all pass: commit succeeds
# If any fail: commit blocked, fix issues
```

### Other Useful Hooks

```bash
# Pre-push hook - run tests before pushing
pnpm husky add .husky/pre-push "pnpm test"

# Commit-msg hook - validate commit message format
pnpm husky add .husky/commit-msg 'pnpm commitlint --edit "$1"'
```

---

## EditorConfig

### What is EditorConfig?

EditorConfig ensures consistent coding styles **across different editors**.

```
Without EditorConfig:
- VS Code: 2 spaces
- Sublime: 4 spaces
- Vim: tabs
- Inconsistent indentation!

With EditorConfig:
- All editors: 2 spaces
- Consistency!
```

### Installation

Most editors support EditorConfig natively. Just create `.editorconfig`:

```ini
# .editorconfig
root = true

# All files
[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

# JavaScript/TypeScript
[*.{js,jsx,ts,tsx}]
indent_size = 2

# Markdown (different rules)
[*.md]
trim_trailing_whitespace = false
insert_final_newline = false
```

---

## Complete Tooling Setup

### Step-by-Step Setup

#### 1. Install All Tools

```bash
pnpm add -D \
  eslint \
  prettier \
  eslint-config-prettier \
  @typescript-eslint/parser \
  @typescript-eslint/eslint-plugin \
  eslint-plugin-react \
  eslint-plugin-react-hooks \
  husky \
  lint-staged
```

#### 2. Create ESLint Config

```javascript
// eslint.config.js
import js from '@eslint/js';
import ts from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import prettier from 'eslint-config-prettier';

export default [
  {
    ignores: ['dist', 'node_modules', '.vite', '.next']
  },
  js.configs.recommended,
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        project: './tsconfig.json'
      }
    },
    plugins: {
      '@typescript-eslint': ts,
      'react': react,
      'react-hooks': reactHooks
    },
    rules: {
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': 'error',
      '@typescript-eslint/explicit-function-return-types': 'warn'
    }
  },
  prettier
];
```

#### 3. Create Prettier Config

```javascript
// .prettierrc.js
export default {
  semi: true,
  singleQuote: true,
  trailingComma: 'es5',
  tabWidth: 2,
  useTabs: false,
  printWidth: 100
};
```

#### 4. Create EditorConfig

```ini
# .editorconfig
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true
```

#### 5. Setup Husky

```bash
pnpm husky install
pnpm husky add .husky/pre-commit "pnpm lint-staged"
```

#### 6. Configure lint-staged

```javascript
// package.json
{
  "lint-staged": {
    "*.{js,jsx,ts,tsx}": "eslint --fix",
    "*.{js,jsx,ts,tsx,json,md}": "prettier --write"
  }
}
```

#### 7. Add Scripts

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint . --max-warnings 0",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "type-check": "tsc --noEmit",
    "prepare": "husky install"
  }
}
```

---

## Common Patterns & Best Practices

### Pattern 1: VSCode Integration

```json
// .vscode/settings.json
{
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### Pattern 2: Environment-Based Rules

```javascript
// eslint.config.js - Different rules for test files
export default [
  {
    files: ['src/**/*.ts'],
    rules: {
      'no-console': 'warn'
    }
  },
  {
    files: ['**/*.test.ts', '**/*.spec.ts'],
    rules: {
      'no-console': 'off' // Logs OK in tests
    }
  }
];
```

### Pattern 3: Commit Hook Optimization

```javascript
// package.json - Only lint changed files
{
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{json,md}": "prettier --write"
  }
}
```

### Pattern 4: TypeScript Strictness Levels

```json
// tsconfig.json - Gradual strictness
{
  "compilerOptions": {
    "strict": true,
    // Override specific rules
    "noImplicitAny": false // Allow during migration
  }
}
```

### Pattern 5: Custom ESLint Rules

```javascript
// For complex projects, create custom rules:
// eslint-plugin-my-company/lib/rules/no-api-calls-in-components.js
// Then use in config
{
  "plugins": ["my-company"],
  "rules": {
    "my-company/no-api-calls-in-components": "error"
  }
}
```

---

## Common Pitfalls

### Pitfall 1: ESLint & Prettier Conflict

```javascript
// ❌ Both enabled, conflicting rules
{
  "extends": ["eslint:recommended"],
  "rules": {
    "semi": "error"  // ESLint says semicolons
  }
  // Prettier says no semicolons!
}

// ✅ Use eslint-config-prettier last
{
  "extends": ["eslint:recommended", "prettier"]
}
```

### Pitfall 2: Too Many ESLint Rules

```javascript
// ❌ Turning everything to error = constant pain
{
  "rules": {
    "@typescript-eslint/no-explicit-any": "error",
    "complexity": ["error", 5],
    "max-lines": ["error", 50]
  }
}

// ✅ Use appropriate severity levels
{
  "rules": {
    "@typescript-eslint/no-explicit-any": "warn",
    "complexity": ["warn", 10],
    "max-lines": ["warn", 300]
  }
}
```

### Pitfall 3: Ignoring Important Hooks Rules

```javascript
// ❌ Disabling hook rules = bugs
{
  "rules": {
    "react-hooks/rules-of-hooks": "off",
    "react-hooks/exhaustive-deps": "off"
  }
}

// ✅ Never disable these
// Keep them as error!
```

### Pitfall 4: Not Configuring Husky Properly

```bash
# ❌ Husky not initialized
# No .git/hooks/pre-commit, hooks don't run

# ✅ Proper setup
pnpm husky install
pnpm husky add .husky/pre-commit "pnpm lint-staged"
```

### Pitfall 5: TypeScript but No Type Checking in CI

```bash
# ❌ Only ESLint in CI
pnpm lint

# ✅ Also type-check
pnpm lint && pnpm type-check
```

---

## Resources

- **ESLint Documentation:** https://eslint.org/docs/rules/
- **Prettier Documentation:** https://prettier.io/docs/
- **TypeScript ESLint:** https://typescript-eslint.io/
- **React ESLint Rules:** https://github.com/jsx-eslint/eslint-plugin-react
- **Husky:** https://typicode.github.io/husky/
- **EditorConfig:** https://editorconfig.org/

---

**Next:** [Part 1.4: Monorepo Concepts & Setup](./01-monorepo-concepts.md) - Master monorepo architecture with TurboRepo and pnpm workspaces
