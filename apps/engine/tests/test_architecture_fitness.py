"""Zero-dependency Python AST architecture fitness checks with coaching error messages."""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ENGINE_ROOT = REPO_ROOT / "apps" / "engine"

ISOLATED_FROM_AUTORESEARCH = {
    "analysis",
    "analytics",
    "attribution",
    "audit",
    "execution",
    "ingest",
    "memory",
    "pipeline",
    "recipes",
    "tools",
    "trading",
}

# Standalone root-invokable CLI utilities in apps/engine/*.py that guard `try: from apps.engine... except ImportError:`
DUAL_ENTRYPOINT_SCRIPTS = {"apps/engine/wiki_lint.py", "apps/engine/sync_knowledge_db.py"}

# Local virtualenvs, vendored site-packages, caches, and scratch trees are not
# first-party engine code and may contain non-UTF-8 or generated files.
_VENDOR_PARTS = {".venv", "market", "__pycache__", "scratch"}


def _is_vendored_or_generated(path: Path) -> bool:
    """True when a path lives under a local venv, vendored tree, cache, or scratch dir."""
    return any(part in _VENDOR_PARTS for part in path.parts)


# Ratchet caps on preexisting >800 LOC legacy files so none can grow and zero new >800 LOC files can land.
LEGACY_ENGINE_LOC_CAPS: dict[str, int] = {
    "apps/engine/tests/test_autoresearch.py": 2460,
    "apps/engine/core/llm/tools.py": 2035,
    "apps/engine/local_autoresearch/double_ratchet.py": 1340,
    "apps/engine/local_autoresearch/runner.py": 1160,
    "apps/engine/local_autoresearch/single_prompt_ratchet.py": 1145,
    "apps/engine/tests/test_portfolio_auditor.py": 1140,
    "apps/engine/tasks/backtest_autoresearch.py": 1000,
    "apps/engine/execution/providers/massive.py": 970,
    "apps/engine/local_autoresearch/test_double_ratchet.py": 955,
    "apps/engine/tasks/daily_autoresearch.py": 950,
    "apps/engine/auto_wiki.py": 920,
    "apps/engine/tests/test_alpaca_broker.py": 920,
    "apps/engine/memory/store.py": 915,
    "apps/engine/tests/test_daily_predictor.py": 895,
    "apps/engine/recipes/test_push_runner.py": 825,
    "apps/engine/tests/test_verification.py": 820,
    "apps/engine/tests/test_portfolio.py": 805,
    "apps/engine/execution/sector_trading.py": 805,
}


def _imported_roots(tree: ast.AST) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.lineno, node.module))
    return found


def scan_forbidden_imports(source: str, rel_path: str) -> list[str]:
    """Return coaching violation strings for forbidden import boundaries."""
    tree = ast.parse(source, filename=rel_path)
    errors: list[str] = []
    parts = rel_path.split("/")
    pkg_name = parts[2] if len(parts) > 3 and parts[0] == "apps" and parts[1] == "engine" else ""
    is_isolated_slice = pkg_name in ISOLATED_FROM_AUTORESEARCH

    for lineno, mod in _imported_roots(tree):
        if (mod == "apps.engine" or mod.startswith("apps.engine.")) and rel_path not in DUAL_ENTRYPOINT_SCRIPTS:
            errors.append(
                f"{rel_path}:{lineno} imports `{mod}`. "
                "REMEDIATION: CI runs with working-directory=apps/engine; import relative to apps/engine "
                "(e.g., `from core.config import ...` instead of `from apps.engine.core.config import ...`)."
            )
        top = mod.split(".")[0]
        if is_isolated_slice and top in {"autoresearch", "local_autoresearch"}:
            errors.append(
                f"{rel_path}:{lineno} imports `{mod}` inside `{pkg_name}/`. "
                "REMEDIATION: Production trading/execution/recipe slices must never depend on autoresearch internals; "
                "read promoted prompt or model state via `core.config` or database contracts instead."
            )
    return errors


