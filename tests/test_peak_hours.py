"""Unit tests for peak hours logic."""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from peak_hours_manager import (
    PT,
    PeakHoursManager,
    PeakStatus,
    _format_countdown,
)


def _make_dt(year, month, day, hour, minute, second=0, tz=PT):
    """Helper: create a datetime in given timezone."""
    return datetime(year, month, day, hour, minute, second, tzinfo=tz)


def _state_at(dt):
    """Get PeakState at a specific datetime."""
    with patch("peak_hours_manager.datetime") as mock_dt:
        mock_dt.now.return_value = dt.astimezone(timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        m = PeakHoursManager()
        m.update()
        return m.state


class TestPeakDetection:
    """Test that peak/off-peak is correctly detected."""

    def test_weekday_during_peak(self):
        # Tuesday 8:00 AM PT = peak
        dt = _make_dt(2026, 3, 31, 8, 0)  # Tuesday
        state = _state_at(dt)
        assert state.is_peak is True
        assert state.status == PeakStatus.PEAK

    def test_weekday_before_peak(self):
        # Tuesday 3:00 AM PT = off-peak
        dt = _make_dt(2026, 3, 31, 3, 0)
        state = _state_at(dt)
        assert state.is_peak is False
        assert state.status == PeakStatus.OFF_PEAK

    def test_weekday_after_peak(self):
        # Tuesday 14:00 PT = off-peak
        dt = _make_dt(2026, 3, 31, 14, 0)
        state = _state_at(dt)
        assert state.is_peak is False

    def test_peak_start_boundary(self):
        # Exactly 5:00 AM PT = peak starts
        dt = _make_dt(2026, 3, 31, 5, 0)
        state = _state_at(dt)
        assert state.is_peak is True

    def test_peak_end_boundary(self):
        # Exactly 11:00 AM PT = peak ends (off-peak)
        dt = _make_dt(2026, 3, 31, 11, 0)
        state = _state_at(dt)
        assert state.is_peak is False

    def test_saturday_always_offpeak(self):
        # Saturday 8:00 AM PT = off-peak
        dt = _make_dt(2026, 4, 4, 8, 0)  # Saturday
        state = _state_at(dt)
        assert state.is_peak is False

    def test_sunday_always_offpeak(self):
        # Sunday 9:00 AM PT = off-peak
        dt = _make_dt(2026, 4, 5, 9, 0)  # Sunday
        state = _state_at(dt)
        assert state.is_peak is False


class TestWarningDirection:
    """Warning should only fire when approaching peak, not leaving it."""

    def test_warning_before_peak_starts(self):
        # Tuesday 4:50 AM PT = 10 min before peak = WARNING
        dt = _make_dt(2026, 3, 31, 4, 50)
        state = _state_at(dt)
        assert state.status == PeakStatus.WARNING

    def test_no_warning_before_peak_ends(self):
        # Tuesday 10:50 AM PT = 10 min before peak ends = still PEAK (not warning)
        dt = _make_dt(2026, 3, 31, 10, 50)
        state = _state_at(dt)
        assert state.status == PeakStatus.PEAK  # NOT warning


class TestCountdown:
    """Test countdown text formatting."""

    def test_minutes_only(self):
        assert _format_countdown(300) == "5min"
        assert _format_countdown(0) == "0min"
        assert _format_countdown(59) == "0min"  # < 1 minute

    def test_hours_and_minutes(self):
        assert _format_countdown(3600) == "1h 0min"
        assert _format_countdown(5400) == "1h 30min"
        assert _format_countdown(7200) == "2h 0min"

    def test_days(self):
        assert _format_countdown(90000) == "1d 1h"  # 25 hours
        assert _format_countdown(180000) == "2d 2h"  # 50 hours


class TestCountdownValues:
    """Test that countdown points to the right next event."""

    def test_countdown_during_peak(self):
        # Tuesday 8:00 AM PT, peak ends at 11:00 = 3 hours left
        dt = _make_dt(2026, 3, 31, 8, 0)
        state = _state_at(dt)
        assert state.is_peak is True
        # Should be ~3 hours (10800 seconds)
        assert 10700 < state.seconds_until_change < 10900

    def test_countdown_before_peak(self):
        # Tuesday 3:00 AM PT, peak starts at 5:00 = 2 hours
        dt = _make_dt(2026, 3, 31, 3, 0)
        state = _state_at(dt)
        assert not state.is_peak
        assert 7100 < state.seconds_until_change < 7300

    def test_countdown_weekend_to_monday(self):
        # Saturday 12:00 PM PT → Monday 5:00 AM PT
        dt = _make_dt(2026, 4, 4, 12, 0)  # Saturday
        state = _state_at(dt)
        assert not state.is_peak
        # ~41 hours to Monday 5 AM
        assert state.seconds_until_change > 140000

    def test_countdown_friday_after_peak(self):
        # Friday 14:00 PT → Monday 5:00 AM PT
        dt = _make_dt(2026, 4, 3, 14, 0)  # Friday
        state = _state_at(dt)
        assert not state.is_peak
        # Should be > 2 days
        assert state.seconds_until_change > 2 * 86400


class TestLocalPeakHours:
    """Test local timezone display string."""

    def test_contains_time_range(self):
        m = PeakHoursManager()
        # Should contain a time range like "14:00–20:00"
        assert "–" in m.state.peak_hours_local
        # Should contain a timezone abbreviation
        parts = m.state.peak_hours_local.split()
        assert len(parts) >= 2  # "HH:MM–HH:MM TZ"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
