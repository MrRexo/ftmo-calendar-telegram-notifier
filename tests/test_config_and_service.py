from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from ftmo_bot.config import load_settings
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


if __name__ == "__main__":
    unittest.main()
