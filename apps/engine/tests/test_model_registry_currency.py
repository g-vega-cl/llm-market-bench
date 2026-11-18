"""Currency guard for the shared model registry.

Fails when `packages/config/models.json` drifts from the canonical vendor model
ids, when an identity list (autoresearch tracks / verifier skips) references a
model string that is not a configured model, or when a retired model id leaks
back into production code (engine, web, workflow env, shared config).

Retired ids are allowed in exactly one place: the web display-alias map, because
stored rows keep the id they actually ran under. Anywhere else they are routing
bugs.

Hermetic: reads files only, no network.
"""

import json
import os
import re
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = ENGINE_DIR.parent.parent
MODELS_JSON = REPO_ROOT / "packages" / "config" / "models.json"
WEB_MODELS_TS = REPO_ROOT / "apps" / "web" / "src" / "config" / "models.ts"

CANONICAL = {
    "OPENAI_MODEL": "gpt-6-luna",
    "ANTHROPIC_MODEL": "claude-haiku-5-5",
    "GEMINI_MODEL": "gemini-3.5-flash-lite",
    "DEEPSEEK_MODEL": "deepseek-flash",
    "DEEPSEEK_FLASH_MODEL": "deepseek-flash",
    "MINIMAX_MODEL": "MiniMax-M3.1-Flash",
}

MODEL_SLOTS = [name for name in CANONICAL if name != "DEEPSEEK_FLASH_MODEL"]

# Retired ids must not be used for routing anywhere in production code.
RETIRED_PATTERNS = [
    re.compile(r"gpt-5\.6-luna"),
    re.compile(r"deepseek-v4-flash"),
    # Exact-id match only: MiniMax-M3.1-Flash is the live successor.
    re.compile(r"MiniMax-M3(?![\w.-])"),
]

# Production surfaces scanned for retired ids.
SCAN_ROOTS = [
    "apps/engine",
    "apps/web/src",
    "packages/config",
    ".github/workflows",
]

# Only display-alias resolution may name a retired id.
RETIRED_ALLOWED_FILES = {
    "apps/web/src/config/model-aliases.ts",
}

SKIP_DIR_NAMES = {
    "__pycache__",
    "node_modules",
    ".venv",
    "dist",
    "coverage",
    ".git",
    ".scratch",
    # Tests legitimately name retired ids to assert alias/label behaviour.
    "tests",
    "__tests__",
}
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".json", ".yml", ".yaml", ".sql", ".sh", ".js"}
TEST_FILE_PREFIXES = ("test_", "conftest")


def _registry() -> dict:
    return json.loads(MODELS_JSON.read_text())


def _iter_source_files():
    for root in SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
            for name in filenames:
                if Path(name).suffix not in SOURCE_SUFFIXES:
                    continue
                if name.startswith(TEST_FILE_PREFIXES) or ".test." in name or ".spec." in name:
                    continue
                yield Path(dirpath) / name


def test_model_slots_are_canonical_ids():
    """Every configured slot points at the canonical vendor id."""
    registry = _registry()
    for slot, expected in CANONICAL.items():
        assert registry[slot] == expected, f"{slot} drifted: {registry[slot]!r} != {expected!r}"


def test_config_module_matches_registry():
    """core.config re-exports the canonical ids (no second source of truth)."""
    import core.config as config

    for slot, expected in CANONICAL.items():
        assert getattr(config, slot) == expected


def test_owner_id_lists_reference_configured_models():
    """Autoresearch tracks and verifier skips only name models we actually run."""
    registry = _registry()
    configured = {registry[slot] for slot in MODEL_SLOTS}

    experiment = set(registry.get("AUTORESEARCH_EXPERIMENT_OWNER_IDS", []))
    assert experiment <= configured, f"unknown experiment owner ids: {experiment - configured}"

    for track, owners in registry.get("AUTORESEARCH_TRACKS", {}).items():
        unknown = set(owners) - configured
        assert not unknown, f"track {track} references unknown models: {unknown}"

    skip = set(registry.get("SKIP_VERIFIER_OWNER_IDS", []))
    assert skip <= configured, f"unknown verifier-skip owner ids: {skip - configured}"

    track_models = set(registry.get("AUTORESEARCH_TRACK_MODELS", {}).values())
    assert track_models <= configured, f"unknown track models: {track_models - configured}"


