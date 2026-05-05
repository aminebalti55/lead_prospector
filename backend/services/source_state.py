"""Per-source enabled flag persistence (small JSON file).

Default: every source is enabled. Disabling a source means the scheduler will
skip it when running saved searches. On-demand `POST /sources/{name}/run`
ignores this flag — explicit user action wins.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.core.config import DIRECT_OUTPUT_DIR


_STATE_FILE: Path = DIRECT_OUTPUT_DIR / "source_state.json"


def get_all() -> dict[str, bool]:
    """Return the explicit-overrides dict from disk. Defaults are NOT materialized."""
    if not _STATE_FILE.exists():
        return {}
    try:
        data = json.loads(_STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    # Coerce values to bool defensively
    return {str(k): bool(v) for k, v in data.items()}


def is_enabled(source: str) -> bool:
    """True unless this source has been explicitly disabled."""
    return get_all().get(source, True)


def set_enabled(source: str, enabled: bool) -> None:
    """Set the enabled flag for a source and persist."""
    state = get_all()
    state[source] = bool(enabled)
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2))


def toggle(source: str) -> bool:
    """Flip the enabled flag for a source. Returns the new value."""
    new_value = not is_enabled(source)
    set_enabled(source, new_value)
    return new_value
