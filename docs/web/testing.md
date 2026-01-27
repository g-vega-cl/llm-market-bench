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
> Files inside `src/routes` that are not actual routes (like tests, components, or utilities) **must** be prefixed with `-` to be ignored by the TanStack Router route tree generator (e.g., `-MyComponent.test.tsx`).

### Pattern: Component Testing

Use the `*.test.tsx` suffix for component tests. Use `-*.test.tsx` if the test is located within the `src/routes` directory.

```tsx
import { render, screen } from '@testing-library/react'
import { MyComponent } from './MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText(/hello/i)).toBeInTheDocument()
  })
})
```

## 6. Best Practices

1. **Test Behavior, Not Implementation**: Focus on what the user sees and interacts with.
2. **Mocking**: Use `vi.mock()` for external dependencies like Supabase or heavy libraries.
3. **Accessibility**: Use `testing-library` queries like `getByRole` or `getByLabelText` to ensure your components are accessible.
