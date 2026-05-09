---
tags: [web, architecture, tanstack]
category: source
---

# Source: Web Application Architecture

Synthesized from `raw/docs/web/README.md`.

## Takeaways

- **Vertical Feature Slicing**: The frontend is organized into self-contained "feature slices" (`src/features/<name>`) that own their own API, components, and tests.
- **Thin Route Shells**: Routes in `src/routes/` are minimal, delegating all logic and rendering to the feature slices.
- **TanStack Ecosystem**: Heavily leverages TanStack Start, Router, and Query for a type-safe, SSR-ready experience.
- **Design System Isolation**: UI primitives are kept in a separate `ui-design-system` package, ensuring zero domain knowledge in the foundation.

## Related

- [[entities/web-app]]
- [[concepts/rag-strategy]]
