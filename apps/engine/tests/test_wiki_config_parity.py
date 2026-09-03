import json

from apps.engine.wiki_lint import validate_config_parity


def test_validate_config_parity_success(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    wiki_dir = repo_root / "wiki"
    wiki_dir.mkdir()
    config_dir = repo_root / "packages" / "config"
    config_dir.mkdir(parents=True)

    models_file = config_dir / "models.json"
    models_file.write_text(json.dumps({"DEEPSEEK_MODEL": "deepseek-v4-pro"}))

    tools_file = config_dir / "tools.json"
    tools_file.write_text(json.dumps([{"name": "get_portfolio_ledger", "desc": "Ledger"}]))

    page = wiki_dir / "tools.md"
    page.write_text("We use deepseek-v4-pro and get_portfolio_ledger tool.")

    pages = {"tools.md": page}
    errors = validate_config_parity(pages, repo_root)
    assert errors == []


def test_validate_config_parity_missing_tool(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    wiki_dir = repo_root / "wiki"
    wiki_dir.mkdir()
    config_dir = repo_root / "packages" / "config"
    config_dir.mkdir(parents=True)

    models_file = config_dir / "models.json"
    models_file.write_text(json.dumps({"DEEPSEEK_MODEL": "deepseek-v4-pro"}))

    tools_file = config_dir / "tools.json"
    tools_file.write_text(
        json.dumps(
            [
                {"name": "get_portfolio_ledger", "desc": "Ledger"},
                {"name": "missing_unregistered_tool", "desc": "Missing"},
            ]
        )
    )

    page = wiki_dir / "tools.md"
    page.write_text("We use deepseek-v4-pro and get_portfolio_ledger tool.")

    pages = {"tools.md": page}
    errors = validate_config_parity(pages, repo_root)
    assert len(errors) == 1
    assert "missing_unregistered_tool" in errors[0]


def test_validate_config_parity_missing_model(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    wiki_dir = repo_root / "wiki"
    wiki_dir.mkdir()
    config_dir = repo_root / "packages" / "config"
    config_dir.mkdir(parents=True)

    models_file = config_dir / "models.json"
    models_file.write_text(json.dumps({"NEW_MODEL": "super-model-9000"}))

    tools_file = config_dir / "tools.json"
    tools_file.write_text(json.dumps([]))

    page = wiki_dir / "tools.md"
    page.write_text("Nothing here.")

    pages = {"tools.md": page}
    errors = validate_config_parity(pages, repo_root)
    assert len(errors) == 1
    assert "super-model-9000" in errors[0]
