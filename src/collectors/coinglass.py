from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.models import Snapshot, require_asset, to_iso
from src.storage import ROOT

PAGE_URLS = {
    "BTC": "https://www.coinglass.com/currencies/BTC",
    "ETH": "https://www.coinglass.com/currencies/ETH",
    "WLD": "https://www.coinglass.com/currencies/WLD",
}


class DataFetchError(RuntimeError):
    pass

METRIC_ALIASES = {
    "oi": ("openInterest", "open_interest", "sumOpenInterest", "totalOpenInterest", "oi"),
    "funding_rate": ("fundingRate", "funding_rate", "avgFundingRate"),
    "liquidation_total": ("liquidation", "liquidations", "totalLiquidation", "liq"),
    "long_liquidation": ("longLiquidation", "long_liquidation", "longLiq"),
    "short_liquidation": ("shortLiquidation", "short_liquidation", "shortLiq"),
    "long_short_ratio": ("longShortRatio", "long_short_ratio", "longShortRate", "lsRatio"),
}


def fetch_page_metrics(asset: str, save_raw: bool = True) -> tuple[dict[str, Any], Path | None, Path]:
    asset = require_asset(asset)
    url = PAGE_URLS[asset]
    html = fetch_html(url)
    raw_path = save_raw_page(asset, html) if save_raw else None
    metrics = parse_metrics_from_html(html)
    metrics.update(
        {
            "asset": asset,
            "source": "coinglass_page",
            "url": url,
            "fetched_at": to_iso(datetime.now().astimezone()),
        }
    )
    metrics_path = save_metrics(asset, metrics)
    return metrics, raw_path, metrics_path


def metrics_to_snapshot(metrics: dict[str, Any], price: float | None = None) -> Snapshot:
    if price is None:
        price = float(metrics.get("price") or 0)
    return Snapshot.from_args(
        timestamp=metrics.get("fetched_at"),
        asset=metrics["asset"],
        price=price,
        oi=as_float(metrics.get("oi")),
        funding_rate=as_float(metrics.get("funding_rate")),
        liquidation_total=as_float(metrics.get("liquidation_total")),
        long_liquidation=as_float(metrics.get("long_liquidation")),
        short_liquidation=as_float(metrics.get("short_liquidation")),
        long_short_ratio=as_float(metrics.get("long_short_ratio")),
        note=f"CoinGlass page scrape: {metrics.get('url')}",
    )


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
        },
    )
    try:
        with urlopen(request, timeout=25) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise DataFetchError(f"CoinGlass HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise DataFetchError(f"CoinGlass network error: {exc.reason}") from exc


def parse_metrics_from_html(html: str) -> dict[str, Any]:
    payloads = extract_json_payloads(html)
    metrics: dict[str, Any] = {}
    for metric_name, aliases in METRIC_ALIASES.items():
        value = find_first_metric(payloads, aliases)
        if value is not None:
            metrics[metric_name] = value
    return metrics


def extract_json_payloads(html: str) -> list[Any]:
    payloads: list[Any] = []
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if match:
        payloads.append(json.loads(match.group(1)))
    for match in re.finditer(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>', html, re.S):
        raw = match.group(1).strip()
        if not raw:
            continue
        try:
            payloads.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return payloads


def find_first_metric(payloads: list[Any], aliases: tuple[str, ...]) -> Any:
    for payload in payloads:
        for key, value in walk_json(payload):
            if key in aliases and is_metric_value(value):
                return value
    return None


def walk_json(value: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def is_metric_value(value: Any) -> bool:
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(re.fullmatch(r"-?\d+(\.\d+)?%?", value.strip()))
    return False


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        value = value.strip().rstrip("%")
    return float(value)


def save_raw_page(asset: str, html: str) -> Path:
    raw_dir = ROOT / "data" / "raw" / "coinglass"
    raw_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    path = raw_dir / f"{asset}_page_{now}.html"
    path.write_text(html, encoding="utf-8")
    return path


def save_metrics(asset: str, metrics: dict[str, Any]) -> Path:
    raw_dir = ROOT / "data" / "raw" / "coinglass"
    raw_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    path = raw_dir / f"{asset}_metrics_{now}.json"
    path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