def test_web_model_mirror_matches_registry():
    """apps/web/src/config/models.ts must mirror models.json."""
    registry = _registry()
    source = WEB_MODELS_TS.read_text()
    pairs = {
        "OPENAI": registry["OPENAI_MODEL"],
        "ANTHROPIC": registry["ANTHROPIC_MODEL"],
        "GEMINI": registry["GEMINI_MODEL"],
        "DEEPSEEK": registry["DEEPSEEK_MODEL"],
        "MINIMAX": registry["MINIMAX_MODEL"],
    }
    for key, value in pairs.items():
        pattern = rf"{key}:\s*'([^']+)'"
        match = re.search(pattern, source)
        assert match, f"missing {key} entry in models.ts"
        assert match.group(1) == value, f"models.ts {key}={match.group(1)!r} != registry {value!r}"


def test_no_retired_model_ids_in_production_paths():
    """Retired ids must not reappear in engine, web, workflow, or shared config code.

    `ARCHIVED_PORTFOLIO_OWNER_IDS` in models.json is the one legitimate exception:
    it names retired ids on purpose so their portfolios can be archived without
    deleting history. That key is stripped before scanning so model slots stay guarded.
    """
    offenders = []
    for path in _iter_source_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in RETIRED_ALLOWED_FILES:
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        if path == MODELS_JSON:
            try:
                registry = json.loads(text)
            except json.JSONDecodeError:
                pass
            else:
                registry.pop("ARCHIVED_PORTFOLIO_OWNER_IDS", None)
                text = json.dumps(registry, indent=2)
        for pattern in RETIRED_PATTERNS:
            for hit in pattern.finditer(text):
                line_no = text[: hit.start()].count("\n") + 1
                offenders.append(f"{rel}:{line_no} -> {hit.group(0)}")
    assert not offenders, "retired model ids in production code: " + "; ".join(offenders)


def test_archived_portfolio_ids_are_retired_models_only():
    """The archive list must only ever contain ids that are genuinely retired."""
    registry = _registry()
    archived = set(registry.get("ARCHIVED_PORTFOLIO_OWNER_IDS", []))
    assert archived, "ARCHIVED_PORTFOLIO_OWNER_IDS must not be empty while retired portfolios exist"

    configured = {registry[slot] for slot in MODEL_SLOTS}
    retired_fragments = {
        "gpt-5.6-luna",
        "deepseek-v4-flash",
        "MiniMax-M3",
        "jev-four-regime-champion",
        "jev-local-autoresearched",
    }
    for owner_id in archived:
        assert owner_id.startswith("sys-"), f"archived owner must be a system portfolio: {owner_id}"
        assert any(fragment in owner_id for fragment in retired_fragments), (
            f"archived owner references a live model id: {owner_id}"
        )
        assert not any(live in owner_id for live in configured if live != "MiniMax-M3.1-Flash"), (
            f"archived owner references a configured model: {owner_id}"
        )


def test_retired_id_allowlist_is_display_only():
    """The allowlisted file must stay a pure static display map (no routing, no I/O)."""
    aliases = REPO_ROOT / "apps/web/src/config/model-aliases.ts"
    text = aliases.read_text()
    for retired in ("gpt-5.6-luna", "deepseek-v4-flash", "minimax-m3"):
        assert retired in text.lower(), f"alias map lost {retired}: historical rows would render raw"
    assert "fetch(" not in text and "supabase" not in text, "alias map must not perform I/O"
    assert "from '~/config/models'" not in text, "alias map must not import the live registry"
