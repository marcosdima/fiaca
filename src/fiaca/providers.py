from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from .config import load_config


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    api_key: str | None
    default_model: str

    def complete(
        self, messages: list[dict[str, str]], model: str | None = None, temperature: float = 0.2
    ) -> str:
        if not self.api_key and not self.base_url.startswith("http://localhost"):
            raise ValueError(
                f"No credentials configured for '{self.name}'. "
                "Set api_key_env in ~/.fiaca.yml or export the variable."
            )
        response = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": ("Bearer " + self.api_key) if self.api_key else "",
                "Content-Type": "application/json",
            },
            json={
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError(f"Unexpected response from provider '{self.name}'") from error


def provider_names() -> list[str]:
    config = load_config()
    return sorted(config.get("providers", {}))


def get_provider(name: str | None = None) -> Provider:
    config = load_config()
    provider_name = name or config.get("provider", "openrouter")
    providers = config.get("providers", {})
    settings = providers.get(provider_name)
    if not isinstance(settings, dict):
        raise ValueError(
            f"Provider '{provider_name}' is not configured. "
            f"Available providers: {', '.join(sorted(providers)) or 'none'}"
        )
    key = settings.get("api_key")
    key_env = settings.get("api_key_env")
    if not key and key_env:
        key = os.environ.get(key_env)
    return Provider(
        name=provider_name,
        base_url=str(settings.get("base_url", "")),
        api_key=key,
        default_model=str(settings.get("default_model", "")),
    )
