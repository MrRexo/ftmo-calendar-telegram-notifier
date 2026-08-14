from __future__ import annotations

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from ftmo_bot.models import EconomicEvent, PRIORITY_ORDER


SUPPORTED_LANGUAGES = frozenset({"pl", "en"})

PRIORITY_LABELS = {
    "pl": {
        "P0": "🔴 P0 — OBOSTRZENIE FTMO",
        "P1": "🟠 P1 — wysoki wpływ",
        "P2": "🟡 P2 — średni wpływ",
        "P3": "⚪ P3 — niski wpływ",
        "P4": "⚪ P4 — święto / inne",
    },
    "en": {
        "P0": "🔴 P0 — FTMO RESTRICTION",
        "P1": "🟠 P1 — high impact",
        "P2": "🟡 P2 — medium impact",
        "P3": "⚪ P3 — low impact",
        "P4": "⚪ P4 — holiday / other",
    },
}

WEEKDAYS = {
    "pl": (
        "poniedziałek",
        "wtorek",
        "środa",
        "czwartek",
        "piątek",
        "sobota",
        "niedziela",
    ),
    "en": (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ),
}


def format_daily_summary(
    events: list[EconomicEvent],
    timezone: ZoneInfo,
    allowed_impacts: frozenset[str],
    summary_day: date | None = None,
    language: str = "pl",
) -> str:
    language = _validated_language(language)
    day_value = summary_day or (
        events[0].date.astimezone(timezone).date() if events else date.today()
    )
    special_notice = _special_notice(day_value, language)

    if not events:
        lines = [
            "📅 FTMO — dzisiaj nie ma wydarzeń w kalendarzu."
            if language == "pl"
            else "📅 FTMO — no calendar events today."
        ]
        if special_notice:
            lines.extend(["", special_notice])
        return "\n".join(lines)

    local_events = sorted(events, key=lambda event: (PRIORITY_ORDER[event.priority], event.date))
    selected = [event for event in local_events if event.restriction or event.impact in allowed_impacts]
    omitted = len(events) - len(selected)
    local_day = events[0].date.astimezone(timezone).date()
    day = f"{WEEKDAYS[language][local_day.weekday()]}, {local_day:%d.%m.%Y}"
    lines = [f"📅 FTMO — {day}", ""]
    if special_notice:
        lines.extend([special_notice, ""])

    if not selected:
        lines.append(
            "Brak wydarzeń o wybranym poziomie ważności."
            if language == "pl"
            else "No events at the selected importance levels."
        )
    else:
        for event in selected:
            local = event.date.astimezone(timezone)
            lines.extend(_event_lines(event, local, language))
            if event.restriction:
                start = local - timedelta(minutes=2)
                end = local + timedelta(minutes=2)
                if language == "pl":
                    lines.append(f"⛔ Zakaz otwierania/zamykania: {start:%H:%M}–{end:%H:%M}")
                else:
                    lines.append(f"⛔ No opening/closing trades: {start:%H:%M}–{end:%H:%M}")
            lines.append("")

    if omitted:
        if language == "pl":
            lines.append(f"Pominięto {omitted} wydarzeń niskiego priorytetu.")
        else:
            lines.append(f"Omitted {omitted} low-priority events.")
    if language == "pl":
        lines.append(
            f"Czas: {timezone}. Reguła dotyczy FTMO Account Standard; "
            "nie dotyczy Evaluation ani Swing."
        )
    else:
        lines.append(
            f"Time: {timezone}. The rule applies to FTMO Account Standard; "
            "it does not apply to Evaluation or Swing."
        )
    return "\n".join(lines).strip()


def format_restricted_reminder(
    event: EconomicEvent,
    timezone: ZoneInfo,
    minutes_until: int,
    language: str = "pl",
) -> str:
    language = _validated_language(language)
    local = event.date.astimezone(timezone)
    start = local - timedelta(minutes=2)
    end = local + timedelta(minutes=2)
    if language == "pl":
        return "\n".join(
            [
                f"🚨 FTMO P0 — za około {max(0, minutes_until)} min",
                f"{local:%H:%M} — {event.title}",
                f"Instrumenty: {event.instrument}",
                f"⛔ Nie otwieraj ani nie zamykaj pozycji od {start:%H:%M} do {end:%H:%M}.",
                "Dotyczy także aktywacji zleceń oczekujących, SL i TP na FTMO Account Standard.",
            ]
        )
    return "\n".join(
        [
            f"🚨 FTMO P0 — in about {max(0, minutes_until)} min",
            f"{local:%H:%M} — {event.title}",
            f"Instruments: {event.instrument}",
            f"⛔ Do not open or close positions from {start:%H:%M} to {end:%H:%M}.",
            "This also applies to pending-order activation, SL and TP on FTMO Account Standard.",
        ]
    )


def format_release(
    event: EconomicEvent,
    timezone: ZoneInfo,
    language: str = "pl",
) -> str:
    language = _validated_language(language)
    local = event.date.astimezone(timezone)
    end = local + timedelta(minutes=2)
    if language == "pl":
        return "\n".join(
            [
                f"✅ FTMO — publikacja {event.title}",
                f"Wynik: {event.actual or '-'} | Prognoza: {event.forecast or '-'} | Poprzednio: {event.previous or '-'}",
                f"Instrumenty: {event.instrument}",
                f"Obostrzenie wygasa o {end:%H:%M}.",
            ]
        )
    return "\n".join(
        [
            f"✅ FTMO — {event.title} release",
            f"Actual: {event.actual or '-'} | Forecast: {event.forecast or '-'} | Previous: {event.previous or '-'}",
            f"Instruments: {event.instrument}",
            f"The restriction expires at {end:%H:%M}.",
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


def _event_lines(event: EconomicEvent, local, language: str) -> list[str]:
    if language == "pl":
        values = (
            f"Wynik: {event.actual or '-'} | Prognoza: {event.forecast or '-'} "
            f"| Poprzednio: {event.previous or '-'}"
            if event.actual
            else f"Prognoza: {event.forecast or '-'} | Poprzednio: {event.previous or '-'}"
        )
        instruments = "Instrumenty"
    else:
        values = (
            f"Actual: {event.actual or '-'} | Forecast: {event.forecast or '-'} "
            f"| Previous: {event.previous or '-'}"
            if event.actual
            else f"Forecast: {event.forecast or '-'} | Previous: {event.previous or '-'}"
        )
        instruments = "Instruments"
    return [
        PRIORITY_LABELS[language][event.priority],
        f"{local:%H:%M} — {event.title}",
        f"{instruments}: {event.instrument}",
        values,
    ]


def _special_notice(day_value: date, language: str) -> str | None:
    if day_value.day != 13:
        return None
    if language == "pl":
        return "🛑 Dziś 13! Nie graj niczego 🙂"
    return "🛑 Today is the 13th! Do not trade anything 🙂"


def _validated_language(language: str) -> str:
    normalized = language.lower()
    if normalized not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported message language: {language}")
    return normalized
