"""Request-scoped reminder store; ids for new reminders are minted here, never by the model."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Reminder:
    id: str
    title: str
    time: datetime


class ReminderStore(Protocol):
    def list(self) -> Sequence[Reminder]: ...

    def add(self, title: str, time: datetime) -> str: ...

    def set_time(self, reminder_id: str, time: datetime) -> None: ...

    def remove(self, reminder_id: str) -> None: ...


class InMemoryReminderStore:
    def __init__(self, initial: Iterable[Reminder] = ()) -> None:
        self._items: dict[str, Reminder] = {r.id: r for r in initial}
        self._counter = 0

    def list(self) -> Sequence[Reminder]:
        return [*self._items.values()]

    def add(self, title: str, time: datetime) -> str:
        while True:
            self._counter += 1
            new_id = f"rem-{self._counter}"
            if new_id not in self._items:
                break
        self._items[new_id] = Reminder(new_id, title, time)
        return new_id

    def set_time(self, reminder_id: str, time: datetime) -> None:
        self._items[reminder_id] = replace(self._items[reminder_id], time=time)

    def remove(self, reminder_id: str) -> None:
        del self._items[reminder_id]
