---
tags: [testing, dependency-injection, pipeline, mocking]
category: concept
---

# Dependency Resolver

`pipeline/resolver.py` exposes a single helper, `resolve_dep(name, fallback)`, that lets the decomposed pipeline stages remain modular while preserving the ability to patch dependencies on the `main` module namespace.

## The Problem

When pipeline orchestration was extracted out of `apps/engine/main.py` into `apps/engine/pipeline/`, existing hermetic test suites that patched symbols like `main.analyze_chunks` or `main.Portfolio` would have broken — the stages no longer referenced those names through `main`.

## The Mechanism

python
def resolve_dep(name: str, fallback: Any) -> Any:
    main_mod = sys.modules.get("main")
    if main_mod is not None and hasattr(main_mod, name):
        return getattr(main_mod, name)
    return fallback


At call time, a stage asks for a dependency by name. If the `main` module is loaded and exposes that attribute (i.e. a test has patched it), the patched value is returned; otherwise the stage falls back to its own direct import.

## Usage

Stages and the decision processor resolve their collaborators through this helper rather than importing them at module scope:

python
log = resolve_dep("logger", logger)
analyze_fn = resolve_dep("analyze_chunks", analyze_chunks)
portfolio_cls = resolve_dep("Portfolio", Portfolio)


`main.py` re-exports the same symbols in its `__all__` so that `main.<symbol>` patching continues to work.

## Trade-offs

- **Pro**: zero-cost backwards compatibility for the existing test suite; stages stay independently importable.
- **Con**: indirection is invisible at the call site — a reader must know that `resolve_dep` may return a patched value. It is a test seam, not a general-purpose DI container.

## Related

- [[entities/pipeline]] — the orchestration layer that uses this resolver
- [[entities/cli]] — the sibling decomposition of the entry point
- [[concepts/vertical-slice-islands]] — the broader decomposition strategy
