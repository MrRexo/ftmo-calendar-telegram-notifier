from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, time
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from ftmo_bot.config import load_settings
from ftmo_bot.filters import is_event_in_notification_window
from ftmo_bot.models import EconomicEvent
from ftmo_bot.service import FtmoNotifierService


TZ = ZoneInfo("Europe/Warsaw")


class ConfigTests(unittest.TestCase):
    def test_legacy_colon_config_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "env.txt"
            path.write_text("BOT_TOKEN: secret\nMOJ_CHAT_ID: 12345\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                settings = load_settings(path)
            self.assertEqual(settings.telegram_bot_token, "secret")
            self.assertEqual(settings.telegram_chat_id, "12345")

    def test_notification_window_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "env.txt"
            path.write_text("BOT_TOKEN: secret\nMOJ_CHAT_ID: 12345\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                settings = load_settings(path)
            self.assertEqual(settings.event_time_from, time(7, 0))
            self.assertEqual(settings.event_time_to, time(20, 0))
            self.assertTrue(settings.exclude_weekends)
            self.assertEqual(settings.message_language, "pl")

    def test_message_language_can_be_english(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "env.txt"
            path.write_text("BOT_TOKEN: secret\nMOJ_CHAT_ID: 12345\n", encoding="utf-8")
            with patch.dict(os.environ, {"MESSAGE_LANGUAGE": "EN"}, clear=True):
                settings = load_settings(path)
            self.assertEqual(settings.message_language, "en")

    def test_unknown_message_language_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "env.txt"
            path.write_text("BOT_TOKEN: secret\nMOJ_CHAT_ID: 12345\n", encoding="utf-8")
            with patch.dict(os.environ, {"MESSAGE_LANGUAGE": "de"}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "MESSAGE_LANGUAGE"):
                    load_settings(path)


class NotificationWindowTests(unittest.TestCase):
    @staticmethod
    def _event(at: datetime) -> EconomicEvent:
        return EconomicEvent(
            title="CPI y/y",
            impact="high",
            instrument="USD",
            restriction=True,
            event_type="normal",
            date=at,
            forecast=None,
            previous=None,
            actual=None,
            article_link=None,
        )

    def test_weekday_boundaries_are_inclusive(self) -> None:
        for hour in (
            datetime(2026, 8, 14, 7, 0, tzinfo=TZ),
            datetime(2026, 8, 14, 20, 0, tzinfo=TZ),
        ):
            with self.subTest(hour=hour):
                self.assertTrue(
                    is_event_in_notification_window(self._event(hour), TZ, time(7), time(20))
                )

    def test_events_outside_window_are_excluded(self) -> None:
        for hour in (
            datetime(2026, 8, 14, 6, 59, tzinfo=TZ),
            datetime(2026, 8, 14, 20, 1, tzinfo=TZ),
        ):
            with self.subTest(hour=hour):
                self.assertFalse(
                    is_event_in_notification_window(self._event(hour), TZ, time(7), time(20))
                )

    def test_weekend_event_is_excluded(self) -> None:
        saturday = datetime(2026, 8, 15, 12, 0, tzinfo=TZ)
        self.assertFalse(
            is_event_in_notification_window(self._event(saturday), TZ, time(7), time(20))
        )


class ReminderSelectionTests(unittest.TestCase):
    def _service(self) -> FtmoNotifierService:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "env.txt"
            path.write_text("BOT_TOKEN: secret\nMOJ_CHAT_ID: 12345\n", encoding="utf-8")
            with patch.dict(os.environ, {"STATE_FILE": str(Path(directory) / "state.json")}, clear=True):
                settings = load_settings(path)
            service = FtmoNotifierService(settings)
            service.telegram.send = unittest.mock.Mock()
            return service

    def test_only_closest_due_reminder_is_sent(self) -> None:
        service = self._service()
        now = datetime(2026, 8, 12, 14, 26, tzinfo=TZ)
        item = EconomicEvent(
            title="CPI y/y",
            impact="high",
            instrument="USD",
            restriction=True,
            event_type="normal",
            date=datetime(2026, 8, 12, 14, 30, tzinfo=TZ),
            forecast=None,
            previous=None,
            actual=None,
            article_link=None,
        )
        service._send_due_reminder(item, now)
        service.telegram.send.assert_called_once()
        self.assertTrue(service.state.was_sent(f"reminder:{item.occurrence_id}:5"))

    def test_summary_is_not_due_on_weekend(self) -> None:
        service = self._service()
        saturday = datetime(2026, 8, 15, 7, 0, tzinfo=TZ)
        self.assertFalse(service._summary_is_due(saturday))


if __name__ == "__main__":
    unittest.main()
