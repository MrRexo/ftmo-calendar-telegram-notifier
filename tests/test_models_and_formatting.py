from __future__ import annotations

import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from ftmo_bot.formatting import (
    format_daily_summary,
    format_release,
    format_restricted_reminder,
    split_telegram_message,
)
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
        self.assertIn("środa, 12.08.2026", text)

    def test_summary_contains_special_notice_on_thirteenth(self) -> None:
        text = format_daily_summary(
            [],
            TZ,
            frozenset({"high", "medium"}),
            summary_day=date(2026, 8, 13),
        )
        self.assertIn("🛑 Dziś 13! Nie graj niczego 🙂", text)

    def test_summary_omits_special_notice_on_other_days(self) -> None:
        text = format_daily_summary(
            [event()],
            TZ,
            frozenset({"high", "medium"}),
            summary_day=date(2026, 8, 12),
        )
        self.assertNotIn("Nie graj niczego", text)

    def test_english_summary_is_fully_localized(self) -> None:
        text = format_daily_summary(
            [event()],
            TZ,
            frozenset({"high", "medium"}),
            language="en",
        )
        self.assertIn("Wednesday, 12.08.2026", text)
        self.assertIn("FTMO RESTRICTION", text)
        self.assertIn("Instruments:", text)
        self.assertIn("No opening/closing trades:", text)
        self.assertIn("Time: Europe/Warsaw", text)
        self.assertNotIn("Instrumenty:", text)

    def test_english_special_notice_on_thirteenth(self) -> None:
        text = format_daily_summary(
            [],
            TZ,
            frozenset({"high", "medium"}),
            summary_day=date(2026, 8, 13),
            language="en",
        )
        self.assertIn("🛑 Today is the 13th! Do not trade anything 🙂", text)

    def test_reminder_and_release_support_english(self) -> None:
        reminder = format_restricted_reminder(event(), TZ, 5, language="en")
        release = format_release(event(actual="3.3 %"), TZ, language="en")
        self.assertIn("in about 5 min", reminder)
        self.assertIn("Do not open or close positions", reminder)
        self.assertIn("Actual: 3.3 %", release)
        self.assertIn("The restriction expires at 14:32", release)

    def test_unknown_language_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            format_daily_summary([event()], TZ, frozenset({"high"}), language="de")

    def test_long_messages_are_split(self) -> None:
        chunks = split_telegram_message(("abc\n" * 2000), limit=100)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 100 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
