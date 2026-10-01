"""Dynamic dependency resolver for pipeline execution.

Enables seamless test mocking on `main.<symbol>` while maintaining
modular separation of pipeline stages.
"""

import sys
from typing import Any


def resolve_dep(name: str, fallback: Any) -> Any:
    """Resolve dependency from `main` namespace if patched, otherwise return fallback."""
    main_mod = sys.modules.get("main")
    if main_mod is not None and hasattr(main_mod, name):
        return getattr(main_mod, name)
    return fallback
