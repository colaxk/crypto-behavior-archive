from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from src.analyzers.outcomes import update_event_outcome
from src.analyzers.queries import query_events
from src.collectors.binance import DataFetchError as BinanceFetchError
from src.collectors.binance import backfill_prices, fetch_24h_snapshot
from src.collectors.coinglass import DataFetchError as CoinGlassFetchError
from src.collectors.coinglass import as_float, fetch_page_metrics, metrics_to_snapshot
from src.models import Event, PricePoint, Snapshot, parse_datetime, to_iso
from src.report_generator.dashboard import generate_dashboard
from src.report_generator.markdown import generate_daily_report
from src.storage import (
    add_event,
    add_price,
    add_snapshot,
    import_snapshots,
    init_storage,
    load_events,
    save_events,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="crypto-behavior-archive",
        description="Local MVP for crypto behavior snapshots, events, queries, and reports.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create local project data directories and empty data files.")

    snapshot = subparsers.add_parser("add-snapshot", help="Add a BTC/WLD daily snapshot.")
    snapshot.add_argument("--asset", required=True)
    snapshot.add_argument("--timestamp")
    snapshot.add_argument("--price", required=True, type=float)
    snapshot.add_argument("--change-24h", dest="change_24h", type=float)
    snapshot.add_argument("--volume-24h", dest="volume_24h", type=float)
    snapshot.add_argument("--oi", type=float)
    snapshot.add_argument("--oi-change", dest="oi_change_rate", type=float)
    snapshot.add_argument("--funding-rate", type=float)
    snapshot.add_argument("--liquidation-total", type=float)
    snapshot.add_argument("--long-liquidation", type=float)
    snapshot.add_argument("--short-liquidation", type=float)
    snapshot.add_argument("--long-short-ratio", type=float)
    snapshot.add_argument("--spot-volume", type=float)
    snapshot.add_argument("--futures-volume", type=float)
    snapshot.add_argument("--note", default="")

    import_parser = subparsers.add_parser("import-snapshots", help="Import snapshots from CSV.")
    import_parser.add_argument("path")

    price = subparsers.add_parser("add-price", help="Add a price point for outcome calculations.")
    price.add_argument("--asset", required=True)
    price.add_argument("--time", dest="timestamp", required=True)
    price.add_argument("--price", required=True, type=float)
    price.add_argument("--source", default="manual")
    price.add_argument("--note", default="")

    backfill = subparsers.add_parser("backfill-prices", help="Backfill BTC/WLD prices from Binance klines.")
    backfill.add_argument("--asset", required=True, choices=["BTC", "WLD"])
    backfill.add_argument("--interval", default="1h")
    backfill.add_argument("--start", help="ISO datetime, e.g. 2026-06-01T00:00:00+08:00")
    backfill.add_argument("--end", help="ISO datetime, e.g. 2026-06-23T00:00:00+08:00")
    backfill.add_argument("--limit", type=int, default=500)
    backfill.add_argument("--no-raw", action="store_true")

    binance_snapshot = subparsers.add_parser("fetch-binance-snapshot", help="Fetch Binance 24h ticker snapshot.")
    binance_snapshot.add_argument("--asset", required=True, choices=["BTC", "WLD"])

    coinglass = subparsers.add_parser("fetch-coinglass", help="Fetch CoinGlass BTC/WLD page and parse available metrics.")
    coinglass.add_argument("--asset", required=True, choices=["BTC", "WLD"])
    coinglass.add_argument("--price", type=float, help="Price to use if CoinGlass page does not expose one.")
    coinglass.add_argument("--write-snapshot", action="store_true")

    daily = subparsers.add_parser("daily-collect", help="Collect daily BTC/WLD data from Binance and CoinGlass.")
    daily.add_argument("--assets", nargs="*", default=["BTC", "WLD"], choices=["BTC", "WLD"])
    daily.add_argument("--interval", default="1h")
    daily.add_argument("--kline-limit", type=int, default=24)
    daily.add_argument("--skip-coinglass", action="store_true")

    event = subparsers.add_parser("add-event", help="Record an abnormal behavior event.")
    event.add_argument("--asset", required=True)
    event.add_argument("--event-time", required=True)
    event.add_argument("--event-type", required=True)
    event.add_argument("--price", required=True, type=float)
    event.add_argument("--title", required=True)
    event.add_argument("--description", default="")
    event.add_argument("--tags", nargs="*", default=["未知"])
    event.add_argument("--source", default="manual")
    event.add_argument("--related-assets", nargs="*", default=[])

    update = subparsers.add_parser("update-outcomes", help="Update event forward returns from price points.")
    update.add_argument("--event-id")
    update.add_argument("--asset")
    update.add_argument("--all", action="store_true")

    list_events = subparsers.add_parser("list-events", help="List events.")
    list_events.add_argument("--asset")
    list_events.add_argument("--tag")
    list_events.add_argument("--event-type")

    query = subparsers.add_parser("query", help="Query historical events.")
    query.add_argument("--asset")
    query.add_argument("--tag")
    query.add_argument("--event-type")
    query.add_argument("--days", type=int)

    report = subparsers.add_parser("generate-report", help="Generate a Markdown daily report.")
    report.add_argument("--date", required=True, help="YYYY-MM-DD")

    subparsers.add_parser("generate-dashboard", help="Generate docs/index.html static dashboard.")

    seed = subparsers.add_parser("seed-demo", help="Create demo BTC/WLD data for a quick smoke test.")
    seed.add_argument("--date", default=date.today().isoformat())

    args = parser.parse_args()
    init_storage()

    if args.command == "init":
        print("Initialized local data directories and files.")
    elif args.command == "add-snapshot":
        handle_add_snapshot(args)
    elif args.command == "import-snapshots":
        count = import_snapshots(Path(args.path))
        print(f"Imported {count} snapshots.")
    elif args.command == "add-price":
        handle_add_price(args)
    elif args.command == "backfill-prices":
        handle_backfill_prices(args)
    elif args.command == "fetch-binance-snapshot":
        handle_fetch_binance_snapshot(args)
    elif args.command == "fetch-coinglass":
        handle_fetch_coinglass(args)
    elif args.command == "daily-collect":
        handle_daily_collect(args)
    elif args.command == "add-event":
        handle_add_event(args)
    elif args.command == "update-outcomes":
        handle_update_outcomes(args)
    elif args.command in {"list-events", "query"}:
        handle_query(args)
    elif args.command == "generate-report":
        path = generate_daily_report(date.fromisoformat(args.date))
        print(f"Generated report: {path}")
    elif args.command == "generate-dashboard":
        path = generate_dashboard()
        print(f"Generated dashboard: {path}")
    elif args.command == "seed-demo":
        handle_seed_demo(args)


