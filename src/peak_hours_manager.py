"""Core peak-hours logic — mirrors PeakHoursManager.swift."""

from __future__ import annotations

import threading
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum, auto
from zoneinfo import ZoneInfo
from typing import Callable

from strings import (
    FULL_POWER, RESTRICTED, RESTRICTIONS_IN, FULL_POWER_IN,
    NOTIF_RESTRICTED_TITLE, NOTIF_RESTRICTED_BODY,
    NOTIF_FULL_POWER_TITLE, NOTIF_FULL_POWER_BODY,
    notif_full_power_soon, notif_restricted_soon,
)

PT = ZoneInfo("America/Los_Angeles")
PEAK_START_HOUR = 5   # 5:00 AM PT
PEAK_END_HOUR = 11    # 11:00 AM PT
WARNING_SECONDS = 15 * 60  # 15 minutes


class PeakStatus(Enum):
    OFF_PEAK = auto()
    PEAK = auto()
    WARNING = auto()


@dataclass
class PeakState:
    is_peak: bool = False
    status: PeakStatus = PeakStatus.OFF_PEAK
    seconds_until_change: float = 0
    countdown_text: str = ""
    peak_hours_local: str = ""
    next_change_label: str = ""
    status_bar_text: str = ""
    status_bar_emoji: str = "🟢"


class PeakHoursManager:
    def __init__(self) -> None:
        self.state = PeakState()
        self._last_notified_peak: bool | None = None
        self._last_notified_warning: bool = False
        self._on_change: Callable[[PeakState], None] | None = None
        self._on_notify: Callable[[str, str], None] | None = None
        self._timer: threading.Timer | None = None
        self._running = False
        self.notifications_enabled = True

        self.update()
        self._compute_local_peak_hours()

    # -- public API ----------------------------------------------------------

    def set_on_change(self, callback: Callable[[PeakState], None]) -> None:
        self._on_change = callback

    def set_on_notify(self, callback: Callable[[str, str], None]) -> None:
        self._on_notify = callback

    def start(self) -> None:
        self._running = True
        self._schedule()

    def stop(self) -> None:
        self._running = False
        if self._timer:
            self._timer.cancel()

    # -- core logic ----------------------------------------------------------

    def update(self) -> None:
        now = datetime.now(timezone.utc).astimezone(PT)
        weekday = now.isoweekday()  # 1=Mon … 7=Sun
        hour, minute, second = now.hour, now.minute, now.second

        is_weekday = 1 <= weekday <= 5
        is_peak = is_weekday and PEAK_START_HOUR <= hour < PEAK_END_HOUR

        seconds_into_day = hour * 3600 + minute * 60 + second
        peak_start_sec = PEAK_START_HOUR * 3600
        peak_end_sec = PEAK_END_HOUR * 3600

        if not is_weekday:
            # Weekend → next Monday 5:00 AM PT
            days_until_monday = (8 - weekday) % 7 or 7  # Sat=2, Sun=1
            secs = days_until_monday * 86400 - seconds_into_day + peak_start_sec
            next_label = RESTRICTIONS_IN
        elif is_peak:
            secs = peak_end_sec - seconds_into_day
            next_label = FULL_POWER_IN
        elif seconds_into_day < peak_start_sec:
            secs = peak_start_sec - seconds_into_day
            next_label = RESTRICTIONS_IN
        else:
            # After peak today
            if weekday == 5:  # Friday after peak → Monday
                secs = 2 * 86400 + (86400 - seconds_into_day) + peak_start_sec
            else:
                secs = (86400 - seconds_into_day) + peak_start_sec
            next_label = RESTRICTIONS_IN

        secs = max(0, secs)

        # Determine status with warning zone
        if secs <= WARNING_SECONDS:
            status = PeakStatus.WARNING
        else:
            status = PeakStatus.PEAK if is_peak else PeakStatus.OFF_PEAK

        # Build state
        self.state = PeakState(
            is_peak=is_peak,
            status=status,
            seconds_until_change=secs,
            countdown_text=_format_countdown(secs),
            peak_hours_local=self.state.peak_hours_local,
            next_change_label=next_label,
            status_bar_text=self._status_bar_text(status, is_peak, secs),
            status_bar_emoji=self._status_bar_emoji(status),
        )

        # Notifications
        if self.notifications_enabled:
            self._handle_notifications(is_peak, secs)

        if self._on_change:
            self._on_change(self.state)

    # -- notifications -------------------------------------------------------

    def _handle_notifications(self, is_peak: bool, secs: float) -> None:
        if self._last_notified_peak is not None and self._last_notified_peak != is_peak:
            if is_peak:
                self._send_notif(NOTIF_RESTRICTED_TITLE, NOTIF_RESTRICTED_BODY)
            else:
                self._send_notif(NOTIF_FULL_POWER_TITLE, NOTIF_FULL_POWER_BODY)
        self._last_notified_peak = is_peak

        should_warn = WARNING_SECONDS >= secs > (WARNING_SECONDS - 60)
        if should_warn and not self._last_notified_warning:
            minutes = int(secs / 60)
            if is_peak:
                t, b = notif_full_power_soon(minutes)
            else:
                t, b = notif_restricted_soon(minutes)
            self._send_notif(t, b)
            self._last_notified_warning = True
        elif not should_warn:
            self._last_notified_warning = False

    def _send_notif(self, title: str, body: str) -> None:
        if self._on_notify:
            self._on_notify(title, body)

    # -- helpers -------------------------------------------------------------

    def _compute_local_peak_hours(self) -> None:
        now = datetime.now(timezone.utc)
        today_pt = now.astimezone(PT).date()

        start_pt = datetime(today_pt.year, today_pt.month, today_pt.day,
                            PEAK_START_HOUR, 0, 0, tzinfo=PT)
        end_pt = datetime(today_pt.year, today_pt.month, today_pt.day,
                          PEAK_END_HOUR, 0, 0, tzinfo=PT)

        local_tz = datetime.now().astimezone().tzinfo
        start_local = start_pt.astimezone(local_tz)
        end_local = end_pt.astimezone(local_tz)

        tz_name = start_local.strftime("%Z")
        self.state.peak_hours_local = (
            f"{start_local.strftime('%H:%M')}–{end_local.strftime('%H:%M')} {tz_name}"
        )

    def _schedule(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(30, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self) -> None:
        self.update()
        self._schedule()

    @staticmethod
    def _status_bar_text(status: PeakStatus, is_peak: bool, secs: float) -> str:
        if status == PeakStatus.WARNING:
            return f"⏱ {int(secs / 60)}min"
        return RESTRICTED if is_peak else FULL_POWER

    @staticmethod
    def _status_bar_emoji(status: PeakStatus) -> str:
        return {
            PeakStatus.OFF_PEAK: "🟢",
            PeakStatus.PEAK: "🔴",
            PeakStatus.WARNING: "🟡",
        }[status]


def _format_countdown(seconds: float) -> str:
    total_minutes = int(seconds) // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours > 24:
        days = hours // 24
        remaining_hours = hours % 24
        return f"{days}d {remaining_hours}h"
    if hours > 0:
        return f"{hours}h {minutes}min"
    return f"{minutes}min"
