---
tags: [web, testing, vitest]
category: source
---

# Source: Frontend Testing Infrastructure

Synthesized from `raw/docs/web/testing.md`.

## Takeaways

- **Vitest & RTL**: Uses Vitest as the runner and React Testing Library for component tests, integrated directly into the Vite build pipeline.
- **Colocation**: Tests live directly next to the components they verify within feature slices (`*.test.tsx`).
- **Behavior-Driven**: Focuses on testing user-visible outcomes rather than implementation details.
- **TDD Workflow**: Encourages a "red-green-refactor" approach for UI changes.

## Related

- [[entities/web-app]]
