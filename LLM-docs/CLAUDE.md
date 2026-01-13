## Repository Structure

This is a multi-project development workspace containing several distinct codebases:

### Major Projects

1. **infra-monorepo** - Infrastructure-as-code monorepo using Terraform, Helm, and ArgoCD
2. **ui-services** - NestJS backend-for-frontend service
3. **usm-native-app** - React Native mobile application
4. **usmobile-mobile-gateway** - Java/Gradle mobile gateway service
5. **web-app** - React PWA dashboard application
6. **test-end-2-end** - Cypress E2E testing suite with desktop and mobile test support
7. **docs** - Project documentation repository for multiple projects

## Common Commands by Project

### infra-monorepo
```bash
./setup.sh           # Quick setup
# Uses Gradle build system - check gradle wrapper scripts
```

### ui-services (NestJS)
```bash
yarn install         # Install dependencies
yarn start:dev       # Development mode
yarn start:prod      # Production mode
yarn build           # Build the project
yarn test            # Unit tests
yarn test:e2e        # E2E tests
yarn test:cov        # Test coverage
yarn lint            # Lint code
```

### usm-native-app (React Native)
```bash
yarn install         # Install dependencies
yarn start           # Start Metro bundler
yarn android         # Run on Android
yarn ios             # Run on iOS
yarn test            # Run tests
yarn lint            # Lint code
yarn fresh           # Clean reinstall with pods
yarn superfresh      # Deep clean and reinstall
yarn sentry:setup    # Generate sentry.properties from .env
```

### web-app (React PWA)
```bash
# Installation & Setup
yarn install:all                 # Install all dependencies (root + shop + marketing)
yarn reset-deps                  # Reset and reinstall all dependencies

# Development
yarn start:webapp                # Start webapp dev server
yarn start:webapp:partial        # Start webapp with partial environment
yarn start:shop                  # Start shop dev server
yarn start:shop:partial          # Start shop with partial environment
yarn start:marketing             # Start marketing dev server
yarn start:marketing:partial     # Start marketing with partial environment
yarn start:demo                  # Start demo environment

# Build
yarn build:webapp                # Build webapp for production
yarn build:shop                  # Build shop for production
yarn build:marketing             # Build marketing for production
yarn build:all                   # Build webapp, shop, and marketing
yarn build:demo                  # Build demo environment

# Serve Production Builds
yarn serve:webapp:production     # Serve webapp production build (port 3002)
yarn serve:shop:production       # Serve shop production build
yarn serve:marketing:production  # Serve marketing production build

# Testing
yarn test                        # Run all tests (jest-pwa)
yarn test:jest-pwa               # Run jest tests with coverage
yarn test:jest-pwa:dev           # Run jest in watch mode (no coverage)
yarn test:clearCache             # Clear jest cache

# Linting & Formatting
yarn lint                        # Lint all files
yarn lint:fix                    # Lint and auto-fix issues
yarn format                      # Format all files with prettier
yarn lint:format                 # Run lint:fix and format together
```

### test-end-2-end (Cypress E2E)
```bash
# Installation
yarn install         # Install dependencies

# Interactive Mode
yarn open            # Open Cypress UI (all tests)
yarn open:desktop    # Open Cypress UI (desktop tests only)
yarn open:mobile     # Open Cypress UI (mobile tests only)
yarn open:utils      # Open utility tests

# Running Tests
yarn test            # Run all tests
yarn test:desktop    # Run desktop tests only (excludes @mobile tagged tests)
yarn test:mobile     # Run mobile tests only (@mobile tagged tests)
yarn test:api        # Run API tests
yarn run:utils       # Run utility tests

# Advanced Cypress Commands
npx cypress open     # Direct Cypress UI
npx cypress run --spec "cypress/e2e/UAT/04_pool_activation_att_esim_plan_builder.cy.ts" --env version=uat,grepTags=-@mobile --browser chrome --headed

# Reporting
yarn report          # Generate JUnit report
```

## AI Agent Rules & Workflow

### Additional Rule Categories

1. **Google Best Practices** - `.cursor/rules/google-best-practices/`
   - TypeScript/JavaScript code standards
   - Naming conventions
   - Documentation requirements
   - Type system usage

2. **Code Review Guidelines** - `.cursor/rules/reviews/`
   - Review checklist and standards

### Tool Selection Priority

**Documentation/URL Content:**
- ✅ Use `web-docs-extractor` agent (when user provides URL to read/extract)
  - The agent automatically uses the `web-fetch` skill with smart-fetch.js for optimal extraction
  - Supports authentication, auto-fallback (HTTP → Browser → Screenshot), and all content types
- ❌ Don't use WebFetch tool directly
- ❌ Don't invoke `web-fetch` skill directly (let the agent handle it)
- ❌ Don't use manual browser automation

**Codebase Exploration:**
- ✅ Use `Explore` agent (for open-ended exploration like "how does X work?")
- ❌ Don't use Grep/Glob directly for exploratory questions

---

## Collaboration Protocol

**Mode: Clarify → Plan → Implement → Verify**

### 0. Clarification (Always First)

For every request—no exceptions:
- Ask **numbered clarifying questions** to remove ambiguity
- Request **examples** if output format is unclear
- Confirm scope, **constraints**, **non-goals**, and "done" definition
- Proceed only **after** user responds

### 1. Planning (Adjacent Possible)

**Principle:** Small steps, not leaps. Each step must be verifiable.

- Extract requirements, constraints, and unknowns
- Define success criteria as **oracles** (tests, benchmarks, checks that decide success)
- Break work into **small, ordered subtasks**—each independently verifiable
- Identify **repo anchors**: existing files, patterns, and prior art to reuse
- Outline 2-3 approaches with trade-offs (select one)
- **PAUSE** and wait for confirmation before implementation

### 2. Implementation (Strict Scope)

- Execute **ONLY** what is explicitly requested
- **Reuse existing patterns**—cite prior art; don't invent new abstractions without justification
- Keep diffs **small and reviewable**
- Touch only specified elements; preserve existing code outside scope
- Remove imports/variables only when directly affected
- Address linter errors only in modified lines

### 3. Verification Loop (Error as Steering)

After each change:
1. Run tests/checks (the oracle)
2. If failures: fix and re-run (don't batch fixes)
3. Repeat until green
4. Status: **PASS**, **NEEDS_IMPROVEMENT**, or **FAIL**

If not PASS, identify **root cause** (not symptoms), fix, and re-verify.

### 4. Completion Checklist

- [ ] Clarifications resolved
- [ ] Plan confirmed by user
- [ ] Existing patterns reused (or new abstraction justified)
- [ ] All oracles pass (tests, lints, benchmarks)
- [ ] Diff is minimal and focused

---

## Context Packet (For Non-Trivial Tasks)

When starting complex work (reliability, perf, migrations, refactors), create or request:

| Field | Description |
|-------|-------------|
| **Goal** | One sentence: the outcome, not the mechanism |
| **Non-goals** | Explicitly out of scope (kills "helpful creativity") |
| **Constraints** | Hard requirements: budgets, safety, compatibility, forbidden actions |
| **Authority order** | When sources conflict: `tests/CI > code > docs > lore` |
| **Repo anchors** | 3-10 files defining truth: entrypoints, types, helpers, config |
| **Prior art** | Patterns to copy, abstractions to reuse |
| **Oracle** | Definition of done: tests to pass, edge cases, benchmarks |
| **Risk/Rollback** | How it could fail, what to watch, how to undo |

**Why:** Turns implicit senior intuition into explicit constraints. Agents stop guessing, reviews focus on invariants instead of vibes

