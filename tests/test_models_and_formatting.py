from __future__ import annotations

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from ftmo_bot.formatting import format_daily_summary, split_telegram_message
from ftmo_bot.models import EconomicEvent


TZ = ZoneInfo("Europe/Warsaw")


def event(**overrides) -> EconomicEvent:
    values = {
        "title": "CPI y/y",
        "impact": "high",
        "instrument": "USD + US Indices + XAUUSD + DXY",
        "restriction": True,
        "event_type": "normal",
        "date": datetime(2026, 8, 12, 14, 30, tzinfo=TZ),
        "forecast": "3.4 %",
        "previous": "3.5 %",
        "actual": None,
        "article_link": None,
    }
    values.update(overrides)
    return EconomicEvent(**values)


class ModelAndFormattingTests(unittest.TestCase):
    def test_restricted_event_is_p0(self) -> None:
        self.assertEqual(event().priority, "P0")

    def test_unrestricted_high_event_is_p1(self) -> None:
        self.assertEqual(event(restriction=False).priority, "P1")

    def test_summary_contains_restriction_window(self) -> None:
        text = format_daily_summary([event()], TZ, frozenset({"high", "medium"}))
        self.assertIn("14:28–14:32", text)
        self.assertIn("P0", text)
        self.assertIn("FTMO Account Standard", text)

    def test_long_messages_are_split(self) -> None:
        chunks = split_telegram_message(("abc\n" * 2000), limit=100)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 100 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
