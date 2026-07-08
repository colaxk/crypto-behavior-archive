from __future__ import annotations

from datetime import timedelta
from typing import Any

from src.models import OUTCOME_WINDOWS, Event, parse_datetime, pct_change, to_iso
from src.storage import load_prices

WINDOW_DELTAS = {
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "24h": timedelta(hours=24),
    "3d": timedelta(days=3),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

WINDOW_TOLERANCES = {
    "1h": timedelta(minutes=30),
    "4h": timedelta(minutes=45),
    "24h": timedelta(hours=3),
    "3d": timedelta(hours=12),
    "7d": timedelta(hours=12),
    "30d": timedelta(days=1),
}


def update_event_outcome(event: Event) -> Event:
    prices = load_prices(event.asset)
    price_points = sorted(
        [
            {
                "timestamp": parse_datetime(row["timestamp"]),
                "price": float(row["price"]),
            }
            for row in prices
            if row.get("price")
        ],
        key=lambda row: row["timestamp"],
    )
    event_time = parse_datetime(event.event_time)
    outcome: dict[str, Any] = dict(event.outcome or {})

    for window in OUTCOME_WINDOWS:
        target_time = event_time + WINDOW_DELTAS[window]
        nearest = nearest_price(price_points, target_time, WINDOW_TOLERANCES[window])
        if not nearest:
            outcome[window] = {"status": "missing_price"}
            continue
        outcome[window] = {
            "target_time": to_iso(target_time),
            "matched_time": to_iso(nearest["timestamp"]),
            "matched_price": nearest["price"],
            "change_pct": pct_change(event.price, nearest["price"]),
        }

    event.outcome = outcome
    event.updated_at = to_iso(parse_datetime(None))
    return event


def nearest_price(
    price_points: list[dict[str, Any]],
    target_time: Any,
    tolerance: timedelta,
) -> dict[str, Any] | None:
    if not price_points:
        return None
    nearest = min(price_points, key=lambda row: abs(row["timestamp"] - target_time))
    if abs(nearest["timestamp"] - target_time) > tolerance:
        return None
    return nearest
