from __future__ import annotations

import logging
import signal
import time as time_module
from datetime import datetime, timedelta

from ftmo_bot.client import FtmoCalendarClient, write_snapshot
from ftmo_bot.config import Settings, load_settings
from ftmo_bot.filters import is_event_in_notification_window
from ftmo_bot.formatting import format_daily_summary, format_release, format_restricted_reminder
from ftmo_bot.models import EconomicEvent
from ftmo_bot.state import NotificationState
from ftmo_bot.telegram import TelegramClient


logger = logging.getLogger(__name__)


class FtmoNotifierService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.calendar = FtmoCalendarClient(
            settings.api_url,
            settings.timezone,
            settings.request_timeout_seconds,
        )
        self.telegram = TelegramClient(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            settings.request_timeout_seconds,
        )
        self.state = NotificationState(settings.state_file)
        self.stop_requested = False
        self.first_run = True

    def request_stop(self, *_args) -> None:
        self.stop_requested = True

    def run_forever(self) -> None:
        signal.signal(signal.SIGTERM, self.request_stop)
        signal.signal(signal.SIGINT, self.request_stop)
        logger.info("FTMO notifier started; poll=%ss", self.settings.poll_seconds)
        while not self.stop_requested:
            cycle_started = time_module.monotonic()
            try:
                self.run_cycle()
            except Exception:
                logger.exception("Notification cycle failed")
            self.first_run = False
            elapsed = time_module.monotonic() - cycle_started
            wait_seconds = max(1, self.settings.poll_seconds - int(elapsed))
            for _ in range(wait_seconds):
                if self.stop_requested:
                    break
                time_module.sleep(1)
        logger.info("FTMO notifier stopped")

    def run_cycle(self, now: datetime | None = None) -> None:
        local_now = (now or datetime.now(self.settings.timezone)).astimezone(self.settings.timezone)
        events, payload = self.calendar.fetch(local_now.date(), local_now.date() + timedelta(days=1))
        write_snapshot(self.settings.snapshot_file, payload)
        eligible_events = [
            event
            for event in events
            if is_event_in_notification_window(
                event,
                self.settings.timezone,
                self.settings.event_time_from,
                self.settings.event_time_to,
                self.settings.exclude_weekends,
            )
        ]
        today_events = [
            event
            for event in eligible_events
            if event.date.astimezone(self.settings.timezone).date() == local_now.date()
        ]

        if self._summary_is_due(local_now):
            key = f"summary:{local_now.date().isoformat()}"
            self.telegram.send(
                format_daily_summary(
                    today_events,
                    self.settings.timezone,
                    self.settings.summary_impacts,
                    summary_day=local_now.date(),
                    language=self.settings.message_language,
                )
            )
            self.state.mark_sent(key, local_now.isoformat(timespec="seconds"))
            logger.info("Daily summary sent for %s", local_now.date())

        for event in eligible_events:
            if event.restriction:
                self._send_due_reminder(event, local_now)
                self._send_release_update(event, local_now)

        logger.info(
            "Cycle complete: %s events (%s eligible, %s today)",
            len(events),
            len(eligible_events),
            len(today_events),
        )

    def _summary_is_due(self, now: datetime) -> bool:
        if self.settings.exclude_weekends and now.weekday() >= 5:
            return False
        key = f"summary:{now.date().isoformat()}"
        if self.state.was_sent(key):
            return False
        if self.first_run and self.settings.send_summary_on_start:
            return True
        scheduled = datetime.combine(now.date(), self.settings.summary_time, self.settings.timezone)
        return scheduled <= now <= scheduled + timedelta(minutes=self.settings.summary_grace_minutes)

    def _send_due_reminder(self, event: EconomicEvent, now: datetime) -> None:
        event_time = event.date.astimezone(self.settings.timezone)
        seconds_until = (event_time - now).total_seconds()
        if seconds_until < 0:
            return
        minutes_until = max(0, int((seconds_until + 59) // 60))
        eligible = [offset for offset in self.settings.reminder_minutes if minutes_until <= offset]
        if not eligible:
            return
        selected_offset = min(eligible)
        key = f"reminder:{event.occurrence_id}:{selected_offset}"
        if self.state.was_sent(key):
            return
        self.telegram.send(
            format_restricted_reminder(
                event,
                self.settings.timezone,
                minutes_until,
                language=self.settings.message_language,
            )
        )
        self.state.mark_sent(key, now.isoformat(timespec="seconds"))
        logger.info("Reminder sent event=%s offset=%s", event.stable_id, selected_offset)

    def _send_release_update(self, event: EconomicEvent, now: datetime) -> None:
        if not event.actual:
            return
        event_time = event.date.astimezone(self.settings.timezone)
        release_end = event_time + timedelta(minutes=2)
        if not (release_end <= now <= release_end + timedelta(minutes=45)):
            return
        key = f"release:{event.occurrence_id}"
        if self.state.was_sent(key):
            return
        self.telegram.send(
            format_release(
                event,
                self.settings.timezone,
                language=self.settings.message_language,
            )
        )
        self.state.mark_sent(key, now.isoformat(timespec="seconds"))
        logger.info("Release update sent event=%s", event.stable_id)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = load_settings()
    FtmoNotifierService(settings).run_forever()
