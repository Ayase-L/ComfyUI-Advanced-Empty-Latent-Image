"""Resolution preset storage and validation.

User-created presets and the names of hidden built-in presets are persisted.
Built-in definitions remain in code, so removed presets can be restored.
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


def normalize_hidden_builtin_presets(value: Any) -> list[str]:
    """Validate hidden built-in names and return their canonical spelling."""
    if not isinstance(value, list):
        raise ValueError("hidden built-in presets must be an array")
    builtin_by_name = {preset["name"].casefold(): preset["name"] for preset in BUILTIN_PRESETS}
    hidden: list[str] = []
    for raw_name in value:
        key = str(raw_name).strip().casefold()
        if key not in builtin_by_name:
            raise ValueError(f"'{raw_name}' is not a built-in preset")
        name = builtin_by_name[key]
        if name not in hidden:
            hidden.append(name)
    return hidden


def _load_data() -> dict[str, Any]:
    try:
        data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_user_presets() -> list[dict[str, Any]]:
    """Load valid user presets, treating a missing/corrupt file as empty."""
    with _LOCK:
        raw_presets = _load_data().get("presets", [])
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


def load_hidden_builtin_presets() -> list[str]:
    with _LOCK:
        try:
            return normalize_hidden_builtin_presets(
                _load_data().get("hidden_builtin_presets", [])
            )
        except ValueError:
            return []


def builtin_presets() -> list[dict[str, Any]]:
    """Return all built-ins, including any that are currently hidden."""
    return [dict(preset) for preset in BUILTIN_PRESETS]


def all_presets() -> list[dict[str, Any]]:
    hidden = {name.casefold() for name in load_hidden_builtin_presets()}
    return [preset for preset in builtin_presets() if preset["name"].casefold() not in hidden] + load_user_presets()


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


def save_presets(
    presets: list[dict[str, Any]], hidden_builtin_presets: list[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate and atomically save user presets plus hidden built-in names."""
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

    hidden = normalize_hidden_builtin_presets(hidden_builtin_presets)
    payload = {
        "presets": [{key: value for key, value in p.items() if key != "builtin"} for p in normalized],
        "hidden_builtin_presets": hidden,
    }
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
    return normalized, hidden


def save_user_presets(presets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Backward-compatible user-preset save which preserves hidden built-ins."""
    saved, _hidden = save_presets(presets, load_hidden_builtin_presets())
    return saved
