from __future__ import annotations

from ..contracts import AgentSpan, SourceRecord


class RouterAgent:
    name = "router"
    prompt_version = "router-v1"
    cheap_model = "gpt-4o-mini"
    hard_model = "gemini-1.5-flash"

    def choose(self, record: SourceRecord, reason_code: str | None) -> tuple[str, AgentSpan]:
        notes = (record.notes or "").lower()
        hard = bool(reason_code) or record.amount is None or record.amount >= 10000 or any(
            marker in notes for marker in ["corrected", "partner feed", "side letter", "inconsistent"]
        )
        model = self.hard_model if hard else self.cheap_model
        detail = "hard/escalated task" if hard else "easy task"
        span = AgentSpan(
            agent=self.name,
            status="ok",
            model=None,
            prompt_version=self.prompt_version,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            latency_ms=1,
            detail=f"{detail}; selected {model}",
        )
        return model, span