def handle_add_snapshot(args: argparse.Namespace) -> None:
    snapshot = Snapshot.from_args(
        timestamp=args.timestamp,
        asset=args.asset,
        price=args.price,
        change_24h=args.change_24h,
        volume_24h=args.volume_24h,
        oi=args.oi,
        oi_change_rate=args.oi_change_rate,
        funding_rate=args.funding_rate,
        liquidation_total=args.liquidation_total,
        long_liquidation=args.long_liquidation,
        short_liquidation=args.short_liquidation,
        long_short_ratio=args.long_short_ratio,
        spot_volume=args.spot_volume,
        futures_volume=args.futures_volume,
        note=args.note,
    )
    add_snapshot(snapshot)
    print(f"Added snapshot: {snapshot.asset} {snapshot.timestamp} price={snapshot.price}")


def handle_add_price(args: argparse.Namespace) -> None:
    price = PricePoint.from_args(
        timestamp=args.timestamp,
        asset=args.asset,
        price=args.price,
        source=args.source,
        note=args.note,
    )
    add_price(price)
    print(f"Added price: {price.asset} {price.timestamp} price={price.price}")


def handle_backfill_prices(args: argparse.Namespace) -> None:
    try:
        added, raw_path = backfill_prices(
            asset=args.asset,
            interval=args.interval,
            start=args.start,
            end=args.end,
            limit=args.limit,
            save_raw=not args.no_raw,
        )
    except BinanceFetchError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"Backfilled {added} new price points from Binance for {args.asset}.")
    if raw_path:
        print(f"Saved raw klines: {raw_path}")


