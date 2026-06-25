from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.models import PricePoint, Snapshot, parse_datetime, require_asset, to_iso
from src.storage import ROOT, add_prices_dedup

BINANCE_BASE_URL = "https://api.binance.com"
BINANCE_FUTURES_BASE_URL = "https://fapi.binance.com"
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


def fetch_futures_metrics(asset: str) -> dict[str, float | str | None]:
    asset = require_asset(asset)
    symbol = SYMBOLS[asset]
    premium = http_get_json(f"{BINANCE_FUTURES_BASE_URL}/fapi/v1/premiumIndex", {"symbol": symbol})
    open_interest = http_get_json(f"{BINANCE_FUTURES_BASE_URL}/fapi/v1/openInterest", {"symbol": symbol})
    ticker = http_get_json(f"{BINANCE_FUTURES_BASE_URL}/fapi/v1/ticker/24hr", {"symbol": symbol})
    long_short = fetch_optional_json(
        f"{BINANCE_FUTURES_BASE_URL}/futures/data/globalLongShortAccountRatio",
        {"symbol": symbol, "period": "5m", "limit": 1},
    )
    taker_flow = fetch_optional_json(
        f"{BINANCE_FUTURES_BASE_URL}/futures/data/takerlongshortRatio",
        {"symbol": symbol, "period": "1h", "limit": 24},
    )
    liquidations = fetch_liquidations(symbol)
    mark_price = float(premium.get("markPrice") or ticker.get("lastPrice") or 0)
    oi_contracts = float(open_interest.get("openInterest") or 0)
    return {
        "funding_rate": float(premium.get("lastFundingRate") or 0) * 100,
        "oi": oi_contracts * mark_price if mark_price else oi_contracts,
        "futures_volume": float(ticker.get("quoteVolume") or 0),
        "long_short_ratio": latest_long_short_ratio(long_short),
        "cvd": taker_cvd(taker_flow),
        "liquidation_total": liquidations["total"],
        "long_liquidation": liquidations["long"],
        "short_liquidation": liquidations["short"],
        "heatmap": "未接入",
    }


def apply_futures_metrics(snapshot: Snapshot, metrics: dict[str, float | str | None]) -> Snapshot:
    snapshot.funding_rate = metrics.get("funding_rate") if metrics.get("funding_rate") is not None else snapshot.funding_rate
    snapshot.oi = metrics.get("oi") if metrics.get("oi") is not None else snapshot.oi
    snapshot.futures_volume = metrics.get("futures_volume") if metrics.get("futures_volume") is not None else snapshot.futures_volume
    snapshot.long_short_ratio = metrics.get("long_short_ratio") if metrics.get("long_short_ratio") is not None else snapshot.long_short_ratio
    snapshot.cvd = metrics.get("cvd") if metrics.get("cvd") is not None else snapshot.cvd
    snapshot.liquidation_total = (
        metrics.get("liquidation_total") if metrics.get("liquidation_total") is not None else snapshot.liquidation_total
    )
    snapshot.long_liquidation = (
        metrics.get("long_liquidation") if metrics.get("long_liquidation") is not None else snapshot.long_liquidation
    )
    snapshot.short_liquidation = (
        metrics.get("short_liquidation") if metrics.get("short_liquidation") is not None else snapshot.short_liquidation
    )
    snapshot.heatmap = str(metrics.get("heatmap") or snapshot.heatmap or "")
    snapshot.note = f"{snapshot.note}; Binance futures metrics"
    return snapshot


def fetch_optional_json(url: str, params: dict[str, object]) -> object | None:
    try:
        return http_get_json(url, params)
    except DataFetchError:
        return None


def latest_long_short_ratio(payload: object | None) -> float | None:
    if not isinstance(payload, list) or not payload:
        return None
    latest = payload[-1]
    if not isinstance(latest, dict):
        return None
    value = latest.get("longShortRatio")
    return float(value) if value not in (None, "") else None


def taker_cvd(payload: object | None) -> float | None:
    if not isinstance(payload, list):
        return None
    total = 0.0
    seen = False
    for row in payload:
        if not isinstance(row, dict):
            continue
        buy = row.get("buyVol")
        sell = row.get("sellVol")
        if buy in (None, "") or sell in (None, ""):
            continue
        total += float(buy) - float(sell)
        seen = True
    return round(total, 4) if seen else None


def fetch_liquidations(symbol: str) -> dict[str, float | None]:
    end_time = datetime.now().astimezone()
    start_time = end_time - timedelta(hours=24)
    payload = fetch_optional_json(
        f"{BINANCE_FUTURES_BASE_URL}/fapi/v1/allForceOrders",
        {
            "symbol": symbol,
            "startTime": to_milliseconds(start_time),
            "endTime": to_milliseconds(end_time),
            "limit": 1000,
        },
    )
    if not isinstance(payload, list):
        return {"total": None, "long": None, "short": None}
    long_total = 0.0
    short_total = 0.0
    for order in payload:
        if not isinstance(order, dict):
            continue
        side = order.get("side")
        qty = float(order.get("executedQty") or order.get("origQty") or 0)
        price = float(order.get("averagePrice") or order.get("price") or 0)
        notional = qty * price
        if side == "SELL":
            long_total += notional
        elif side == "BUY":
            short_total += notional
    total = long_total + short_total
    return {
        "total": round(total, 4),
        "long": round(long_total, 4),
        "short": round(short_total, 4),
    }


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
