from __future__ import annotations

from .util import utc_now


def delivered_approval_trail(amount: float | None, amendment: dict) -> list[dict]:
    trail = [
        {"state": "draft", "actor": "staffing_worker", "ts": utc_now(), "reason": None},
        {"state": "in_review", "actor": "orchestrator", "ts": utc_now(), "reason": None},
        {"state": "approved", "actor": "operator", "ts": utc_now(), "reason": "standard staffing package approved"},
    ]
    if amount is not None and amount >= amendment["threshold"]:
        trail.append(
            {
                "state": "approved",
                "actor": amendment["role"],
                "ts": utc_now(),
                "reason": f"CASE_ID amendment approval for amount >= {amendment['threshold']}",
            }
        )
    trail.append({"state": "delivered", "actor": "delivery", "ts": utc_now(), "reason": None})
    return trail


def blocked_approval_trail(reason_code: str) -> list[dict]:
    return [{"state": "blocked", "actor": "orchestrator", "ts": utc_now(), "reason": reason_code}]


def can_deliver(approval_trail: list[dict], amount: float | None, amendment: dict) -> tuple[bool, str]:
    states = [item["state"] for item in approval_trail]
    actors = [item["actor"] for item in approval_trail if item["state"] == "approved"]
    if "approved" not in states:
        return False, "normal approval missing"
    if amount is not None and amount >= amendment["threshold"] and amendment["role"] not in actors:
        return False, "CASE_ID amendment approval missing"
    return True, "approved"
