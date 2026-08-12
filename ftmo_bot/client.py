from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ftmo_bot.models import EconomicEvent


class FtmoCalendarClient:
    def __init__(self, api_url: str, timezone: ZoneInfo, timeout_seconds: int = 20) -> None:
        self.api_url = api_url
        self.timezone = timezone
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "FTMO-Calendar-Telegram-Notifier/1.0",
            }
        )

    def fetch(self, start_day: date, end_day_inclusive: date) -> tuple[list[EconomicEvent], dict]:
        start = datetime.combine(start_day, time.min, self.timezone)
        end_exclusive = datetime.combine(end_day_inclusive + timedelta(days=1), time.min, self.timezone)
        response = self.session.get(
            self.api_url,
            params={
                "dateFrom": start.isoformat(),
                "dateTo": end_exclusive.isoformat(),
                "timezone": getattr(self.timezone, "key", str(self.timezone)),
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise ValueError("Unexpected FTMO API response")
        events = [EconomicEvent.from_api(item) for item in payload["items"]]
        events.sort(key=lambda event: event.date)
        return events, payload


def write_snapshot(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
