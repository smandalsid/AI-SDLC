"""CreateHandler: one new reminder, store-minted id, verbatim title (FR-1, Principle VIII)."""

from datetime import datetime

import pytest
from app_helpers import NOW, create_dict, request

from app.models.action import ProposedAction
from app.models.requests import CallerContext
from app.models.responses import AppliedResult
from app.services.applier import Applier, CreateHandler
from app.services.store import InMemoryReminderStore, Reminder

pytestmark = pytest.mark.covers("FR-1", "AC-1", "AC-38")

WHEN = "2026-11-09T09:00:00+05:30"
EXISTING = Reminder("r1", "Dentist", datetime.fromisoformat("2026-11-06T10:00:00+00:00"))
CONTEXT = CallerContext.build(request(timezone="Asia/Kolkata"), NOW)


def _apply(**overrides: object) -> tuple[InMemoryReminderStore, AppliedResult]:
    store = InMemoryReminderStore([EXISTING])
    action = ProposedAction.model_validate(create_dict(datetime_iso=WHEN, **overrides))
    return store, Applier().apply(action, store, CONTEXT)


def test_exactly_one_reminder_is_added_with_the_given_title_and_time() -> None:
    store, result = _apply(title="pay rent")
    added = [r for r in store.list() if r.id != "r1"]
    assert len(store.list()) == 2 and len(added) == 1
    assert added[0].title == "pay rent" and added[0].time == datetime.fromisoformat(WHEN)
    assert added[0].time.utcoffset() == datetime.fromisoformat(WHEN).utcoffset()
    assert result.operation == "created" and result.new_time == WHEN


def test_the_id_is_minted_by_the_store_never_taken_from_the_model() -> None:
    store, result = _apply(target_reminder_id="model-chosen-id")
    ids = [r.id for r in store.list()]
    assert "model-chosen-id" not in ids
    assert result.affected_id == "rem-1" and "rem-1" in ids


def test_the_minted_id_skips_ids_already_in_use() -> None:
    store = InMemoryReminderStore([Reminder("rem-1", "Old", EXISTING.time)])
    action = ProposedAction.model_validate(create_dict(datetime_iso=WHEN))
    result = Applier().apply(action, store, CONTEXT)
    assert result.affected_id == "rem-2"
    assert [r.title for r in store.list() if r.id == "rem-1"] == ["Old"]


def test_other_reminders_are_unchanged() -> None:
    store, result = _apply()
    assert EXISTING in store.list()
    listed = {r.id: (r.title, r.time) for r in result.reminders}
    assert listed["r1"] == ("Dentist", "2026-11-06T10:00:00+00:00")


@pytest.mark.parametrize(
    "title", ["x", "x" * 120, "  spaced  title ", "take my blood pressure pills"]
)
def test_the_title_is_kept_verbatim_and_sensitive_text_is_not_masked(title: str) -> None:
    store, _ = _apply(title=title)
    assert [r.title for r in store.list() if r.id != "r1"] == [title]


def test_the_handler_reports_the_change_it_made() -> None:
    store = InMemoryReminderStore()
    action = ProposedAction.model_validate(create_dict(datetime_iso=WHEN))
    change = CreateHandler().handle(action, store, CONTEXT)
    assert change.operation == "created" and change.affected_id == "rem-1"
    assert change.new_time == datetime.fromisoformat(WHEN)
