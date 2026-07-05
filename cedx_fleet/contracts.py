from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


REQUIRED_FIELDS = ["id", "owner", "deadline", "amount", "category", "notes", "version"]
VALID_CATEGORIES = {"ONBOARDING", "RENEWAL", "REVIEW", "REPORT", "INTAKE"}

FIELD_ALIASES = {
    "id": ["id", "record_id", "request_id", "case_id", "work_request_id"],
    "owner": ["owner", "assignee", "requester", "manager", "coordinator"],
    "deadline": ["deadline", "due", "due_date", "target_date"],
    "amount": ["amount", "value", "total", "price", "cost", "fee", "figure"],
    "category": ["category", "type", "service_line", "request_type"],
    "version": ["version", "revision", "rev"],
    "notes": ["notes", "description", "comments", "details", "summary"],
}


@dataclass
class SourceRecord:
    id: str
    owner: str | None
    deadline: str | None
    amount: float | None
    category: str | None
    notes: str | None
    version: int
    source_format: str
    source_path: str
    raw_fields: dict[str, Any]
    source_version_hash: str
    normalization_notes: list[str] = field(default_factory=list)


@dataclass
class AgentSpan:
    agent: str
    status: str
    model: str | None = None
    prompt_version: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    latency_ms: float | None = None
    retries: int | None = 0
    transcript_hash: str | None = None
    verdict: str | None = None
    detail: str | None = None

    def to_json(self) -> dict[str, Any]:
        data = {
            "agent": self.agent,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "retries": self.retries,
            "transcript_hash": self.transcript_hash,
            "status": self.status,
            "verdict": self.verdict,
        }
        if self.detail:
            data["detail"] = self.detail
        return data


def agent_roster() -> list[dict[str, Any]]:
    return [
        {
            "name": "orchestrator",
            "role": "orchestrator",
            "models": [],
            "prompt_version": "orchestrator-v1",
            "can_call": ["router", "staffing_worker", "verifier"],
        },
        {
            "name": "router",
            "role": "router",
            "models": [],
            "prompt_version": "router-v1",
            "can_call": [],
        },
        {
            "name": "staffing_worker",
            "role": "worker",
            "models": ["gpt-4o-mini", "gemini-1.5-flash"],
            "prompt_version": "staffing-worker-v1",
            "can_call": [],
        },
        {
            "name": "verifier",
            "role": "verifier",
            "models": ["gpt-4o-mini"],
            "prompt_version": "verifier-v1",
            "can_call": [],
        },
    ]
