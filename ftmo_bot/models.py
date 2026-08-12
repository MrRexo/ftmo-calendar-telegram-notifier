from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any


PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


@dataclass(frozen=True)
class EconomicEvent:
    title: str
    impact: str
    instrument: str
    restriction: bool
    event_type: str
    date: datetime
    forecast: str | None
    previous: str | None
    actual: str | None
    article_link: str | None

    @property
    def priority(self) -> str:
        if self.restriction:
            return "P0"
        return {
            "high": "P1",
            "medium": "P2",
            "low": "P3",
            "holiday": "P4",
        }.get(self.impact.lower(), "P4")

    @property
    def stable_id(self) -> str:
        local_day = self.date.date().isoformat()
        raw = f"{self.title}|{self.instrument}|{local_day}"
        return sha256(raw.encode("utf-8")).hexdigest()[:20]

    @property
    def occurrence_id(self) -> str:
        raw = f"{self.stable_id}|{self.date.isoformat()}"
        return sha256(raw.encode("utf-8")).hexdigest()[:24]

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> "EconomicEvent":
        date_value = datetime.fromisoformat(str(item["date"]).replace("Z", "+00:00"))
        if date_value.tzinfo is None:
            raise ValueError("FTMO event date has no timezone")
        return cls(
            title=str(item.get("title") or "Untitled event"),
            impact=str(item.get("impact") or "unknown").lower(),
            instrument=str(item.get("instrument") or "Unknown"),
            restriction=bool(item.get("restriction")),
            event_type=str(item.get("eventType") or "normal"),
            date=date_value,
            forecast=_optional_text(item.get("forecast")),
            previous=_optional_text(item.get("previous")),
            actual=_optional_text(item.get("actual")),
            article_link=_optional_text(item.get("articleLink")),
        )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
