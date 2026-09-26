"""Current state alongside the full ordered history per unit."""

from __future__ import annotations

import dataclasses
import threading
from typing import Any


@dataclasses.dataclass(frozen=True)
class StateEntry:
    unit_id: str
    state: str
    tick: int
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "state": self.state,
            "tick": self.tick,
            "reason": self.reason,
        }


class StateHistory:
    """Keeps the whole transition chain so past states stay queryable."""

    def __init__(self) -> None:
        self._entries: dict[str, list[StateEntry]] = {}
        self._lock = threading.RLock()

    def record(self, unit_id: str, state: str, tick: int, reason: str = "") -> StateEntry:
        entry = StateEntry(unit_id=unit_id, state=state, tick=int(tick), reason=reason)
        with self._lock:
            self._entries.setdefault(unit_id, []).append(entry)
        return entry

    def current(self, unit_id: str) -> StateEntry | None:
        with self._lock:
            chain = self._entries.get(unit_id)
            return chain[-1] if chain else None

    def at(self, unit_id: str, tick: int) -> StateEntry | None:
        """Return the state that was current at ``tick`` (historical view)."""

        with self._lock:
            chain = self._entries.get(unit_id)
            if not chain:
                return None
            result: StateEntry | None = None
            for entry in chain:
                if entry.tick > tick:
                    break
                result = entry
            return result

    def between(self, unit_id: str, start_tick: int, end_tick: int) -> list[StateEntry]:
        with self._lock:
            return [
                entry
                for entry in self._entries.get(unit_id, [])
                if start_tick <= entry.tick <= end_tick
            ]

    def transitions(self, unit_id: str) -> list[str]:
        with self._lock:
            collapsed: list[str] = []
            for entry in self._entries.get(unit_id, []):
                if not collapsed or collapsed[-1] != entry.state:
                    collapsed.append(entry.state)
            return collapsed

    def changed_between(self, unit_id: str, start_tick: int, end_tick: int) -> bool:
        with self._lock:
            chain = self._entries.get(unit_id, [])
            initial: StateEntry | None = None
            for entry in chain:
                if entry.tick > start_tick:
                    break
                initial = entry
            initial_state = initial.state if initial is not None else None
            for entry in chain:
                if entry.tick <= start_tick:
                    continue
                if entry.tick > end_tick:
                    break
                if entry.state != initial_state:
                    return True
            return False

    def units(self) -> list[str]:
        with self._lock:
            return sorted(self._entries.keys())

    def length(self, unit_id: str) -> int:
        with self._lock:
            return len(self._entries.get(unit_id, []))
