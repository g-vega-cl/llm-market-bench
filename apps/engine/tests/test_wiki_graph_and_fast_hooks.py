"""Hermetic tests for fast pre-commit hooks, QMD MCP parity, and on-demand reverse code-to-wiki graph."""

import json
from pathlib import Path

import wiki_lint

REPO_ROOT = Path(__file__).resolve().parents[3]
PRE_COMMIT = REPO_ROOT / ".husky" / "pre-commit"
ROOT_MCP = REPO_ROOT / ".mcp.json"


def test_pre_commit_excludes_slow_llm_and_gpu_embedding():
    """Pre-commit must finish deterministically in seconds without auto-wiki LLM calls or GPU qmd embed."""
    text = PRE_COMMIT.read_text()
    assert "auto-wiki.sh" not in text, "pre-commit must not invoke blocking scripts/auto-wiki.sh"
    assert "auto_wiki.py" not in text, "pre-commit must not invoke blocking auto_wiki.py"
    assert "qmd embed" not in text, "pre-commit must not run GPU qmd embed synchronously"
    assert "secret_scanner.py" in text
    assert "wiki_lint.py" in text


def test_root_mcp_registers_qmd_and_knowledge_rag():
    """Root .mcp.json must expose both qmd (with Node 24 wrapper) and knowledge-rag."""
    data = json.loads(ROOT_MCP.read_text())
    servers = data.get("mcpServers", {})
    assert "qmd" in servers, "Root .mcp.json must register the qmd MCP server"
    assert "knowledge-rag" in servers, "Root .mcp.json must retain knowledge-rag MCP server"
    qmd_args = " ".join(servers["qmd"].get("args", []))
    assert "nvm use 24" in qmd_args and "qmd mcp" in qmd_args


def test_reverse_code_to_wiki_map_identifies_affected_pages():
    """wiki_lint must map modified repo paths (including top-level scripts/) back to citing wiki pages."""
    affected = wiki_lint.affected_wiki_pages(["apps/free_llm_proxy/router.py", "scripts/qmd-garden.sh"])
    assert "entities/free-llm-proxy.md" in affected.get("apps/free_llm_proxy/router.py", [])
    assert "concepts/agentic-worktree-spine.md" in affected.get("scripts/qmd-garden.sh", [])


def test_on_demand_topic_map_preserves_orphan_detection():
    """Topic map must render on demand without persisting a wiki/_meta file that masks orphans."""
    assert not (REPO_ROOT / "wiki" / "_meta").exists(), "wiki/_meta must not persist duplicate state on disk"
    rendered = wiki_lint.render_topic_map()
    assert "apps/free_llm_proxy" in rendered
    assert "[[entities/free-llm-proxy]]" in rendered

    issues = wiki_lint.lint(fix=False)
    assert issues == [], f"Expected zero wiki_lint issues, got: {issues}"
