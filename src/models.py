from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


SUPPORTED_ASSETS = {"BTC", "ETH", "WLD"}

EVENT_TAGS = {
    "趋势转强",
    "趋势转弱",
    "突破",
    "假突破",
    "跌破",
    "假跌破",
    "加速上涨",
    "加速下跌",
    "震荡",
    "趋势延续",
    "放量突破",
    "放量上涨",
    "放量下跌",
    "放量滞涨",
    "缩量上涨",
    "缩量下跌",
    "缩量阴跌",
    "天量",
    "地量",
    "成交衰减",
    "恐慌下杀",
    "洗盘",
    "派发",
    "吸筹",
    "吸筹观察",
    "换手",
    "换手充分",
    "试盘",
    "诱多",
    "诱空",
    "诱多风险",
    "控盘",
    "撤退",
    "资金试探",
    "合约推动",
    "现货推动",
    "大盘拖累",
    "独立行情",
    "KOL影响",
    "消息驱动",
    "Funding异常升高",
    "Funding异常降低",
    "Funding升高",
    "Funding降低",
    "OI暴增",
    "OI暴减",
    "OI增加",
    "OI减少",
    "OI平稳",
    "大额爆仓",
    "爆仓集中",
    "空头挤压",
    "多头踩踏",
    "多头过热",
    "空头拥挤",
    "空头衰减",
    "杠杆释放",
    "供应释放",
    "供应减少",
    "锁仓增加",
    "解锁压力",
    "长期持仓增加",
    "长期持仓减少",
    "BTC强于ETH",
    "ETH强于BTC",
    "ETH相对强势",
    "ETH相对弱势",
    "AI板块强于BTC",
    "AI板块弱于BTC",
    "山寨轮动",
    "资金回流BTC",
    "资金流向ETH",
    "资金流向AI",
    "资金离开AI",
    "未知",
}

OUTCOME_WINDOWS = ("1h", "4h", "24h", "3d", "7d", "30d")


def require_asset(asset: str) -> str:
    normalized = asset.upper()
    if normalized not in SUPPORTED_ASSETS:
        raise ValueError(f"Unsupported asset: {asset}. Supported assets: BTC, ETH, WLD")
    return normalized


def parse_datetime(value: str | None = None) -> datetime:
    if not value:
        return datetime.now().astimezone()
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def to_iso(dt: datetime) -> str:
    return dt.astimezone().isoformat(timespec="seconds")


def optional_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    return float(value)


def pct_change(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return round((end - start) / start * 100, 4)


@dataclass
class Snapshot:
    timestamp: str
    asset: str
    price: float
    change_24h: float | None = None
    volume_24h: float | None = None
    oi: float | None = None
    oi_change_rate: float | None = None
    funding_rate: float | None = None
    liquidation_total: float | None = None
    long_liquidation: float | None = None
    short_liquidation: float | None = None
    long_short_ratio: float | None = None
    cvd: float | None = None
    heatmap: str = ""
    spot_volume: float | None = None
    futures_volume: float | None = None
    note: str = ""

    @classmethod
    def from_args(cls, **kwargs: Any) -> "Snapshot":
        kwargs["asset"] = require_asset(kwargs["asset"])
        kwargs["timestamp"] = to_iso(parse_datetime(kwargs.get("timestamp")))
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PricePoint:
    timestamp: str
    asset: str
    price: float
    source: str = "manual"
    note: str = ""

    @classmethod
    def from_args(cls, **kwargs: Any) -> "PricePoint":
        kwargs["asset"] = require_asset(kwargs["asset"])
        kwargs["timestamp"] = to_iso(parse_datetime(kwargs.get("timestamp")))
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    event_id: str
    asset: str
    event_time: str
    event_type: str
    title: str
    price: float
    description: str = ""
    tags: list[str] = field(default_factory=list)
    source: str = "manual"
    related_assets: list[str] = field(default_factory=list)
    outcome: dict[str, Any] = field(default_factory=dict)
    conclusion: str = "未知"
    created_at: str = field(default_factory=lambda: to_iso(parse_datetime(None)))
    updated_at: str = field(default_factory=lambda: to_iso(parse_datetime(None)))

    @classmethod
    def from_args(cls, **kwargs: Any) -> "Event":
        asset = require_asset(kwargs["asset"])
        event_time = parse_datetime(kwargs["event_time"])
        event_id = kwargs.get("event_id") or build_event_id(asset, event_time)
        tags = kwargs.get("tags") or ["未知"]
        related_assets = [item.upper() for item in kwargs.get("related_assets", [])]
        return cls(
            event_id=event_id,
            asset=asset,
            event_time=to_iso(event_time),
            event_type=kwargs["event_type"],
            title=kwargs["title"],
            price=float(kwargs["price"]),
            description=kwargs.get("description", ""),
            tags=tags,
            source=kwargs.get("source", "manual"),
            related_assets=related_assets,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_event_id(asset: str, event_time: datetime) -> str:
    return f"EVT-{event_time.strftime('%Y%m%d-%H%M%S')}-{asset.upper()}"
