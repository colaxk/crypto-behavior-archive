from __future__ import annotations

from datetime import timedelta

from src.models import Event, parse_datetime
from src.storage import load_events


def query_events(
    asset: str | None = None,
    tag: str | None = None,
    event_type: str | None = None,
    days: int | None = None,
) -> list[Event]:
    events = load_events()
    if asset:
        events = [event for event in events if event.asset == asset.upper()]
    if tag:
        events = [event for event in events if tag in event.tags]
    if event_type:
        events = [event for event in events if event.event_type == event_type]
    if days:
        latest_time = max((parse_datetime(event.event_time) for event in events), default=None)
        if latest_time:
            cutoff = latest_time - timedelta(days=days)
            events = [event for event in events if parse_datetime(event.event_time) >= cutoff]
    return sorted(events, key=lambda event: parse_datetime(event.event_time), reverse=True)
