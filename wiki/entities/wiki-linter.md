---
tags: [wiki, lint, tooling, python]
category: entity
---

# Wiki Linter

`apps/engine/wiki_lint.py` is the structural lint layer for the wiki. It runs
in ~20ms with no API cost and is invoked on every commit via a pre-commit hook.

## Checks

- **Frontmatter completeness** — every page must declare `tags` and `category`.
- **Broken links** — every wiki cross-reference must resolve to a real file.
- **Orphan pages** — every page needs at least one inbound link.
- **Index coverage gaps** — pages listed in `index.md` must exist and vice versa.

## Link Resolution

`resolve_link` converts a wikilink target into a relative path from `wiki/`.

- Plain targets get a `.md` suffix if missing (e.g. `[[entities/engine]]` →
  `entities/engine.md`).
- **Aliased targets** are supported: the pipe segment is stripped before
  resolution, so `[[entities/engine|the engine]]` resolves against
  `entities/engine.md` and renders with the display alias in Obsidian.

Resolution is done via `WIKI_DIR / target`; unresolvable targets return `None`
and surface as broken-link findings.

## Related

- [[entities/auto-wiki]] — the agent that produces wiki edits this linter verifies
- [[concepts/wiki-synchronization]] — the workflow this linter backs
- [[entities/engine]]
