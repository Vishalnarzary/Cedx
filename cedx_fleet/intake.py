from __future__ import annotations

import json
import re
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from .contracts import FIELD_ALIASES, SourceRecord
from .util import parse_number, sha


KEY_RE = re.compile(r"^\s*([A-Za-z][A-Za-z _-]*):\s*(.*?)\s*$")
FIELD_MAP = {alias: canonical for canonical, aliases in FIELD_ALIASES.items() for alias in aliases}


def load_seed(seed_dir: Path) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    feed = seed_dir / "feed.json"
    if feed.exists():
        for item in json.loads(feed.read_text(encoding="utf-8")):
            records.append(_record_from_fields(item, "feed", str(feed), item))
    inbox = seed_dir / "inbox"
    if inbox.exists():
        for path in sorted(inbox.iterdir()):
            if path.suffix.lower() == ".eml":
                try:
                    raw = _parse_eml(path)
                except Exception as exc:
                    raw = _parse_failed_file(path, exc)
                records.append(_record_from_fields(raw, "eml", str(path), raw))
            elif path.suffix.lower() == ".pdf":
                try:
                    raw = _parse_pdf(path)
                except Exception as exc:
                    raw = _parse_failed_file(path, exc)
                records.append(_record_from_fields(raw, "pdf", str(path), raw))
    return records


def _parse_eml(path: Path) -> dict[str, Any]:
    msg = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    body = msg.get_body(preferencelist=("plain",))
    text = body.get_content() if body else msg.get_content()
    return _parse_key_values(text)


def _parse_pdf(path: Path) -> dict[str, Any]:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - surfaced by runtime
        raise RuntimeError("pypdf is required for PDF intake") from exc
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return _parse_key_values(text)


def _parse_key_values(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for line in text.splitlines():
        match = KEY_RE.match(line)
        if not match:
            continue
        key, value = match.group(1).strip(), match.group(2).strip()
        fields[key] = value
    return fields


def _parse_failed_file(path: Path, exc: Exception) -> dict[str, Any]:
    return {
        "Id": path.stem,
        "Notes": f"Intake parse failed for {path.name}: {type(exc).__name__}",
    }


def _record_from_fields(fields: dict[str, Any], source_format: str, source_path: str, raw: dict[str, Any]) -> SourceRecord:
    lowered = {str(k).strip().lower().replace(" ", "_"): v for k, v in fields.items()}
    normalized: dict[str, Any] = {}
    notes: list[str] = []
    for key, value in lowered.items():
        canonical = FIELD_MAP.get(key)
        if canonical:
            normalized[canonical] = value
            if canonical != key:
                notes.append(f"mapped {key} to {canonical}")
    amount = parse_number(normalized.get("amount"))
    version_value = normalized.get("version", 1)
    try:
        version = int(version_value)
    except Exception:
        version = 1
    return SourceRecord(
        id=str(normalized.get("id", "")).strip(),
        owner=_clean_str(normalized.get("owner")),
        deadline=_clean_str(normalized.get("deadline")),
        amount=amount,
        category=_clean_str(normalized.get("category")),
        notes=_clean_str(normalized.get("notes")),
        version=version,
        source_format=source_format,
        source_path=source_path,
        raw_fields=raw,
        source_version_hash=sha(raw),
        normalization_notes=notes,
    )


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None
