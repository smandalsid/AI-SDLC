"""Deterministic reference calendar and daylight-saving helpers (FR-1)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.calendar_context import local_time_status, reference_calendar

pytestmark = pytest.mark.covers("FR-1", "AC-26", "AC-36")

NY = ZoneInfo("America/New_York")
KOLKATA = ZoneInfo("Asia/Kolkata")


def test_lists_now_weekday_and_the_next_14_dates_with_offsets() -> None:
    now = datetime.fromisoformat("2026-11-05T10:00:00+05:30")
    text = reference_calendar(KOLKATA, now)
    assert "2026-11-05T10:00:00+05:30" in text and "Thursday" in text and "Asia/Kolkata" in text
    dated = [line for line in text.splitlines() if line.startswith("2026-11-")]
    assert len(dated) == 14 and dated[0].startswith("2026-11-06 Friday") and "+05:30" in dated[0]
    assert dated[-1].startswith("2026-11-19")


def test_spring_forward_day_is_called_out() -> None:
    now = datetime.fromisoformat("2027-03-13T12:00:00-05:00")
    text = reference_calendar(NY, now)
    line = next(ln for ln in text.splitlines() if "offset changes" in ln)
    assert "2027-03-14" in line and "-05:00 -> -04:00" in line
    assert "02:00-02:59" in line and "do not exist" in line


def test_fall_back_day_is_called_out() -> None:
    now = datetime.fromisoformat("2026-10-30T12:00:00-04:00")
    line = next(ln for ln in reference_calendar(NY, now).splitlines() if "offset changes" in ln)
    assert "2026-11-01" in line and "-04:00 -> -05:00" in line
    assert "01:00-01:59" in line and "occur twice" in line


def test_a_zone_without_changes_has_no_offset_change_line() -> None:
    now = datetime.fromisoformat("2026-11-05T10:00:00+05:30")
    assert "offset changes" not in reference_calendar(KOLKATA, now)


def test_output_is_deterministic() -> None:
    now = datetime.fromisoformat("2027-03-13T12:00:00-05:00")
    assert reference_calendar(NY, now) == reference_calendar(NY, now)


@pytest.mark.parametrize(
    ("local", "status"),
    [
        ("2027-03-14T02:30:00", "gap"),
        ("2027-03-14T03:00:00", "exists"),
        ("2027-03-14T01:59:00", "exists"),
        ("2026-11-01T01:30:00", "ambiguous"),
        ("2026-11-01T02:00:00", "exists"),
        ("2026-11-05T09:00:00", "exists"),
    ],
)
def test_local_time_status(local: str, status: str) -> None:
    assert local_time_status(NY, datetime.fromisoformat(local)) == status
