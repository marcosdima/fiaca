import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()
CONF_PATH = Path(os.environ.get("FIACA_CONFIG", "~/.fiaca.yml")).expanduser()


DEFAULT_CONFIG: dict[str, Any] = {
    "provider": "openrouter",
    "providers": {
        "openrouter": {
            "api_key_env": "OPENROUTER_API_KEY",
            "base_url": "https://openrouter.ai/api/v1",
            "default_model": "openrouter/free",
        }
    },
}


def load_config() -> dict[str, Any]:
    """Load configuration, preserving a usable default when no file exists."""
    if not CONF_PATH.exists():
        return DEFAULT_CONFIG.copy()
    with CONF_PATH.open(encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Configuration must be a YAML mapping: {CONF_PATH}")
    return loaded


def save_config(config: dict[str, Any]) -> None:
    """Save configuration and create its parent directory if necessary."""
    CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONF_PATH.open("w", encoding="utf-8") as config_file:
        yaml.safe_dump(config, config_file, sort_keys=False)
