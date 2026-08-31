"""Repository integrity checks — docs, assets, and security hygiene."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_logo_assets_exist():
    assert (ROOT / "assets" / "logo.png").is_file()
    assert (ROOT / "services" / "pmo-ui" / "static" / "img" / "logo.png").is_file()


def test_readme_english_default():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "**English**" in readme
    assert "README.fa.md" in readme
    assert readme.index("**English**") < readme.index("README.fa.md")


def test_readme_fa_links_english():
    readme_fa = (ROOT / "README.fa.md").read_text(encoding="utf-8")
    assert "[English](README.md)" in readme_fa


def test_env_not_committed():
    env = ROOT / ".env"
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore
    # .env may exist locally but must not be part of the repo tree for publish
    tracked = __import__("subprocess").run(
        ["git", "ls-files", ".env"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert tracked.stdout.strip() == ""


def test_github_workflow_exists():
    assert (ROOT / ".github" / "workflows" / "ci.yml").is_file()


def test_required_docs_exist():
    required = [
        "INSTALL.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "LICENSE",
        "docs/README.md",
        "docs/ARCHITECTURE.md",
        "docs/BRAND.md",
    ]
    for rel in required:
        assert (ROOT / rel).is_file(), rel


def test_models_yaml_ssot():
    text = (ROOT / "config" / "models.yaml").read_text(encoding="utf-8")
    assert "gemma-4-e4b-it-ud" in text
    assert "nomic-embed-text-v2" in text
