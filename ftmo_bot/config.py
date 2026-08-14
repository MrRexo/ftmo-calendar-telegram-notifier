from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    api_url: str
    timezone: ZoneInfo
    message_language: str
    summary_time: time
    event_time_from: time
    event_time_to: time
    exclude_weekends: bool
    poll_seconds: int
    reminder_minutes: tuple[int, ...]
    summary_impacts: frozenset[str]
    send_summary_on_start: bool
    summary_grace_minutes: int
    state_file: Path
    snapshot_file: Path
    request_timeout_seconds: int


def load_settings(config_file: Path | None = None) -> Settings:
    values = _read_config_file(config_file or Path(os.getenv("FTMO_CONFIG_FILE", "env.txt")))

    aliases = {
        "BOT_TOKEN": "TELEGRAM_BOT_TOKEN",
        "MOJ_CHAT_ID": "TELEGRAM_CHAT_ID",
        "CHAT_ID": "TELEGRAM_CHAT_ID",
    }
    normalized = {aliases.get(key, key): value for key, value in values.items()}

    def get(name: str, default: str = "") -> str:
        return os.getenv(name, normalized.get(name, default)).strip()

    token = get("TELEGRAM_BOT_TOKEN")
    chat_id = get("TELEGRAM_CHAT_ID")
    if not token:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
    if not chat_id:
        raise RuntimeError("Missing TELEGRAM_CHAT_ID")

    reminder_minutes = tuple(
        sorted(
            {int(value.strip()) for value in get("REMINDER_MINUTES", "15,5").split(",") if value.strip()},
            reverse=True,
        )
    )
    summary_impacts = frozenset(
        value.strip().lower()
        for value in get("SUMMARY_IMPACTS", "high,medium").split(",")
        if value.strip()
    )
    event_time_from = _parse_time(get("EVENT_TIME_FROM", "07:00"))
    event_time_to = _parse_time(get("EVENT_TIME_TO", "20:00"))
    if event_time_from > event_time_to:
        raise RuntimeError("EVENT_TIME_FROM must not be later than EVENT_TIME_TO")
    message_language = get("MESSAGE_LANGUAGE", "pl").lower()
    if message_language not in {"pl", "en"}:
        raise RuntimeError("MESSAGE_LANGUAGE must be one of: en, pl")

    return Settings(
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        api_url=get("FTMO_API_URL", "https://gw2.ftmo.com/public-api/v1/economic-calendar"),
        timezone=ZoneInfo(get("TIMEZONE", "Europe/Warsaw")),
        message_language=message_language,
        summary_time=_parse_time(get("SUMMARY_TIME", "07:00")),
        event_time_from=event_time_from,
        event_time_to=event_time_to,
        exclude_weekends=_parse_bool(get("EXCLUDE_WEEKENDS", "true")),
        poll_seconds=max(60, int(get("POLL_SECONDS", "300"))),
        reminder_minutes=reminder_minutes,
        summary_impacts=summary_impacts,
        send_summary_on_start=_parse_bool(get("SEND_SUMMARY_ON_START", "true")),
        summary_grace_minutes=max(0, int(get("SUMMARY_GRACE_MINUTES", "180"))),
        state_file=Path(get("STATE_FILE", "data/state.json")),
        snapshot_file=Path(get("SNAPSHOT_FILE", "data/latest.json")),
        request_timeout_seconds=max(5, int(get("REQUEST_TIMEOUT_SECONDS", "20"))),
    )


def _read_config_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _parse_time(value: str) -> time:
    hours, minutes = value.split(":", 1)
    return time(hour=int(hours), minute=int(minutes))


def _parse_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on", "tak"}
