---
tags: [wayfinder, planning, methodology, agent-skill]
category: concept
---

# Wayfinder Planning Skill

Wayfinder is a planning methodology for decomposing large, ambiguous work into a shared map of **decision tickets** on the issue tracker. Instead of charging at the destination, wayfinding charts the route one decision at a time, resolving each ticket until the path is clear enough to hand off for execution.

## Core Concepts

- **Destination**: The goal of the effort (spec, decision, or change). It is named first and fixes the scope.
- **Map**: A single issue labeled `wayfinder:map` that serves as the canonical artifact. It contains the destination, notes, decisions-so-far index, fog of war, and out-of-scope items.
- **Tickets**: Child issues of the map, each resolving one question sized to a single agent session. Each ticket has a type (research, prototype, grilling, task) and a `wayfinder:<type>` label.
- **Fog of war**: The dim view of decisions that are in scope but not yet sharp enough to ticket. Written in the map’s **Not yet specified** section.
- **Out of scope**: Work ruled beyond the destination. Written in the **Out of scope** section; never graduates unless the destination is redrawn.

## Ticket Types

| Type | HITL/AFK | Purpose |
|------|----------|---------|
| Research | AFK | Read documentation, APIs, or knowledge bases to surface a fact. |
| Prototype | HITL | Create a cheap, rough artifact (outline, stub, UI/logic code) to react to. |
| Grilling | HITL | Conversation to resolve a question through discussion. |
| Task | AFK or HITL | Manual work (signing up, provisioning, moving data) that unblocks a decision. |

## Invocation

Two modes:

1. **Chart the map** — When a loose idea arrives, name the destination, map the frontier breadth-first, create the map and tickets, then fire research subagents in parallel. Stop after charting.
2. **Work through the map** — Given an existing map, claim a frontier ticket, resolve it (zoom, record answer, close), update the map (graduate fog, rule out-of-scope items), and create any new tickets surfaced. Never resolve more than one ticket per session (except research).

## Related

- [[concepts/agents]] — Comprehensive agent roles and tools
- [[concepts/agent-workflow]] — Mandatory Search/Plan/TDD sequence
- [[concepts/visual-planning]] — Terminal-native visual planning tools
