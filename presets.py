"""Resolution preset storage and validation.

Only user-created presets are persisted.  Built-in presets deliberately remain
in code so updating this node can safely add or correct them without mutating a
user's data file.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any


BUILTIN_PRESETS: tuple[dict[str, Any], ...] = (
    {"name": "Smartphone", "width": 1440, "height": 3200, "builtin": True},
    {"name": "Smartphone 4K", "width": 2160, "height": 4800, "builtin": True},
    {"name": "9:16 FHD", "width": 1080, "height": 1920, "builtin": True},
    {"name": "9:16 4K", "width": 2160, "height": 3840, "builtin": True},
)

PRESETS_FILE = Path(__file__).with_name("presets.json")
_LOCK = RLock()


def _positive_int(value: Any, field: str) -> int:
    # bool is an int subclass but is not a meaningful image dimension.
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a positive integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a positive integer") from exc
    if number <= 0 or str(value).strip() not in {str(number), f"{number}.0"}:
        raise ValueError(f"{field} must be a positive integer")
    return number


def normalize_preset(value: Any) -> dict[str, Any]:
    """Validate a user preset and return its JSON-safe canonical shape."""
    if not isinstance(value, dict):
        raise ValueError("preset must be an object")
    name = str(value.get("name", "")).strip()
    if not name:
        raise ValueError("preset name is required")
    if len(name) > 128:
        raise ValueError("preset name must be 128 characters or fewer")
    return {
        "name": name,
        "width": _positive_int(value.get("width"), "width"),
        "height": _positive_int(value.get("height"), "height"),
        "builtin": False,
    }


def load_user_presets() -> list[dict[str, Any]]:
    """Load valid user presets, treating a missing/corrupt file as empty."""
    with _LOCK:
        try:
            data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        raw_presets = data.get("presets", []) if isinstance(data, dict) else []
        if not isinstance(raw_presets, list):
            return []
        presets = []
        names: set[str] = set()
        for raw in raw_presets:
            try:
                preset = normalize_preset(raw)
            except ValueError:
                continue
            key = preset["name"].casefold()
            if key not in names:
                presets.append(preset)
                names.add(key)
        return presets


def all_presets() -> list[dict[str, Any]]:
    return [dict(preset) for preset in BUILTIN_PRESETS] + load_user_presets()


def preset_names() -> list[str]:
    return [preset["name"] for preset in BUILTIN_PRESETS] + [
        preset["name"] for preset in load_user_presets()
    ] + ["Custom"]


def find_preset(name: str) -> dict[str, Any] | None:
    wanted = str(name).casefold()
    for preset in all_presets():
        if preset["name"].casefold() == wanted:
            return preset
    return None


def save_user_presets(presets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and atomically save user presets, returning the saved values."""
    normalized: list[dict[str, Any]] = []
    names = {preset["name"].casefold() for preset in BUILTIN_PRESETS}
    for raw in presets:
        preset = normalize_preset(raw)
        key = preset["name"].casefold()
        if key == "custom" or key in names:
            raise ValueError(f"preset name '{preset['name']}' is reserved")
        if key in {item["name"].casefold() for item in normalized}:
            raise ValueError(f"duplicate preset name '{preset['name']}'")
        normalized.append(preset)

    payload = {"presets": [{key: value for key, value in p.items() if key != "builtin"} for p in normalized]}
    with _LOCK:
        fd, temporary_name = tempfile.mkstemp(
            prefix=".presets-", suffix=".json", dir=str(PRESETS_FILE.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temporary_name, PRESETS_FILE)
        except Exception:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise
    return normalized
