"""Configuration from ``pyproject.toml`` (``[tool.rich-results-lint]``) or ``.rich-results-lint.toml``."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10
    import tomli as tomllib

CONFIG_FILES = (".rich-results-lint.toml", "pyproject.toml")
KEYS = {
    "select",
    "ignore",
    "severity",
    "features",
    "fail-on",
    "format",
    "content-checks",
    "base-url",
    "timeout",
    "user-agent",
}


class ConfigError(Exception):
    pass


def find_config(start: Path) -> Path | None:
    """The nearest config file in ``start`` or a parent directory."""
    for directory in [start, *start.parents]:
        for name in CONFIG_FILES:
            candidate = directory / name
            if candidate.is_file():
                if name == "pyproject.toml" and not _section(_read(candidate)):
                    continue
                return candidate
    return None


def load_config(path: Path) -> dict[str, Any]:
    data = _read(path)
    section = _section(data) if path.name == "pyproject.toml" else data.get("tool", {}).get("rich-results-lint", data)
    unknown = set(section) - KEYS
    if unknown:
        raise ConfigError(f"{path}: unknown option(s): {', '.join(sorted(unknown))}")
    for key in ("select", "ignore", "features"):
        if key in section and not (isinstance(section[key], list) and all(isinstance(x, str) for x in section[key])):
            raise ConfigError(f"{path}: {key} must be a list of strings")
    if "severity" in section and not isinstance(section["severity"], dict):
        raise ConfigError(f"{path}: severity must be a table of rule = level")
    return dict(section)


def _read(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc


def _section(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("tool", {}).get("rich-results-lint", {})
