from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from src.models import parse_datetime
from src.storage import REPORTS_DIR, latest_snapshot, load_events


def generate_daily_report(report_date: date, output_dir: Path = REPORTS_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    events = [
        event
        for event in load_events()
        if parse_datetime(event.event_time).date() == report_date
    ]

    btc = latest_snapshot("BTC")
    eth = latest_snapshot("ETH")
    wld = latest_snapshot("WLD")
    path = output_dir / f"{report_date.isoformat()}_daily_report.md"
    path.write_text(
        "\n".join(
            [
                f"# Crypto Behavior Archive 日报 - {report_date.isoformat()}",
                "",
                "## 今日市场概况",
                "- 本报告由本地 MVP 自动生成。",
                "- 请结合手动备注、截图、新闻事件继续补充判断。",
                "",
                "## BTC状态",
                snapshot_block(btc),
                "",
                "## ETH状态",
                snapshot_block(eth),
                "",
                "## WLD状态",
                snapshot_block(wld),
                "",
                "## 异常数据",
                event_table(events),
                "",
                "## 关键事件",
                event_details(events),
                "",
                "## 技术结构",
                "- 待人工补充：趋势、关键均线、前高/前低、支撑压力。",
                "",
                "## OI / Funding / 爆仓分析",
                "- 待人工补充：OI变化、Funding冷热、爆仓方向、合约拥挤度。",
                "",
                "## 当前行为判断",
                "- 待人工补充：有效信号 / 假突破 / 洗盘 / 出货 / 未知。",
                "",
                "## 风险提示",
                "- 本系统仅用于记录和复盘，不构成交易建议。",
                "- 数据可能来自手动录入，请核对关键字段。",
                "",
                "## 待验证假设",
                "- 事件后 1h / 4h / 24h / 7d 表现是否支持当前行为标签。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def snapshot_block(row: dict[str, Any] | None) -> str:
    if not row:
        return "- 暂无快照。"
    fields = [
        ("时间", "timestamp"),
        ("价格", "price"),
        ("24h涨跌幅", "change_24h"),
        ("24h成交量", "volume_24h"),
        ("OI", "oi"),
        ("OI变化率", "oi_change_rate"),
        ("Funding Rate", "funding_rate"),
        ("爆仓总额", "liquidation_total"),
        ("多单爆仓", "long_liquidation"),
        ("空单爆仓", "short_liquidation"),
        ("多空比", "long_short_ratio"),
        ("CVD", "cvd"),
        ("Heatmap", "heatmap"),
        ("现货成交量", "spot_volume"),
        ("合约成交量", "futures_volume"),
        ("备注", "note"),
    ]
    return "\n".join(f"- {label}: {row.get(key) or '-'}" for label, key in fields)


def event_table(events: list[Any]) -> str:
    if not events:
        return "- 暂无异常事件。"
    lines = ["| 时间 | 标的 | 类型 | 标题 | 标签 |", "| --- | --- | --- | --- | --- |"]
    for event in events:
        lines.append(
            f"| {event.event_time} | {event.asset} | {event.event_type} | {event.title} | {', '.join(event.tags)} |"
        )
    return "\n".join(lines)


def event_details(events: list[Any]) -> str:
    if not events:
        return "- 暂无关键事件。"
    blocks = []
    for event in events:
        outcome_lines = []
        for window, result in (event.outcome or {}).items():
            if isinstance(result, dict) and "change_pct" in result:
                outcome_lines.append(f"  - {window}: {result['change_pct']}%")
            else:
                outcome_lines.append(f"  - {window}: 缺少价格点")
        blocks.append(
            "\n".join(
                [
                    f"### {event.title}",
                    f"- ID: {event.event_id}",
                    f"- 标的: {event.asset}",
                    f"- 时间: {event.event_time}",
                    f"- 价格: {event.price}",
                    f"- 标签: {', '.join(event.tags)}",
                    f"- 描述: {event.description or '-'}",
                    f"- 结论: {event.conclusion}",
                    "- 后续表现:",
                    "\n".join(outcome_lines) if outcome_lines else "  - 暂未计算",
                ]
            )
        )
    return "\n\n".join(blocks)
