from __future__ import annotations

import csv
import json
from dataclasses import fields
from pathlib import Path
from typing import Any, Iterable

from src.models import Event, PricePoint, Snapshot, parse_datetime

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS_CSV = ROOT / "data" / "processed" / "snapshots.csv"
PRICES_CSV = ROOT / "data" / "processed" / "prices.csv"
EVENTS_JSONL = ROOT / "events" / "events.jsonl"
REPORTS_DIR = ROOT / "reports"


def init_storage() -> None:
    for path in [
        ROOT / "data" / "raw",
        ROOT / "data" / "processed",
        ROOT / "data" / "screenshots",
        ROOT / "assets" / "BTC",
        ROOT / "assets" / "ETH",
        ROOT / "assets" / "WLD",
        ROOT / "events",
        ROOT / "reports",
        ROOT / "notebooks",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    ensure_csv(SNAPSHOTS_CSV, Snapshot)
    ensure_csv(PRICES_CSV, PricePoint)
    EVENTS_JSONL.touch(exist_ok=True)


def ensure_csv(path: Path, model: type[Any]) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field.name for field in fields(model)])
        writer.writeheader()


def append_csv(path: Path, model: type[Any], row: dict[str, Any]) -> None:
    ensure_csv(path, model)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field.name for field in fields(model)])
        writer.writerow(row)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def add_snapshot(snapshot: Snapshot) -> None:
    append_csv(SNAPSHOTS_CSV, Snapshot, snapshot.to_dict())


def add_price(price: PricePoint) -> None:
    append_csv(PRICES_CSV, PricePoint, price.to_dict())


def add_prices_dedup(prices: Iterable[PricePoint]) -> int:
    ensure_csv(PRICES_CSV, PricePoint)
    existing = {
        (row.get("asset", "").upper(), row.get("timestamp"), row.get("source", ""))
        for row in read_csv(PRICES_CSV)
    }
    added = 0
    with PRICES_CSV.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[field.name for field in fields(PricePoint)])
        for price in prices:
            key = (price.asset.upper(), price.timestamp, price.source)
            if key in existing:
                continue
            writer.writerow(price.to_dict())
            existing.add(key)
            added += 1
    return added


def import_snapshots(path: Path) -> int:
    rows = read_csv(path)
    count = 0
    for row in rows:
        snapshot = Snapshot.from_args(
            timestamp=row.get("timestamp") or row.get("date") or row.get("datetime") or None,
            asset=(row.get("asset") or "").upper(),
            price=float(row["price"]),
            change_24h=_float(row.get("change_24h")),
            volume_24h=_float(row.get("volume_24h")),
            oi=_float(row.get("oi")),
            oi_change_rate=_float(row.get("oi_change_rate") or row.get("oi_change")),
            funding_rate=_float(row.get("funding_rate")),
            liquidation_total=_float(row.get("liquidation_total")),
            long_liquidation=_float(row.get("long_liquidation")),
            short_liquidation=_float(row.get("short_liquidation")),
            long_short_ratio=_float(row.get("long_short_ratio")),
            spot_volume=_float(row.get("spot_volume")),
            futures_volume=_float(row.get("futures_volume")),
            note=row.get("note") or "",
        )
        add_snapshot(snapshot)
        count += 1
    return count


def add_event(event: Event) -> None:
    EVENTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")


def load_events() -> list[Event]:
    if not EVENTS_JSONL.exists():
        return []
    events = []
    with EVENTS_JSONL.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            events.append(Event(**payload))
    return events


def save_events(events: Iterable[Event]) -> None:
    EVENTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_JSONL.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")


def load_snapshots(asset: str | None = None) -> list[dict[str, str]]:
    rows = read_csv(SNAPSHOTS_CSV)
    if asset:
        return [row for row in rows if row.get("asset", "").upper() == asset.upper()]
    return rows


def load_prices(asset: str | None = None) -> list[dict[str, str]]:
    rows = read_csv(PRICES_CSV)
    if asset:
        return [row for row in rows if row.get("asset", "").upper() == asset.upper()]
    return rows


def latest_snapshot(asset: str) -> dict[str, str] | None:
    rows = sorted(
        load_snapshots(asset),
        key=lambda item: parse_datetime(item["timestamp"]),
        reverse=True,
    )
    return rows[0] if rows else None


def _float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
