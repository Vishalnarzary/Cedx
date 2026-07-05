from __future__ import annotations

from typing import Any


def to_toon(obj: Any) -> str:
    """Encode JSON-like data as compact TOON-style text for model prompts."""
    lines: list[str] = []
    _emit(obj, lines, "")
    return "\n".join(lines)


def from_toon(text: str) -> dict[str, Any]:
    """Parse the flat TOON form produced by/to the Worker back into a dict."""
    data: dict[str, Any] = {}
    for raw_line in _strip_fences(text).splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        _set_path(data, key.strip(), _parse_scalar(raw_value.strip()))
    return data


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines)
    return stripped


def _emit(value: Any, lines: list[str], path: str) -> None:
    if isinstance(value, dict):
        for key in sorted(value):
            child_path = f"{path}.{key}" if path else str(key)
            _emit(value[key], lines, child_path)
        return
    if isinstance(value, list):
        if not value:
            lines.append(f"{path}: []")
            return
        for index, item in enumerate(value):
            child_path = f"{path}[{index}]"
            _emit(item, lines, child_path)
        return
    lines.append(f"{path}: {_scalar(value)}")


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    if "\n" in text:
        return repr(text)
    return text


def _parse_scalar(value: str) -> Any:
    if value == "null":
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value == "[]":
        return []
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("\"'")


def _set_path(data: dict[str, Any], path: str, value: Any) -> None:
    cursor = data
    parts = path.split(".")
    for part in parts[:-1]:
        cursor = cursor.setdefault(part, {})
    cursor[parts[-1]] = value
