from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..contracts import AgentSpan, SourceRecord
from ..llm import LLMClient, PROMPT_VERSION


class StaffingWorkerAgent:
    name = "staffing_worker"
    prompt_version = PROMPT_VERSION

    def __init__(self, transcripts_dir: Path, replay: bool):
        self.llm = LLMClient(transcripts_dir, replay)

    def draft(self, record: SourceRecord, model: str) -> tuple[dict[str, Any], AgentSpan]:
        payload = asdict(record)
        response, meta = self.llm.complete_worker(payload, model)
        span = AgentSpan(
            agent=self.name,
            status="ok",
            model=model,
            prompt_version=self.prompt_version,
            tokens_in=meta["tokens_in"],
            tokens_out=meta["tokens_out"],
            cost_usd=meta["cost_usd"],
            latency_ms=meta["latency_ms"],
            retries=0,
            transcript_hash=meta["transcript_hash"],
        )
        return response, span