def handle_fetch_binance_snapshot(args: argparse.Namespace) -> None:
    try:
        snapshot = fetch_24h_snapshot(args.asset)
    except BinanceFetchError as exc:
        raise SystemExit(str(exc)) from exc
    add_snapshot(snapshot)
    print(f"Added Binance snapshot: {snapshot.asset} {snapshot.timestamp} price={snapshot.price}")


def handle_fetch_coinglass(args: argparse.Namespace) -> None:
    try:
        metrics, raw_path, metrics_path = fetch_page_metrics(args.asset)
    except CoinGlassFetchError as exc:
        raise SystemExit(str(exc)) from exc
    found = {key: value for key, value in metrics.items() if key not in {"asset", "source", "url", "fetched_at"}}
    print(f"Fetched CoinGlass page for {args.asset}.")
    if raw_path:
        print(f"Saved raw page: {raw_path}")
    print(f"Saved parsed metrics: {metrics_path}")
    if found:
        print("Parsed metrics:")
        for key, value in found.items():
            print(f"- {key}: {value}")
    else:
        print("No structured metrics parsed from the page. Raw HTML and metrics JSON were saved for review.")
    if args.write_snapshot:
        if args.price is None and not metrics.get("price"):
            raise SystemExit("--write-snapshot requires --price when the page does not expose price.")
        snapshot = metrics_to_snapshot(metrics, price=args.price)
        add_snapshot(snapshot)
        print(f"Added CoinGlass snapshot: {snapshot.asset} {snapshot.timestamp}")


def handle_daily_collect(args: argparse.Namespace) -> None:
    for asset in args.assets:
        print(f"Collecting {asset}...")
        try:
            added_prices, raw_klines = backfill_prices(
                asset=asset,
                interval=args.interval,
                limit=args.kline_limit,
                save_raw=True,
            )
            snapshot = fetch_24h_snapshot(asset)
        except BinanceFetchError as exc:
            print(f"- Binance failed: {exc}")
            continue

        print(f"- Binance prices added: {added_prices}")
        if raw_klines:
            print(f"- Binance raw klines: {raw_klines}")

        if not args.skip_coinglass:
            try:
                metrics, raw_page, metrics_path = fetch_page_metrics(asset)
                snapshot.oi = as_float(metrics.get("oi"))
                snapshot.funding_rate = as_float(metrics.get("funding_rate"))
                snapshot.liquidation_total = as_float(metrics.get("liquidation_total"))
                snapshot.long_liquidation = as_float(metrics.get("long_liquidation"))
                snapshot.short_liquidation = as_float(metrics.get("short_liquidation"))
                snapshot.long_short_ratio = as_float(metrics.get("long_short_ratio"))
                snapshot.note = f"{snapshot.note}; CoinGlass page metrics"
                print(f"- CoinGlass raw page: {raw_page}")
                print(f"- CoinGlass metrics: {metrics_path}")
            except CoinGlassFetchError as exc:
                snapshot.note = f"{snapshot.note}; CoinGlass failed: {exc}"
                print(f"- CoinGlass failed: {exc}")

        add_snapshot(snapshot)
        print(f"- Snapshot saved: {snapshot.asset} {snapshot.timestamp} price={snapshot.price}")


