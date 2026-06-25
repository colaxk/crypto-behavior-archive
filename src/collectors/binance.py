from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.models import PricePoint, Snapshot, parse_datetime, require_asset, to_iso
from src.storage import ROOT, add_prices_dedup

BINANCE_BASE_URL = "https://api.binance.com"
SYMBOLS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "WLD": "WLDUSDT",
}


class DataFetchError(RuntimeError):
    pass


def backfill_prices(
    asset: str,
    interval: str = "1h",
    start: str | None = None,
    end: str | None = None,
    limit: int = 500,
    save_raw: bool = True,
) -> tuple[int, Path | None]:
    asset = require_asset(asset)
    symbol = SYMBOLS[asset]
    klines = fetch_klines(symbol=symbol, interval=interval, start=start, end=end, limit=limit)
    if save_raw:
        raw_path = save_raw_klines(asset, symbol, interval, klines)
    else:
        raw_path = None
    prices = [kline_to_price(asset, symbol, interval, item) for item in klines]
    return add_prices_dedup(prices), raw_path


def fetch_24h_snapshot(asset: str) -> Snapshot:
    asset = require_asset(asset)
    symbol = SYMBOLS[asset]
    payload = http_get_json(f"{BINANCE_BASE_URL}/api/v3/ticker/24hr", {"symbol": symbol})
    return Snapshot.from_args(
        timestamp=to_iso(datetime.now().astimezone()),
        asset=asset,
        price=float(payload["lastPrice"]),
        change_24h=float(payload["priceChangePercent"]),
        volume_24h=float(payload["quoteVolume"]),
        spot_volume=float(payload["quoteVolume"]),
        note=f"Binance spot ticker {symbol}",
    )


def fetch_klines(
    symbol: str,
    interval: str,
    start: str | None,
    end: str | None,
    limit: int,
) -> list[list[object]]:
    params: dict[str, object] = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    if start:
        params["startTime"] = to_milliseconds(parse_datetime(start))
    if end:
        params["endTime"] = to_milliseconds(parse_datetime(end))
    return http_get_json(f"{BINANCE_BASE_URL}/api/v3/klines", params)


def http_get_json(url: str, params: dict[str, object]) -> object:
    full_url = f"{url}?{urlencode(params)}"
    request = Request(
        full_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "crypto-behavior-archive/0.1",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise DataFetchError(f"Binance HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise DataFetchError(f"Binance network error: {exc.reason}") from exc


def kline_to_price(asset: str, symbol: str, interval: str, kline: list[object]) -> PricePoint:
    open_time_ms = int(kline[0])
    close_price = float(kline[4])
    timestamp = datetime.fromtimestamp(open_time_ms / 1000).astimezone()
    return PricePoint.from_args(
        timestamp=to_iso(timestamp),
        asset=asset,
        price=close_price,
        source=f"binance:{symbol}:{interval}",
        note="Kline close price",
    )


def save_raw_klines(asset: str, symbol: str, interval: str, klines: list[list[object]]) -> Path:
    raw_dir = ROOT / "data" / "raw" / "binance"
    raw_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    path = raw_dir / f"{asset}_{symbol}_{interval}_{now}.json"
    path.write_text(json.dumps(klines, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def to_milliseconds(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)
