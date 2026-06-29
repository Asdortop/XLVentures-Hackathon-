"""
Adapter loader — reads YAML config files for each domain.
Supports hot-reload: call reload_adapters() after saving new adapter.
"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ADAPTERS_DIR = Path(os.getenv("ADAPTERS_DIR", "./adapters"))

_registry: dict[str, dict] = {}


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_adapter(slug: str) -> dict:
    adapter_dir = ADAPTERS_DIR / slug
    if not adapter_dir.exists():
        raise FileNotFoundError(f"Adapter not found: {slug}")

    return {
        "slug": slug,
        "schema": _load_yaml(adapter_dir / "schema.yaml"),
        "intents": _load_yaml(adapter_dir / "intents.yaml"),
        "actions": _load_yaml(adapter_dir / "actions.yaml"),
        "rules": _load_yaml(adapter_dir / "rules.yaml"),
        "knowledge": _load_yaml(adapter_dir / "knowledge.yaml"),
        "ui": _load_yaml(adapter_dir / "ui.yaml"),
    }


def reload_adapters():
    """Hot-reload all adapters from disk."""
    global _registry
    _registry = {}
    if not ADAPTERS_DIR.exists():
        return
    for slug_dir in ADAPTERS_DIR.iterdir():
        if slug_dir.is_dir():
            try:
                _registry[slug_dir.name] = load_adapter(slug_dir.name)
                print(f"[Adapter] Loaded: {slug_dir.name}")
            except Exception as e:
                print(f"[Adapter] Failed to load {slug_dir.name}: {e}")


def get_adapter(slug: str) -> dict:
    if slug not in _registry:
        _registry[slug] = load_adapter(slug)
    return _registry[slug]


def list_adapter_slugs() -> list[str]:
    if not ADAPTERS_DIR.exists():
        return []
    return [d.name for d in ADAPTERS_DIR.iterdir() if d.is_dir()]


def save_adapter_files(slug: str, files: dict[str, str]):
    """
    Save adapter YAML files to disk and hot-reload.
    files: { "schema.yaml": "...", "intents.yaml": "...", ... }
    """
    adapter_dir = ADAPTERS_DIR / slug
    adapter_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in files.items():
        (adapter_dir / filename).write_text(content, encoding="utf-8")
    # Invalidate cache
    _registry.pop(slug, None)
    print(f"[Adapter] Saved and reloaded: {slug}")


# Load on startup
reload_adapters()
