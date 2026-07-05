from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .agents.verifier import VerifierAgent
from .amendment import compute_amendment
from .audit import AuditEvents
from .contracts import SourceRecord
from .eval_harness import run_eval_harness
from .orchestrator import Orchestrator
from .review import can_deliver
from .util import read_json, write_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cedx-fleet")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    trace = sub.add_parser("trace")
    trace.add_argument("--id", required=True)
    replay = sub.add_parser("replay")
    replay.add_argument("--id", required=True)
    sub.add_parser("eval")
    sub.add_parser("probe-approval")
    sub.add_parser("probe-agent-failure")
    sub.add_parser("probe-budget")
    sub.add_parser("probe-append-only")
    sub.add_parser("probe-idempotency")
    args = parser.parse_args(argv)

    if args.cmd == "demo":
        return run_demo()
    if args.cmd == "trace":
        return print_trace(args.id)
    if args.cmd == "replay":
        return print_replay(args.id)
    if args.cmd == "eval":
        return run_eval()
    if args.cmd == "probe-approval":
        return probe_approval()
    if args.cmd == "probe-agent-failure":
        return probe_agent_failure()
    if args.cmd == "probe-budget":
        return probe_budget()
    if args.cmd == "probe-append-only":
        return probe_append_only()
    if args.cmd == "probe-idempotency":
        return probe_idempotency()
    return 2


def run_demo() -> int:
    seed_dir = Path(os.environ.get("SEED_DIR", "seed"))
    audit = Orchestrator(seed_dir, Path("out"), Path("transcripts")).run()
    delivered = len([r for r in audit["records"] if r["status"] == "delivered"])
    exceptions = len([r for r in audit["records"] if r["status"] == "exception"])
    print(f"Demo complete: {delivered} delivered, {exceptions} exceptions, cost=${audit['cost']['total_usd']:.6f}")
    return 0


def print_trace(record_id: str) -> int:
    audit = _load_audit()
    record = _find_record(audit, record_id)
    print(f"Trace for {record_id} ({record['status']}, reason={record.get('reason_code')}):")
    for i, span in enumerate(record.get("agent_trace", []), 1):
        print(
            f"{i}. {span['agent']} status={span['status']} model={span.get('model')} "
            f"cost={span.get('cost_usd')} verdict={span.get('verdict')} detail={span.get('detail')}"
        )
    return 0


def print_replay(record_id: str) -> int:
    audit = _load_audit()
    record = _find_record(audit, record_id)
    print(f"Lineage for {record_id}:")
    print(f"- source hash: {record.get('source_version_hash')}")
    print(f"- transcript: {record.get('transcript_hash')}")
    print(f"- delivered hash: {record.get('delivered_fields_hash')}")
    for event in audit.get("events", []):
        if event.get("record_id") == record_id:
            print(f"- event {event['seq']}: {event['actor']} {event['action']} at {event['ts']}")
    return 0


def run_eval() -> int:
    ok, report = run_eval_harness()
    print(report)
    return 0 if ok else 1


def probe_approval() -> int:
    amendment = compute_amendment(os.environ.get("CASE_ID", "CEDX-681ACE"))
    ok, reason = can_deliver([], amendment["threshold"] + 1, amendment)
    Path("out/probes").mkdir(parents=True, exist_ok=True)
    write_json(Path("out/probes/probe_approval.json"), {"allowed": ok, "reason": reason, "amendment": amendment})
    if ok:
        print("FAIL: non-approved delivery was allowed")
        return 1
    print(f"PASS: delivery refused ({reason})")
    return 0


def probe_agent_failure() -> int:
    verifier = VerifierAgent()
    record = SourceRecord(
        id="PROBE-AGENT",
        owner="probe.owner",
        deadline="2026-08-01",
        amount=5000.0,
        category="RENEWAL",
        notes="Probe record",
        version=1,
        source_format="feed",
        source_path="probe",
        raw_fields={},
        source_version_hash="sha256:" + "0" * 64,
    )
    hallucinated = {
        "delivered_fields": {
            "case_id": "PROBE-AGENT",
            "owner": "someone.else",
            "deadline": "2026-08-01",
            "service_line": "RENEWAL",
            "work_order_amount": 5000.0,
            "source_version": 1,
        },
        "unsupported_claims": ["changed owner"],
    }
    ok, reason, span = verifier.verify(record, hallucinated)
    malformed_ok, malformed_reason, malformed_span = verifier.verify(record, {"not_delivered_fields": True})
    result = {
        "hallucination": {"verifier_ok": ok, "reason": reason, "span": span.to_json()},
        "malformed": {
            "verifier_ok": malformed_ok,
            "reason": malformed_reason,
            "span": malformed_span.to_json(),
        },
    }
    write_json(Path("out/probes/probe_agent_failure.json"), result)
    if ok or reason != "AGENT_HALLUCINATION" or malformed_ok or malformed_reason != "AGENT_MALFORMED":
        print("FAIL: verifier missed bad worker output")
        return 1
    print("PASS: verifier routed hallucinated and malformed worker output")
    return 0


def probe_budget() -> int:
    old_cost = os.environ.get("MAX_COST_USD_PER_RECORD")
    os.environ["MAX_COST_USD_PER_RECORD"] = "0.000001"
    try:
        audit = Orchestrator(Path(os.environ.get("SEED_DIR", "seed")), Path("out/probe_budget"), Path("transcripts")).run()
    finally:
        if old_cost is None:
            os.environ.pop("MAX_COST_USD_PER_RECORD", None)
        else:
            os.environ["MAX_COST_USD_PER_RECORD"] = old_cost
    found = any(r.get("reason_code") == "BUDGET_EXCEEDED" and r.get("status") == "exception" for r in audit["records"])
    if not found:
        print("FAIL: budget exhaustion was not routed")
        return 1
    print("PASS: BUDGET_EXCEEDED raised and routed")
    return 0


def probe_append_only() -> int:
    events = AuditEvents()
    events.append("probe", "first_event")
    events.seal()
    refused = events.attempt_mutation()
    write_json(Path("out/probes/probe_append_only.json"), {"mutation_refused": refused})
    if not refused:
        print("FAIL: audit mutation was not refused")
        return 1
    print("PASS: append-only mutation refused")
    return 0


def probe_idempotency() -> int:
    first = Orchestrator(Path(os.environ.get("SEED_DIR", "seed")), Path("out"), Path("transcripts")).run()
    second = Orchestrator(Path(os.environ.get("SEED_DIR", "seed")), Path("out"), Path("transcripts")).run()
    key1 = sorted((r["id"], r["version"], r["status"], r.get("reason_code")) for r in first["records"])
    key2 = sorted((r["id"], r["version"], r["status"], r.get("reason_code")) for r in second["records"])
    ok = key1 == key2 and len(key2) == len(set(key2))
    write_json(Path("out/probes/probe_idempotency.json"), {"idempotent": ok, "records": len(key2)})
    if not ok:
        print("FAIL: repeated run changed record set or duplicated records")
        return 1
    print("PASS: repeated demo is idempotent")
    return 0


def _load_audit() -> dict:
    path = Path("out/audit.json")
    if not path.exists():
        raise SystemExit("out/audit.json not found; run make demo first")
    return read_json(path)


def _find_record(audit: dict, record_id: str) -> dict:
    matches = [r for r in audit["records"] if r["id"] == record_id and r["status"] != "superseded"]
    if not matches:
        matches = [r for r in audit["records"] if r["id"] == record_id]
    if not matches:
        raise SystemExit(f"record not found: {record_id}")
    return matches[-1]


if __name__ == "__main__":
    sys.exit(main())
