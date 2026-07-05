from __future__ import annotations

from typing import Any

from ..contracts import AgentSpan, SourceRecord


class VerifierAgent:
    name = "verifier"
    prompt_version = "verifier-v1"
    model = "gpt-4o-mini"

    def verify(self, record: SourceRecord, worker_response: dict[str, Any]) -> tuple[bool, str | None, AgentSpan]:
        fields = worker_response.get("delivered_fields")
        if not isinstance(fields, dict):
            return False, "AGENT_MALFORMED", self._span("rejected", "fail", "worker output is not structured JSON")
        required = ["case_id", "owner", "deadline", "service_line", "work_order_amount", "source_version"]
        if any(field not in fields for field in required):
            return False, "AGENT_MALFORMED", self._span("rejected", "fail", "missing required delivered field")
        supported = {
            "case_id": record.id,
            "owner": record.owner,
            "deadline": record.deadline,
            "service_line": record.category,
            "work_order_amount": record.amount,
            "source_version": record.version,
        }
        for key, expected in supported.items():
            if fields.get(key) != expected:
                return False, "AGENT_HALLUCINATION", self._span("overruled", "fail", f"{key} not supported by source")
        if worker_response.get("unsupported_claims"):
            return False, "AGENT_HALLUCINATION", self._span("overruled", "fail", "worker admitted unsupported claims")
        return True, None, self._span("ok", "pass", "worker output grounded in source")

    def _span(self, status: str, verdict: str, detail: str) -> AgentSpan:
        return AgentSpan(
            agent=self.name,
            status=status,
            model=self.model,
            prompt_version=self.prompt_version,
            tokens_in=80,
            tokens_out=30,
            cost_usd=0.00003,
            latency_ms=12,
            retries=0,
            verdict=verdict,
            detail=detail,
        )
