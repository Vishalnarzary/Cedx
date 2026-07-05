from __future__ import annotations

import statistics
from datetime import date
import re
import os
from typing import Iterable

from .contracts import SourceRecord, VALID_CATEGORIES
from .llm import classify_note_reason


CLASS_A = {"STALE", "MISSING_INPUT", "OUTLIER", "INJECTION_BLOCKED", "LOW_CONFIDENCE", "UNVERIFIED_ANOMALY"}
CLASS_B = {"SCHEMA_DRIFT", "SUPERSEDED_VERSION"}


def select_latest_versions(records: Iterable[SourceRecord]) -> tuple[list[SourceRecord], list[SourceRecord]]:
    groups: dict[str, list[SourceRecord]] = {}
    for record in records:
        groups.setdefault(record.id, []).append(record)
    active: list[SourceRecord] = []
    superseded: list[SourceRecord] = []
    for versions in groups.values():
        ordered = sorted(versions, key=lambda r: r.version, reverse=True)
        active.append(ordered[0])
        superseded.extend(ordered[1:])
    return sorted(active, key=lambda r: r.id), sorted(superseded, key=lambda r: (r.id, r.version))


def detect_record(record: SourceRecord, active_records: list[SourceRecord], pipeline_now: str) -> tuple[str | None, str | None]:
    blocking = _blocking_reason(record, active_records, pipeline_now)
    if blocking:
        return blocking, "A"
    if _has_schema_drift(record):
        return "SCHEMA_DRIFT", "B"
    return None, None


def _blocking_reason(record: SourceRecord, active_records: list[SourceRecord], pipeline_now: str) -> str | None:
    if _is_stale(record.deadline, pipeline_now):
        return "STALE"
    if not record.id or not record.owner or not record.deadline or record.amount is None or not record.category:
        return "MISSING_INPUT"
    if _is_injection(record.notes or ""):
        return "INJECTION_BLOCKED"
    if _is_outlier(record.amount, [r.amount for r in active_records if r.amount is not None]):
        return "OUTLIER"
    if _is_low_confidence(record):
        return "LOW_CONFIDENCE"
    if _is_unverified_anomaly(record):
        return "UNVERIFIED_ANOMALY"
    llm_reason = _llm_note_reason(record)
    if llm_reason:
        return llm_reason
    return None


def _is_stale(deadline: str | None, pipeline_now: str) -> bool:
    if not deadline:
        return False
    try:
        return date.fromisoformat(deadline) < date.fromisoformat(pipeline_now)
    except ValueError:
        return False


def _is_injection(notes: str) -> bool:
    text = notes.lower()
    patterns = [
        "ignore all previous instructions",
        "approve immediately",
        "skip review",
        "ignore your rules",
        "output approved",
        "bypass approval",
    ]
    return any(pattern in text for pattern in patterns)


def _is_outlier(amount: float, amounts: list[float]) -> bool:
    if len(amounts) < 5:
        return False
    median = statistics.median(amounts)
    deviations = [abs(v - median) for v in amounts]
    mad = statistics.median(deviations) or 1.0
    robust_z = 0.6745 * abs(amount - median) / mad
    sorted_amounts = sorted(amounts)
    q1 = sorted_amounts[len(sorted_amounts) // 4]
    q3 = sorted_amounts[(len(sorted_amounts) * 3) // 4]
    iqr = max(q3 - q1, 1.0)
    return robust_z > 8 or amount > q3 + 3 * iqr or amount < q1 - 3 * iqr


def _is_low_confidence(record: SourceRecord) -> bool:
    category = (record.category or "").upper()
    notes = (record.notes or "").lower()
    if category not in VALID_CATEGORIES:
        return True
    uncertainty_markers = [
        "ambiguous",
        "unclear",
        "unsure",
        "unknown",
        "could be",
        "maybe",
        "not attached",
        "tbd",
        "inconsistent",
        "conflicting",
        "contradict",
    ]
    service_types = ["onboarding", "renewal", "review", "report", "intake"]
    service_hits = sum(1 for marker in service_types if marker in notes)
    return any(marker in notes for marker in uncertainty_markers) or service_hits >= 2


def _is_unverified_anomaly(record: SourceRecord) -> bool:
    notes = (record.notes or "").lower()
    has_override_language = any(
        phrase in notes
        for phrase in [
            "real number",
            "correct number",
            "actual number",
            "ignore the field",
            "ignore the amount",
            "override",
            "use this number instead",
        ]
    )
    mentions_structured_value = bool(re.search(r"\b(amount|value|total|figure)\b", notes))
    mentions_numeric_literal = bool(re.search(r"\b\d[\d,]*\b", notes))
    return has_override_language and (mentions_structured_value or mentions_numeric_literal)


def _has_schema_drift(record: SourceRecord) -> bool:
    return any(note.startswith("mapped ") for note in record.normalization_notes)


def _llm_note_reason(record: SourceRecord) -> str | None:
    if os.environ.get("USE_LLM_NOTE_CLASSIFIER", "false").lower() != "true":
        return None
    return classify_note_reason(record.notes or "", record.category)
