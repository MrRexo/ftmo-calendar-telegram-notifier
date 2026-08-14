"""Rules deciding which FTMO events may trigger notifications."""

from datetime import time
from zoneinfo import ZoneInfo

from .models import EconomicEvent


def is_event_in_notification_window(
    event: EconomicEvent,
    timezone: ZoneInfo,
    start_time: time,
    end_time: time,
    exclude_weekends: bool = True,
) -> bool:
    """Return whether an event is eligible based on its local date and time."""
    local_event_time = event.date.astimezone(timezone)

    if exclude_weekends and local_event_time.weekday() >= 5:
        return False

    event_time = local_event_time.time().replace(tzinfo=None)
    return start_time <= event_time <= end_time
