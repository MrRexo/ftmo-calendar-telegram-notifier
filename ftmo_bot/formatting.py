from __future__ import annotations

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from ftmo_bot.models import EconomicEvent, PRIORITY_ORDER


PRIORITY_LABELS = {
    "P0": "🔴 P0 — OBOSTRZENIE FTMO",
    "P1": "🟠 P1 — wysoki wpływ",
    "P2": "🟡 P2 — średni wpływ",
    "P3": "⚪ P3 — niski wpływ",
    "P4": "⚪ P4 — święto / inne",
}


def format_daily_summary(
    events: list[EconomicEvent],
    timezone: ZoneInfo,
    allowed_impacts: frozenset[str],
    summary_day: date | None = None,
) -> str:
    day_value = summary_day or (
        events[0].date.astimezone(timezone).date() if events else date.today()
    )
    special_notice = "🛑 Dziś 13! Nie graj niczego 🙂" if day_value.day == 13 else None

    if not events:
        lines = ["📅 FTMO — dzisiaj nie ma wydarzeń w kalendarzu."]
        if special_notice:
            lines.extend(["", special_notice])
        return "\n".join(lines)

    local_events = sorted(events, key=lambda event: (PRIORITY_ORDER[event.priority], event.date))
    selected = [event for event in local_events if event.restriction or event.impact in allowed_impacts]
    omitted = len(events) - len(selected)
    day = events[0].date.astimezone(timezone).strftime("%A, %d.%m.%Y")
    lines = [f"📅 FTMO — {day}", ""]
    if special_notice:
        lines.extend([special_notice, ""])

    if not selected:
        lines.append("Brak wydarzeń o wybranym poziomie ważności.")
    else:
        for event in selected:
            local = event.date.astimezone(timezone)
            lines.extend(
                [
                    f"{PRIORITY_LABELS[event.priority]}",
                    f"{local:%H:%M} — {event.title}",
                    f"Instrumenty: {event.instrument}",
                    f"Forecast: {event.forecast or '-'} | Previous: {event.previous or '-'}",
                ]
            )
            if event.restriction:
                start = local - timedelta(minutes=2)
                end = local + timedelta(minutes=2)
                lines.append(f"⛔ Zakaz otwierania/zamykania: {start:%H:%M}–{end:%H:%M}")
            lines.append("")

    if omitted:
        lines.append(f"Pominięto {omitted} wydarzeń niskiego priorytetu.")
    lines.append("Czas: Europe/Warsaw. Reguła dotyczy FTMO Account Standard; nie dotyczy Evaluation ani Swing.")
    return "\n".join(lines).strip()


def format_restricted_reminder(event: EconomicEvent, timezone: ZoneInfo, minutes_until: int) -> str:
    local = event.date.astimezone(timezone)
    start = local - timedelta(minutes=2)
    end = local + timedelta(minutes=2)
    return "\n".join(
        [
            f"🚨 FTMO P0 — za około {max(0, minutes_until)} min",
            f"{local:%H:%M} — {event.title}",
            f"Instrumenty: {event.instrument}",
            f"⛔ Nie otwieraj ani nie zamykaj pozycji od {start:%H:%M} do {end:%H:%M}.",
            "Dotyczy także aktywacji zleceń oczekujących, SL i TP na FTMO Account Standard.",
        ]
    )


def format_release(event: EconomicEvent, timezone: ZoneInfo) -> str:
    local = event.date.astimezone(timezone)
    end = local + timedelta(minutes=2)
    return "\n".join(
        [
            f"✅ FTMO — publikacja {event.title}",
            f"Actual: {event.actual or '-'} | Forecast: {event.forecast or '-'} | Previous: {event.previous or '-'}",
            f"Instrumenty: {event.instrument}",
            f"Obostrzenie wygasa o {end:%H:%M}.",
        ]
    )


def split_telegram_message(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for line in text.splitlines(keepends=True):
        if current and current_length + len(line) > limit:
            chunks.append("".join(current).rstrip())
            current = []
            current_length = 0
        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]
        current.append(line)
        current_length += len(line)
    if current:
        chunks.append("".join(current).rstrip())
    return chunks
