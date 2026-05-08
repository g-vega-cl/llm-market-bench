---
tags: [source, web, testing, vitest]
category: source
source: docs/web/testing.md
---

# Source: Frontend Testing Infrastructure

Vitest + React Testing Library for the web app.

Key details:

- **Stack**: Vitest (runner), jsdom (environment), @testing-library/react, @testing-library/jest-dom
- **Colocation**: Tests live next to code — `*.test.tsx` alongside components in `features/`
- **Route files**: `-` prefix rule only applies to non-route files in `src/routes/` (which no longer contain components)
- **Patterns**: Behavior-driven testing (user-visible outcomes), TDD for new features, feature API testing
- **Mocking**: `vi.mock()` for Supabase and heavy libraries, accessibility-first queries (getByRole, getByLabelText)
