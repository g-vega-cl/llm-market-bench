# Frontend Testing Infrastructure

This document outlines the testing strategy and setup for the `apps/web` application.

## 1. Overview

We use **Vitest** as our test runner and **React Testing Library** for component testing. This combination provides a fast, modern testing experience that remains consistent with our Vite-based build system.

## 2. Tech Stack

- **Runner**: [Vitest](https://vitest.dev/)
- **Environment**: [jsdom](https://github.com/jsdom/jsdom)
- **DOM Utilities**: [@testing-library/react](https://testing-library.com/docs/react-testing-library/intro/)
- **Matchers**: [@testing-library/jest-dom](https://github.com/testing-library/jest-dom)

## 3. Getting Started

### Installation

The dependencies are already configured in `apps/web/package.json`. If you need to reinstall:

```bash
pnpm add -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react
```

### Configuration

- **`vitest.config.ts`**: Root configuration for Vitest.
- **`src/test/setup.ts`**: Global setup file that imports `jest-dom` matchers.

## 4. Running Tests

From the `apps/web` directory:

```bash
# Run all tests once
pnpm test

# Run tests in watch mode
pnpm test:watch
```

## 5. Writing Tests

We follow the **"Colocation"** principle defined in [README.md](./README.md). Tests should live next to the code they test.

> [!IMPORTANT]
> Tests inside feature slices use `*.test.tsx` alongside the component they test (e.g., `features/today/components/MarketStatusHero.test.tsx`). No `-` prefix is needed — `features/` is **not** a TanStack Router directory.
>
> The `-` prefix rule only applies to non-route files inside `src/routes/` (e.g., `-utils.ts`). Routes should no longer contain components or tests — those live in `features/`.

### Pattern: Feature-Colocated Component Testing

```tsx
// features/today/components/MarketStatusHero.test.tsx
import { render, screen } from '@testing-library/react'
import { MarketStatusHero } from './MarketStatusHero'

describe('MarketStatusHero', () => {
  it('shows market status indicator', () => {
    render(<MarketStatusHero isOpen={true} />)
    expect(screen.getByText(/market open/i)).toBeInTheDocument()
  })
})
```

### Pattern: Test-Driven Development (TDD)

We follow TDD for new features and UI changes. Write a failing test first, make it pass with the minimal implementation, then refactor.

**Example:** Adding an LLM name label to Lesson Learned cards.

1. **Write the failing test** (`AgentInsights.test.tsx`):

```tsx
it('renders agent name text for known model', () => {
  render(<AgentInsights memories={[createLessonMemory('example-model-preview')]} />)
  expect(screen.getByText('ExampleProvider')).toBeInTheDocument()
})
```

2. **Run the test — confirm it fails**:

```bash
pnpm vitest run src/features/today/components/AgentInsights.test.tsx
```

3. **Implement the minimal change** (`AgentInsights.tsx`):

```tsx
<span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">
  {lessonAgent.name}
</span>
```

4. **Run the test again — confirm it passes**, then run the full suite to prevent regressions.

> See `features/today/components/AgentInsights.test.tsx` for the complete test file covering all known LLM agents, missing metadata, and edge cases.

### Pattern: Feature API Testing

```tsx
// features/portfolios/api/fetch-portfolios.test.ts
import { describe, it, expect } from 'vitest'
import { fetchPortfolios } from './fetch-portfolios'

describe('fetchPortfolios', () => {
  it('returns portfolio list', async () => {
    const result = await fetchPortfolios()
    expect(result.data).toBeDefined()
  })
})
```

## 6. Best Practices

1. **Test Behavior, Not Implementation**: Focus on what the user sees and interacts with.
2. **Mocking**: Use `vi.mock()` for external dependencies like Supabase or heavy libraries.
3. **Accessibility**: Use `testing-library` queries like `getByRole` or `getByLabelText` to ensure your components are accessible.
