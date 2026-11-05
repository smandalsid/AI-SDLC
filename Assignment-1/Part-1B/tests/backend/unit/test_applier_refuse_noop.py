"""A refusal changes nothing; bulk actions cannot be expressed (GR-1 to GR-6)."""

from datetime import datetime

import pytest
from app_helpers import NOW, action_dict, request
from pydantic import ValidationError

from app.models.action import ProposedAction, ProposedActionWire, RefusalReason
from app.models.requests import CallerContext
from app.services.applier import Applier
from app.services.store import InMemoryReminderStore, Reminder

pytestmark = pytest.mark.covers("GR-1", "GR-2", "GR-3", "GR-6", "SC-005")

STORED = [
    Reminder("r1", "Dentist", datetime.fromisoformat("2026-11-06T10:00:00+00:00")),
    Reminder("r2", "Gym session", datetime.fromisoformat("2026-11-07T07:00:00+00:00")),
]
CONTEXT = CallerContext.build(request(), NOW)


def _refusal(reason: RefusalReason) -> ProposedAction:
    return ProposedAction.model_validate(
        action_dict(intent="refuse", refusal_reason=reason.value, clarification_question=None)
    )


@pytest.mark.parametrize("reason", list(RefusalReason), ids=lambda reason: reason.value)
def test_every_refusal_reason_leaves_the_store_untouched(reason: RefusalReason) -> None:
    store = InMemoryReminderStore(STORED)
    result = Applier().apply(_refusal(reason), store, CONTEXT)
    assert result.operation == "none" and result.affected_id is None and result.new_time is None
    assert list(store.list()) == STORED
    assert [r.id for r in result.reminders] == ["r1", "r2"]


def test_a_refusal_that_also_carries_a_target_still_changes_nothing() -> None:
    action = ProposedAction.model_validate(
        action_dict(
            intent="refuse",
            refusal_reason="bulk_action",
            target_reminder_id="r1",
            clarification_question=None,
        )
    )
    store = InMemoryReminderStore(STORED)
    assert Applier().apply(action, store, CONTEXT).operation == "none"
    assert list(store.list()) == STORED


def test_the_contract_has_one_string_target_so_a_bulk_request_cannot_be_represented() -> None:
    assert ProposedActionWire.model_fields["target_reminder_id"].annotation == (str | None)
    for many in (["r1", "r2"], {"all": True}):
        scripted = action_dict(
            intent="cancel", target_reminder_id=many, clarification_question=None
        )
        with pytest.raises(ValidationError):
            ProposedActionWire.model_validate(scripted)
