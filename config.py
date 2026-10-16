"""Configuration helpers: read the API key from the environment or a .env file."""

from __future__ import annotations

import os
from pathlib import Path


def _read_dotenv(path: Path) -> dict[str, str]:
    """Very small .env parser (KEY=VALUE per line, '#' starts a comment)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_api_key(cli_value: str | None = None, project_root: Path | None = None) -> str | None:
    """Return the YouTube API key.

    Priority: command-line value > environment variable > .env file.
    Returns None when no key is configured (the app then falls back to demo mode).
    """
    if cli_value:
        return cli_value
    env_value = os.environ.get("YOUTUBE_API_KEY")
    if env_value:
        return env_value
    root = project_root or Path(__file__).resolve().parent.parent
    return _read_dotenv(root / ".env").get("YOUTUBE_API_KEY") or None
