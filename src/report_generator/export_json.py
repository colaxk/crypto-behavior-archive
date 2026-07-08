from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from src.analyzers.behavior import build_behavior_archive
from src.models import parse_datetime
from src.storage import REPORTS_DIR, ROOT, load_events, load_prices, load_snapshots

DOCS_DIR = ROOT / "docs"
DOCS_DATA_DIR = DOCS_DIR / "data"
DOCS_REPORTS_DIR = DOCS_DIR / "reports"
ASSETS = ("BTC", "ETH", "WLD")


def export_json() -> list[Path]:
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    snapshots = normalize_rows(load_snapshots())
    prices = normalize_rows(load_prices())
    events = [event.to_dict() for event in load_events()]
    reports = export_reports()
    hypotheses = build_hypotheses(snapshots, events)
    behavior = build_behavior_archive(snapshots, events)

    written = [
        write_json(DOCS_DATA_DIR / "snapshots.json", snapshots),
        write_json(DOCS_DATA_DIR / "events.json", events),
        write_json(DOCS_DATA_DIR / "behavior.json", behavior),
        write_json(DOCS_DATA_DIR / "hypotheses.json", hypotheses),
        write_json(DOCS_DATA_DIR / "reports.json", reports),
    ]
    for asset in ASSETS:
        rows = [row for row in prices if row.get("asset") == asset]
        written.append(write_json(DOCS_DATA_DIR / f"prices_{asset}.json", rows))
    return written


def normalize_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        item: dict[str, Any] = {}
        for key, value in row.items():
            if value in (None, ""):
                item[key] = None
            elif key in {"asset", "timestamp", "source", "note", "heatmap"}:
                item[key] = value
            else:
                item[key] = maybe_number(value)
        normalized.append(item)
    return sorted(normalized, key=lambda item: item.get("timestamp") or "")


def maybe_number(value: str) -> int | float | str:
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer():
        return int(number)
    return number


def export_reports() -> list[dict[str, Any]]:
    reports = []
    existing = {path.name for path in REPORTS_DIR.glob("*.md")}
    for stale in DOCS_REPORTS_DIR.glob("*.md"):
        if stale.name not in existing:
            stale.unlink()
    for path in sorted(REPORTS_DIR.glob("*.md")):
        target = DOCS_REPORTS_DIR / path.name
        shutil.copyfile(path, target)
        text = path.read_text(encoding="utf-8")
        reports.append(
            {
                "date": date_from_report_name(path),
                "title": first_title(text) or path.stem,
                "path": f"reports/{path.name}",
                "summary": summarize(text),
            }
        )
    return reports


def build_hypotheses(snapshots: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    latest = {}
    for asset in ASSETS:
        rows = [row for row in snapshots if row.get("asset") == asset and row.get("timestamp")]
        latest[asset] = rows[-1] if rows else {}
    verified = []
    for event in events:
        outcome = event.get("outcome") or {}
        compact = []
        for window in ("1h", "4h", "24h", "3d", "7d", "30d"):
            result = outcome.get(window)
            if isinstance(result, dict) and result.get("change_pct") is not None:
                compact.append(f"{window}:{result['change_pct']}%")
        if compact:
            verified.append(
                {
                    "event_id": event.get("event_id"),
                    "asset": event.get("asset"),
                    "title": event.get("title"),
                    "outcome": " ".join(compact),
                }
            )
    return {
        "current": [
            "BTC/ETH/WLD 当前结构需要结合 OI、Funding、成交量、异常事件和 BTC 大盘环境判断。",
            "CVD 当前使用 Binance Futures taker buy/sell 近似值。",
            "Heatmap / 清算地图仍需接入稳定数据源。",
        ],
        "verified": verified[:10],
        "pending": [
            "验证 Funding 与 OI 同向升温后，价格 1h/4h/24h/3d/7d/30d 表现是否持续。",
            "验证 BTC 下跌时 WLD 和 ETH 的相对强弱。",
            "补充更稳定的爆仓与 Heatmap 数据源。",
        ],
        "latest_snapshot_time": max(
            [row.get("timestamp") for row in latest.values() if row.get("timestamp")] or [None]
        ),
    }


def date_from_report_name(path: Path) -> str:
    return path.name.replace("_daily_report.md", "")


def first_title(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def summarize(text: str, max_lines: int = 18) -> str:
    lines = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#"):
            continue
        lines.append(clean)
        if len(lines) >= max_lines:
            break
    return "\n".join(lines)


def write_json(path: Path, payload: Any) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
