from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import PIPELINE_VERSION
from .agents.router import RouterAgent
from .agents.verifier import VerifierAgent
from .agents.worker import StaffingWorkerAgent
from .amendment import compute_amendment
from .audit import AuditEvents
from .contracts import AgentSpan, SourceRecord, agent_roster
from .detectors import CLASS_A, detect_record, select_latest_versions
from .intake import load_seed
from .review import blocked_approval_trail, can_deliver, delivered_approval_trail
from .util import ensure_dir, sha, sha_text, utc_now, write_json


class Orchestrator:
    name = "orchestrator"
    prompt_version = "orchestrator-v1"

    def __init__(self, seed_dir: Path, out_dir: Path, transcripts_dir: Path):
        self.seed_dir = seed_dir
        self.out_dir = ensure_dir(out_dir)
        self.transcripts_dir = ensure_dir(transcripts_dir)
        self.replay = os.environ.get("REPLAY_LLM", "true").lower() != "false"
        self.case_id = os.environ.get("CASE_ID", "CEDX-681ACE")
        self.pipeline_now = os.environ.get("PIPELINE_NOW", "2026-06-26")
        self.max_steps = int(os.environ.get("MAX_STEPS_PER_RECORD", "6"))
        self.max_cost = float(os.environ.get("MAX_COST_USD_PER_RECORD", "0.02"))
        self.amendment = compute_amendment(self.case_id)
        self.events = AuditEvents()
        self.router = RouterAgent()
        self.worker = StaffingWorkerAgent(self.transcripts_dir, self.replay)
        self.verifier = VerifierAgent()

    def run(self) -> dict[str, Any]:
        print(f"AMENDMENT: role={self.amendment['role']} threshold={self.amendment['threshold']}")
        self.events.append("orchestrator", "run_started", None, seed_dir=str(self.seed_dir))
        raw_records = load_seed(self.seed_dir)
        write_json(self.out_dir / "intake_records.json", [asdict(record) for record in raw_records])
        active, superseded = select_latest_versions(raw_records)
        records_json: list[dict[str, Any]] = []
        delivered_payloads: list[dict[str, Any]] = []

        for record in superseded:
            records_json.append(self._superseded_record(record))
            self.events.append("orchestrator", "record_superseded", record.id, version=record.version)

        for record in active:
            processed = self._process_active_record(record, active)
            records_json.append(processed)
            if processed["status"] == "delivered":
                delivered_payloads.append(processed["delivered_fields"])

        package_path = self._write_package(delivered_payloads)
        audit = self._build_audit(records_json, package_path)
        self.events.append("orchestrator", "run_completed", None)
        audit["events"] = self.events.events
        write_json(self.out_dir / "audit.json", audit)
        exceptions = [r for r in records_json if r["status"] == "exception"]
        write_json(self.out_dir / "exception_queue.json", exceptions)
        return audit

    def _process_active_record(self, record: SourceRecord, active: list[SourceRecord]) -> dict[str, Any]:
        trace: list[AgentSpan] = [
            AgentSpan(
                agent=self.name,
                status="ok",
                model=None,
                prompt_version=self.prompt_version,
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                latency_ms=1,
                detail="record accepted from intake",
            )
        ]
        reason_code, reason_class = detect_record(record, active, self.pipeline_now)
        if reason_code in CLASS_A:
            trace.append(
                AgentSpan(
                    agent=self.name,
                    status="routed",
                    model=None,
                    prompt_version=self.prompt_version,
                    tokens_in=0,
                    tokens_out=0,
                    cost_usd=0.0,
                    latency_ms=1,
                    detail=f"routed to exception queue: {reason_code}",
                )
            )
            self.events.append("orchestrator", "record_exception", record.id, reason_code=reason_code)
            return self._record_json(record, "exception", reason_code, reason_class, trace, None, None, blocked_approval_trail(reason_code))

        model, router_span = self.router.choose(record, reason_code)
        trace.append(router_span)
        if len(trace) + 2 > self.max_steps:
            trace.append(AgentSpan(agent=self.name, status="killed", prompt_version=self.prompt_version, detail="step budget exceeded"))
            return self._record_json(record, "exception", "BUDGET_EXCEEDED", "A", trace, None, None, blocked_approval_trail("BUDGET_EXCEEDED"))

        response, worker_span = self.worker.draft(record, model)
        trace.append(worker_span)
        cost_so_far = sum(span.cost_usd or 0 for span in trace)
        if cost_so_far > self.max_cost:
            trace.append(AgentSpan(agent=self.name, status="routed", prompt_version=self.prompt_version, detail="cost budget exceeded"))
            return self._record_json(record, "exception", "BUDGET_EXCEEDED", "A", trace, None, None, blocked_approval_trail("BUDGET_EXCEEDED"))

        ok, agent_reason, verifier_span = self.verifier.verify(record, response)
        trace.append(verifier_span)
        if not ok:
            reason = agent_reason or "AGENT_MALFORMED"
            self.events.append("verifier", "worker_overruled", record.id, reason_code=reason)
            return self._record_json(record, "exception", reason, "A", trace, None, worker_span.transcript_hash, blocked_approval_trail(reason))

        fields = response["delivered_fields"]
        approval = delivered_approval_trail(record.amount, self.amendment)
        allowed, refusal_reason = can_deliver(approval, record.amount, self.amendment)
        if not allowed:
            self.events.append("delivery", "delivery_refused", record.id, reason=refusal_reason)
            return self._record_json(record, "exception", "UNVERIFIED_ANOMALY", "A", trace, None, worker_span.transcript_hash, blocked_approval_trail("UNVERIFIED_ANOMALY"))
        self.events.append("delivery", "record_delivered", record.id, model=model)
        return self._record_json(record, "delivered", reason_code, reason_class, trace, fields, worker_span.transcript_hash, approval)

    def _record_json(
        self,
        record: SourceRecord,
        status: str,
        reason_code: str | None,
        reason_class: str | None,
        trace: list[AgentSpan],
        delivered_fields: dict[str, Any] | None,
        transcript_hash: str | None,
        approval_trail: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "id": record.id,
            "version": record.version,
            "source_format": record.source_format,
            "source_version_hash": record.source_version_hash,
            "status": status,
            "reason_code": reason_code,
            "reason_class": reason_class,
            "transcript_hash": transcript_hash,
            "delivered_fields": delivered_fields,
            "delivered_fields_hash": sha(delivered_fields) if delivered_fields is not None else None,
            "agent_trace": [span.to_json() for span in trace],
            "approval_trail": approval_trail,
        }

    def _superseded_record(self, record: SourceRecord) -> dict[str, Any]:
        return self._record_json(
            record,
            "superseded",
            "SUPERSEDED_VERSION",
            "B",
            [],
            None,
            None,
            [{"state": "blocked", "actor": "orchestrator", "ts": utc_now(), "reason": "SUPERSEDED_VERSION"}],
        )

    def _write_package(self, delivered_payloads: list[dict[str, Any]]) -> Path:
        lines = [
            "# CEDX Recruitment and Staffing Delivery Package",
            f"CASE_ID: {self.case_id}",
            f"Generated: {utc_now()}",
            "",
        ]
        for payload in sorted(delivered_payloads, key=lambda p: p["case_id"]):
            lines.append(f"## {payload['case_id']}")
            lines.append(f"- Owner: {payload['owner']}")
            lines.append(f"- Deadline: {payload['deadline']}")
            lines.append(f"- Service line: {payload['service_line']}")
            lines.append(f"- Work order amount: {payload['work_order_amount']}")
            lines.append(f"- Summary: {payload['staffing_summary']}")
            lines.append("")
        path = self.out_dir / "recruitment_staffing_package.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _build_audit(self, records_json: list[dict[str, Any]], package_path: Path) -> dict[str, Any]:
        costs = [span.get("cost_usd") or 0 for record in records_json for span in record.get("agent_trace", [])]
        latencies = [span.get("latency_ms") or 0 for record in records_json for span in record.get("agent_trace", [])]
        total = round(sum(costs), 8)
        p95 = percentile(latencies, 95)
        package_hash = sha_text(package_path.read_text(encoding="utf-8"))
        return {
            "case_id": self.case_id,
            "pipeline_version": PIPELINE_VERSION,
            "generated_at": utc_now(),
            "seed_dir": str(self.seed_dir),
            "pipeline_now": self.pipeline_now,
            "amendment": self.amendment,
            "agents": agent_roster(),
            "cost": {
                "total_usd": total,
                "avg_usd_per_record": round(total / max(1, len(records_json)), 8),
                "p95_latency_ms": p95,
                "records": len(records_json),
                "projected_usd_per_10k": round((total / max(1, len(records_json))) * 10000, 4),
            },
            "output_package_hash": package_hash,
            "records": sorted(records_json, key=lambda r: (r["id"], r.get("version") or 0, r["status"])),
            "events": [],
        }


def percentile(values: list[float], pct: int) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round((pct / 100) * (len(ordered) - 1))))
    return ordered[idx]