def scan_unconditional_skips(source: str, rel_path: str) -> list[str]:
    """Return coaching errors if a test file uses pytest.mark.skip or pytest.skip() to mask failures."""
    tree = ast.parse(source, filename=rel_path)
    errors: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "skip":
            if isinstance(node.value, ast.Attribute) and node.value.attr == "mark":
                errors.append(
                    f"{rel_path}:{node.lineno} uses `@pytest.mark.skip`. "
                    "REMEDIATION: Never silence tests with `.skip`; fix the code/mock boundary or delete obsolete tests."
                )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "skip"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in {"pytest", "unittest"}
        ):
            errors.append(
                f"{rel_path}:{node.lineno} calls `{node.func.value.id}.skip(...)`. "
                "REMEDIATION: Never skip assertions dynamically in hermetic unit tests; mock external I/O instead."
            )
    return errors


def test_engine_import_boundaries_hold():
    """All dynamically discovered production engine modules must obey import-root and slice boundaries."""
    violations: list[str] = []
    for py_file in sorted(ENGINE_ROOT.rglob("*.py")):
        if _is_vendored_or_generated(py_file) or "tests" in py_file.parts:
            continue
        if py_file.name.startswith("test_") or py_file.name.endswith("_test.py"):
            continue
        rel = str(py_file.relative_to(REPO_ROOT))
        violations.extend(scan_forbidden_imports(py_file.read_text(), rel))
    assert not violations, "Architecture import violations:\n" + "\n".join(violations)


def test_zero_skipped_tests_in_engine():
    """Engine test files must not add @pytest.mark.skip or pytest.skip()."""
    violations: list[str] = []
    for py_file in sorted(ENGINE_ROOT.rglob("*.py")):
        if _is_vendored_or_generated(py_file):
            continue
        if py_file.name.startswith("test_") or py_file.name.endswith("_test.py"):
            rel = str(py_file.relative_to(REPO_ROOT))
            violations.extend(scan_unconditional_skips(py_file.read_text(), rel))
    assert not violations, "Forbidden skipped tests detected:\n" + "\n".join(violations)


def test_engine_800_loc_hard_ceiling():
    """No new Python file in apps/engine may exceed 800 LOC, and legacy files may not grow past their cap."""
    violations: list[str] = []
    for py_file in sorted(ENGINE_ROOT.rglob("*.py")):
        if _is_vendored_or_generated(py_file):
            continue
        rel = str(py_file.relative_to(REPO_ROOT))
        lines = len(py_file.read_text().splitlines())
        cap = LEGACY_ENGINE_LOC_CAPS.get(rel, 800)
        if lines > cap:
            violations.append(
                f"{rel} is {lines} LOC (ceiling: {cap}). "
                "REMEDIATION: Extract a cohesive vertical slice helper module to stay under the 400/800 LOC budget."
            )
    assert not violations, "File size ceiling violations:\n" + "\n".join(violations)


def test_vendored_paths_are_excluded_from_fitness_scans():
    """Vendored/non-first-party trees must be skipped without hiding engine test files."""
    assert _is_vendored_or_generated(Path("apps/engine/market/lib/python3.13/site-packages/joblib/test/x.py"))
    assert _is_vendored_or_generated(Path("apps/engine/.venv/lib/python3.13/site-packages/x.py"))
    assert _is_vendored_or_generated(Path("apps/engine/__pycache__/x.py"))
    assert not _is_vendored_or_generated(Path("apps/engine/execution/portfolio.py"))
    assert not _is_vendored_or_generated(Path("apps/engine/tests/test_portfolio.py"))


def test_scanners_emit_coaching_remediation_messages():
    """Verify scanners reject synthetic violations with actionable REMEDIATION guidance."""
    bad_import = "from apps.engine.core import config\nimport autoresearch.evaluator\n"
    imp_errs = scan_forbidden_imports(bad_import, "apps/engine/execution/sample.py")
    assert len(imp_errs) == 2
    assert all("REMEDIATION:" in e for e in imp_errs)

    bad_skip = "import pytest\n@pytest.mark.skip(reason='later')\ndef test_x():\n    pytest.skip('nope')\n"
    skip_errs = scan_unconditional_skips(bad_skip, "apps/engine/tests/test_sample.py")
    assert len(skip_errs) == 2
    assert all("REMEDIATION:" in e for e in skip_errs)
