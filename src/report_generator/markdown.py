from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from src.analyzers.behavior import build_behavior_archive
from src.models import parse_datetime
from src.storage import REPORTS_DIR, latest_snapshot, load_events, load_snapshots


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
    behavior = build_behavior_archive(load_snapshots(), [event.to_dict() for event in load_events()])
    behavior_day = behavior.get("by_date", {}).get(report_date.isoformat()) or behavior.get("latest", {})
    path = output_dir / f"{report_date.isoformat()}_daily_report.md"
    path.write_text(
        "\n".join(
            [
                f"# Crypto Behavior Archive 日报 - {report_date.isoformat()}",
                "",
                "## Behavior Conclusion（行为结论）",
                behavior_conclusion_block(behavior_day),
                "",
                "## Behavior Summary（行为画像）",
                behavior_summary_block(behavior_day),
                "",
                "## Behavior Confidence（结论可信度）",
                behavior_confidence_block(behavior_day),
                "",
                "## Behavior Score（行为评分）",
                behavior_score_block(behavior_day),
                "",
                "## Behavior Evidence（行为证据）",
                behavior_evidence_block(behavior_day),
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
                "## 风险提示",
                "- 本系统仅用于记录和复盘，不构成交易建议。",
                "- 数据可能来自手动录入，请核对关键字段。",
                "",
                "## 待验证假设",
                "- 事件后 1h / 4h / 24h / 7d / 30d 表现是否支持当前行为标签。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def behavior_conclusion_block(day_payload: dict[str, Any]) -> str:
    conclusion = day_payload.get("conclusion") or {}
    headline = conclusion.get("headline") or "暂无足够数据生成今日最大变化。"
    summary = conclusion.get("summary") or "暂无行为画像。"
    return "\n".join(
        [
            f"- 今天最大的变化: {headline}",
            f"- 结构摘要: {summary}",
            f"- 聚焦资产: {conclusion.get('focus_asset') or '-'}",
        ]
    )


def behavior_summary_block(day_payload: dict[str, Any]) -> str:
    assets = day_payload.get("assets") or {}
    if not assets:
        return "- 暂无行为画像。"
    lines = ["| 标的 | 阶段 | 一句话 | 标签 |", "| --- | --- | --- | --- |"]
    for asset in ("BTC", "ETH", "WLD"):
        item = assets.get(asset)
        if not item:
            continue
        lines.append(
            f"| {asset} | {item.get('phase', '-')} | {item.get('summary', '-')} | {', '.join(item.get('tags', []))} |"
        )
    return "\n".join(lines)


def behavior_confidence_block(day_payload: dict[str, Any]) -> str:
    assets = day_payload.get("assets") or {}
    if not assets:
        return "- 暂无可信度判断。"
    blocks = []
    for asset in ("BTC", "ETH", "WLD"):
        item = assets.get(asset)
        if not item:
            continue
        confidence = item.get("confidence") or {}
        support = confidence.get("support") or []
        against = confidence.get("against") or []
        lines = [
            f"### {asset}: {behavior_title(item)}",
            f"- 可信度: {confidence.get('level', '-')}",
            "- 原因:",
        ]
        if support:
            lines.extend(f"  - 支持: {line}" for line in support)
        else:
            lines.append("  - 支持: 暂无足够支持证据。")
        if against:
            lines.extend(f"  - 反对: {line}" for line in against)
        else:
            lines.append("  - 反对: 暂无明显反对证据。")
        lines.append(f"- 结论: {confidence.get('conclusion', item.get('phase', '-'))}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def behavior_title(item: dict[str, Any]) -> str:
    tags = item.get("tags") or []
    priority = [
        "杠杆释放",
        "空头衰减",
        "吸筹观察",
        "资金试探",
        "趋势转强",
        "趋势转弱",
        "多头过热",
        "诱多风险",
        "OI暴增",
        "OI暴减",
        "成交衰减",
        "放量上涨",
        "放量下跌",
    ]
    selected = [tag for tag in priority if tag in tags]
    if not selected:
        selected = tags[:3]
    return "、".join(selected[:3]) or item.get("phase", "-")


def behavior_score_block(day_payload: dict[str, Any]) -> str:
    assets = day_payload.get("assets") or {}
    if not assets:
        return "- 暂无行为评分。"
    labels = [
        ("估值", "valuation"),
        ("趋势", "trend"),
        ("主力", "whale_behavior"),
        ("资金", "capital_quality"),
        ("杠杆", "leverage_health"),
        ("散户", "retail_sentiment"),
        ("供应", "tokenomics"),
        ("综合", "composite"),
    ]
    lines = ["| 标的 | " + " | ".join(label for label, _ in labels) + " |"]
    lines.append("| --- | " + " | ".join("---" for _ in labels) + " |")
    for asset in ("BTC", "ETH", "WLD"):
        item = assets.get(asset)
        if not item:
            continue
        scores = item.get("scores", {})
        stars = item.get("score_stars", {})
        values = [f"{scores.get(key, '-')}/100 {stars.get(key, '')}" for _, key in labels]
        lines.append(f"| {asset} | " + " | ".join(values) + " |")
    return "\n".join(lines)


def behavior_evidence_block(day_payload: dict[str, Any]) -> str:
    assets = day_payload.get("assets") or {}
    if not assets:
        return "- 暂无行为证据。"
    blocks = []
    for asset in ("BTC", "ETH", "WLD"):
        item = assets.get(asset)
        if not item:
            continue
        evidence = item.get("evidence", {})
        lines = [f"### {asset}", f"- 当前阶段: {item.get('phase', '-')}", f"- 今日变化: {item.get('biggest_change', '-')}"]
        for label, key in [
            ("趋势", "trend"),
            ("主力行为", "whale_behavior"),
            ("资金质量", "capital_quality"),
            ("杠杆", "leverage"),
            ("散户", "retail"),
            ("供应结构", "tokenomics"),
            ("相对强弱", "relative_strength"),
        ]:
            details = "；".join(evidence.get(key, []))
            lines.append(f"- {label}: {details or '-'}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


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