def handle_add_event(args: argparse.Namespace) -> None:
    event = Event.from_args(
        asset=args.asset,
        event_time=args.event_time,
        event_type=args.event_type,
        price=args.price,
        title=args.title,
        description=args.description,
        tags=args.tags,
        source=args.source,
        related_assets=args.related_assets,
    )
    add_event(event)
    print(f"Added event: {event.event_id}")


def handle_update_outcomes(args: argparse.Namespace) -> None:
    events = load_events()
    updated_ids = []
    for idx, event in enumerate(events):
        should_update = args.all
        should_update = should_update or (args.event_id and event.event_id == args.event_id)
        should_update = should_update or (args.asset and event.asset == args.asset.upper())
        if should_update:
            events[idx] = update_event_outcome(event)
            updated_ids.append(event.event_id)
    save_events(events)
    print(f"Updated {len(updated_ids)} events.")
    for event_id in updated_ids:
        print(f"- {event_id}")


def handle_query(args: argparse.Namespace) -> None:
    events = query_events(
        asset=args.asset,
        tag=args.tag,
        event_type=args.event_type,
        days=getattr(args, "days", None),
    )
    if not events:
        print("No events found.")
        return
    for event in events:
        tags = ", ".join(event.tags)
        print(f"{event.event_id} | {event.event_time} | {event.asset} | {event.event_type} | {event.title} | {tags}")
        if event.outcome:
            changes = []
            for window, result in event.outcome.items():
                if isinstance(result, dict) and "change_pct" in result:
                    changes.append(f"{window}:{result['change_pct']}%")
            if changes:
                print(f"  outcomes: {' '.join(changes)}")


def handle_seed_demo(args: argparse.Namespace) -> None:
    day = date.fromisoformat(args.date)
    base_dt = datetime.fromisoformat(f"{day.isoformat()}T12:00:00+08:00")
    base = to_iso(base_dt)
    snapshots = [
        Snapshot.from_args(
            timestamp=base,
            asset="BTC",
            price=65000,
            change_24h=2.1,
            volume_24h=35000000000,
            oi=18500000000,
            oi_change_rate=3.4,
            funding_rate=0.006,
            liquidation_total=180000000,
            long_liquidation=70000000,
            short_liquidation=110000000,
            long_short_ratio=1.08,
            spot_volume=12000000000,
            futures_volume=42000000000,
            note="Demo BTC snapshot",
        ),
        Snapshot.from_args(
            timestamp=base,
            asset="WLD",
            price=3.25,
            change_24h=8.6,
            volume_24h=260000000,
            oi=95000000,
            oi_change_rate=16.8,
            funding_rate=0.021,
            liquidation_total=7800000,
            long_liquidation=2300000,
            short_liquidation=5500000,
            long_short_ratio=1.42,
            spot_volume=90000000,
            futures_volume=410000000,
            note="Demo WLD funding and OI heating up",
        ),
    ]
    for snapshot in snapshots:
        add_snapshot(snapshot)

    for timestamp, price_value in [
        (base, 3.25),
        (to_iso(base_dt + timedelta(hours=1)), 3.31),
        (to_iso(base_dt + timedelta(hours=4)), 3.44),
        (to_iso(base_dt + timedelta(hours=24)), 3.38),
        (to_iso(base_dt + timedelta(days=3)), 3.12),
        (to_iso(base_dt + timedelta(days=7)), 3.72),
    ]:
        add_price(PricePoint.from_args(timestamp=timestamp, asset="WLD", price=price_value, source="demo"))

    event = Event.from_args(
        asset="WLD",
        event_time=base,
        event_type="funding_hot",
        price=3.25,
        title="WLD Funding 与 OI 同步升温",
        description="Demo event: Funding 过热，OI 增速明显，观察是否为合约推动行情。",
        tags=["Funding异常升高", "OI暴增", "合约推动"],
        source="demo",
        related_assets=["BTC"],
    )
    add_event(update_event_outcome(event))
    path = generate_daily_report(day)
    print(f"Seeded demo data and generated report: {path}")


if __name__ == "__main__":
    main()
