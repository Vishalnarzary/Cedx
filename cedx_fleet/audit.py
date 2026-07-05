from __future__ import annotations

from typing import Any

from .util import utc_now


class AuditEvents:
    def __init__(self):
        self._events: list[dict[str, Any]] = []
        self._sealed = False

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def append(self, actor: str, action: str, record_id: str | None = None, **extra: Any) -> None:
        if self._sealed:
            raise RuntimeError("audit log is sealed; append refused")
        event = {"seq": len(self._events), "ts": utc_now(), "actor": actor, "action": action, "record_id": record_id}
        event.update(extra)
        self._events.append(event)

    def seal(self) -> None:
        self._sealed = True

    def attempt_mutation(self) -> bool:
        if not self._events:
            self.append("probe", "seed_event")
        before = list(self._events)
        try:
            if self._sealed:
                raise RuntimeError("append-only log refuses mutation")
            self._events[0]["action"] = "tampered"
        except RuntimeError:
            return self._events == before
        return False
