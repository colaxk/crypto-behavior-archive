from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from src.models import parse_datetime, pct_change, to_iso

ASSETS = ("BTC", "ETH", "WLD")
SCORE_KEYS = (
    "valuation",
    "trend",
    "whale_behavior",
    "capital_quality",
    "leverage_health",
    "retail_sentiment",
    "tokenomics",
    "composite",
)

SCORE_LABELS = {
    "valuation": "估值评分",
    "trend": "趋势评分",
    "whale_behavior": "主力行为评分",
    "capital_quality": "资金质量评分",
    "leverage_health": "杠杆健康评分",
    "retail_sentiment": "散户情绪评分",
    "tokenomics": "Tokenomics评分",
    "composite": "综合评分",
}


def build_behavior_archive(
    snapshots: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = normalize_snapshots(snapshots)
    by_asset = {
        asset: sorted(
            [row for row in rows if row.get("asset") == asset],
            key=lambda row: row.get("timestamp") or "",
        )
        for asset in ASSETS
    }
    price_ranges = build_price_ranges(by_asset)
    analyses: list[dict[str, Any]] = []
    previous_by_asset: dict[str, dict[str, Any] | None] = {asset: None for asset in ASSETS}

    for row in sorted(rows, key=lambda item: item.get("timestamp") or ""):
        asset = row.get("asset")
        if asset not in ASSETS:
            continue
        previous = previous_by_asset.get(asset)
        context = latest_context_by_asset(by_asset, row.get("timestamp"))
        analysis = analyze_snapshot(row, previous, context, price_ranges.get(asset, {}))
        analyses.append(analysis)
        previous_by_asset[asset] = row

    by_date: dict[str, Any] = {}
    for analysis in analyses:
        date_key = day(analysis.get("timestamp"))
        if not date_key:
            continue
        bucket = by_date.setdefault(date_key, {"date": date_key, "assets": {}})
        asset = analysis["asset"]
        current = bucket["assets"].get(asset)
        if not current or str(analysis.get("timestamp", "")) >= str(current.get("timestamp", "")):
            bucket["assets"][asset] = analysis

    for date_key, bucket in by_date.items():
        bucket["conclusion"] = build_daily_conclusion(bucket["assets"], date_key)

    latest_date = max(by_date.keys(), default=None)
    latest = by_date.get(latest_date, {"assets": {}, "conclusion": {}}) if latest_date else {}

    return {
        "generated_at": to_iso(datetime.now().astimezone()),
        "latest_date": latest_date,
        "score_labels": SCORE_LABELS,
        "latest": latest,
        "by_date": dict(sorted(by_date.items())),
        "history": build_score_history(analyses),
        "validations": build_historical_validation(events),
    }


def analyze_snapshot(
    row: dict[str, Any],
    previous: dict[str, Any] | None,
    context: dict[str, dict[str, Any] | None],
    price_range: dict[str, float],
) -> dict[str, Any]:
    asset = str(row.get("asset") or "").upper()
    change_24h = num(row.get("change_24h"))
    price = num(row.get("price"))
    previous_price = num(previous.get("price")) if previous else None
    price_delta = pct_change(previous_price, price) if previous_price and price is not None else None
    oi_delta = first_number(row.get("oi_change_rate"), pct_delta(previous, row, "oi"))
    volume_delta = pct_delta(previous, row, "volume_24h")
    futures_volume_delta = pct_delta(previous, row, "futures_volume")
    cvd = num(row.get("cvd"))
    previous_cvd = num(previous.get("cvd")) if previous else None
    cvd_delta = cvd - previous_cvd if cvd is not None and previous_cvd is not None else None
    funding = num(row.get("funding_rate"))
    previous_funding = num(previous.get("funding_rate")) if previous else None
    long_short_ratio = num(row.get("long_short_ratio"))
    liquidation_total = num(row.get("liquidation_total"))
    spot_volume = num(row.get("spot_volume"))
    futures_volume = num(row.get("futures_volume"))

    tags = build_tags(
        row=row,
        previous=previous,
        context=context,
        change_24h=change_24h,
        price_delta=price_delta,
        oi_delta=oi_delta,
        volume_delta=volume_delta,
        futures_volume_delta=futures_volume_delta,
        cvd_delta=cvd_delta,
        funding=funding,
        previous_funding=previous_funding,
        long_short_ratio=long_short_ratio,
    )
    scores = build_scores(
        asset=asset,
        price=price,
        price_range=price_range,
        change_24h=change_24h,
        price_delta=price_delta,
        oi_delta=oi_delta,
        volume_delta=volume_delta,
        cvd=cvd,
        cvd_delta=cvd_delta,
        funding=funding,
        long_short_ratio=long_short_ratio,
        liquidation_total=liquidation_total,
        spot_volume=spot_volume,
        futures_volume=futures_volume,
        tags=tags,
    )
    evidence = build_evidence(
        row=row,
        previous=previous,
        context=context,
        change_24h=change_24h,
        price_delta=price_delta,
        oi_delta=oi_delta,
        volume_delta=volume_delta,
        futures_volume_delta=futures_volume_delta,
        cvd_delta=cvd_delta,
        funding=funding,
        previous_funding=previous_funding,
        long_short_ratio=long_short_ratio,
        spot_volume=spot_volume,
        futures_volume=futures_volume,
        tags=tags,
    )
    phase = infer_phase(tags, scores)
    biggest_change = infer_biggest_change(row, previous, tags, scores, oi_delta, volume_delta, cvd_delta)
    summary = summarize_behavior(asset, phase, tags, scores)

    return {
        "asset": asset,
        "timestamp": row.get("timestamp"),
        "date": day(row.get("timestamp")),
        "phase": phase,
        "summary": summary,
        "biggest_change": biggest_change,
        "scores": scores,
        "score_stars": {key: score_to_stars(value) for key, value in scores.items()},
        "tags": tags,
        "evidence": evidence,
        "raw_refs": {
            "price": price,
            "change_24h": change_24h,
            "oi": num(row.get("oi")),
            "oi_delta": oi_delta,
            "funding_rate": funding,
            "volume_24h": num(row.get("volume_24h")),
            "cvd": cvd,
            "long_short_ratio": long_short_ratio,
        },
    }


def build_tags(
    row: dict[str, Any],
    previous: dict[str, Any] | None,
    context: dict[str, dict[str, Any] | None],
    change_24h: float | None,
    price_delta: float | None,
    oi_delta: float | None,
    volume_delta: float | None,
    futures_volume_delta: float | None,
    cvd_delta: float | None,
    funding: float | None,
    previous_funding: float | None,
    long_short_ratio: float | None,
) -> list[str]:
    tags: list[str] = []
    direction = first_number(change_24h, price_delta)

    if direction is not None:
        if direction >= 5:
            tags.append("趋势转强")
            if direction >= 8:
                tags.append("加速上涨")
        elif direction <= -5:
            tags.append("趋势转弱")
            if direction <= -8:
                tags.append("加速下跌")
        elif abs(direction) <= 2:
            tags.append("震荡")
        else:
            tags.append("趋势延续")

    if volume_delta is not None:
        if volume_delta >= 35 and direction is not None and direction > 1:
            tags.append("放量上涨")
        elif volume_delta >= 35 and direction is not None and direction < -1:
            tags.append("放量下跌")
        elif volume_delta <= -25:
            tags.append("成交衰减")
        elif volume_delta >= 60:
            tags.append("换手充分")

    if oi_delta is not None:
        tags.append("OI增加" if oi_delta > 3 else "OI减少" if oi_delta < -3 else "OI平稳")
        if oi_delta >= 12:
            tags.append("OI暴增")
        if oi_delta <= -12:
            tags.append("OI暴减")

    if funding is not None:
        if previous_funding is not None:
            if funding > previous_funding * 1.2 and abs(funding - previous_funding) >= 0.002:
                tags.append("Funding升高")
            elif funding < previous_funding * 0.8:
                tags.append("Funding降低")
        if funding >= 0.03:
            tags.append("多头过热")
        elif funding <= -0.01:
            tags.append("空头拥挤")

    if oi_delta is not None and funding is not None and direction is not None:
        if oi_delta > 5 and funding >= 0.01 and direction > 2:
            tags.append("合约推动")
        if oi_delta < -5 and abs(funding) < 0.015:
            tags.append("杠杆释放")

    if direction is not None and direction < 0:
        if (volume_delta is not None and volume_delta < 0) or (cvd_delta is not None and cvd_delta > 0):
            tags.append("空头衰减")
    if oi_delta is not None and oi_delta > 3 and direction is not None and direction <= 1:
        tags.append("资金试探")
    if oi_delta is not None and oi_delta > 3 and direction is not None and direction < 0:
        tags.append("吸筹观察")
    if oi_delta is not None and oi_delta > 5 and direction is not None and direction > 5 and funding and funding > 0.015:
        tags.append("诱多风险")

    if long_short_ratio is not None:
        if long_short_ratio >= 1.45:
            tags.append("散户偏多")
        elif long_short_ratio <= 0.8:
            tags.append("散户偏空")

    relative_tag = relative_strength_tag(row, context, direction)
    if relative_tag:
        tags.append(relative_tag)

    if futures_volume_delta is not None and futures_volume_delta >= 50:
        tags.append("合约成交放大")

    return dedupe(tags) or ["等待确认"]


def build_scores(
    asset: str,
    price: float | None,
    price_range: dict[str, float],
    change_24h: float | None,
    price_delta: float | None,
    oi_delta: float | None,
    volume_delta: float | None,
    cvd: float | None,
    cvd_delta: float | None,
    funding: float | None,
    long_short_ratio: float | None,
    liquidation_total: float | None,
    spot_volume: float | None,
    futures_volume: float | None,
    tags: list[str],
) -> dict[str, int]:
    low = price_range.get("low")
    high = price_range.get("high")
    if price is not None and low is not None and high is not None and high > low:
        percentile = (price - low) / (high - low)
        valuation = clamp(95 - percentile * 55)
    else:
        valuation = 55

    direction = first_number(change_24h, price_delta)
    trend = 50
    if direction is not None:
        trend += direction * 4
    if price_delta is not None:
        trend += price_delta * 2
    if "趋势转强" in tags:
        trend += 10
    if "趋势转弱" in tags:
        trend -= 10

    whale = 50
    if oi_delta is not None:
        whale += clamp(oi_delta * 1.2, -18, 18)
    if cvd is not None:
        whale += 8 if cvd > 0 else -8 if cvd < 0 else 0
    if cvd_delta is not None:
        whale += 8 if cvd_delta > 0 else -6
    if "吸筹观察" in tags or "资金试探" in tags:
        whale += 8
    if "诱多风险" in tags:
        whale -= 8

    capital = 50
    if spot_volume and futures_volume:
        spot_share = spot_volume / max(spot_volume + futures_volume, 1)
        capital += (spot_share - 0.35) * 45
    if cvd is not None:
        capital += 10 if cvd > 0 else -10
    if funding is not None and funding > 0.03:
        capital -= 12
    if "合约推动" in tags:
        capital -= 7

    leverage = 72
    if funding is not None:
        leverage -= min(abs(funding) * 650, 28)
    if oi_delta is not None and abs(oi_delta) > 10:
        leverage -= min((abs(oi_delta) - 10) * 1.2, 18)
    if liquidation_total:
        leverage -= 5
    if "杠杆释放" in tags:
        leverage += 8

    retail = 55
    if long_short_ratio is not None:
        retail += clamp((long_short_ratio - 1) * 42, -20, 20)
        if long_short_ratio > 1.45:
            retail -= 10
    if funding is not None and funding > 0.03:
        retail -= 10

    tokenomics = 52
    if asset == "WLD":
        tokenomics -= 8

    scores = {
        "valuation": clamp(valuation),
        "trend": clamp(trend),
        "whale_behavior": clamp(whale),
        "capital_quality": clamp(capital),
        "leverage_health": clamp(leverage),
        "retail_sentiment": clamp(retail),
        "tokenomics": clamp(tokenomics),
    }
    composite = (
        scores["valuation"] * 0.12
        + scores["trend"] * 0.18
        + scores["whale_behavior"] * 0.18
        + scores["capital_quality"] * 0.16
        + scores["leverage_health"] * 0.14
        + scores["retail_sentiment"] * 0.08
        + scores["tokenomics"] * 0.14
    )
    scores["composite"] = clamp(composite)
    return scores


def build_evidence(
    row: dict[str, Any],
    previous: dict[str, Any] | None,
    context: dict[str, dict[str, Any] | None],
    change_24h: float | None,
    price_delta: float | None,
    oi_delta: float | None,
    volume_delta: float | None,
    futures_volume_delta: float | None,
    cvd_delta: float | None,
    funding: float | None,
    previous_funding: float | None,
    long_short_ratio: float | None,
    spot_volume: float | None,
    futures_volume: float | None,
    tags: list[str],
) -> dict[str, list[str]]:
    evidence = {
        "trend": [],
        "whale_behavior": [],
        "capital_quality": [],
        "leverage": [],
        "retail": [],
        "tokenomics": [],
        "relative_strength": [],
    }
    evidence["trend"].append(metric_sentence("24h涨跌幅", change_24h, "%"))
    if price_delta is not None:
        evidence["trend"].append(metric_sentence("相对上一条快照价格变化", price_delta, "%"))
    else:
        evidence["trend"].append("缺少上一条同资产快照，趋势变化只能参考24h涨跌幅。")
    evidence["trend"].append(tag_sentence(tags, ("趋势转强", "趋势转弱", "震荡", "趋势延续", "加速上涨", "加速下跌")))

    if oi_delta is not None:
        evidence["whale_behavior"].append(metric_sentence("OI变化", oi_delta, "%"))
    else:
        evidence["whale_behavior"].append("OI变化率缺失，无法确认新增仓位是否持续进入。")
    if cvd_delta is not None:
        evidence["whale_behavior"].append(metric_sentence("CVD相对上一条快照变化", cvd_delta))
    elif row.get("cvd") not in (None, ""):
        evidence["whale_behavior"].append(metric_sentence("当前CVD", num(row.get("cvd"))))
    else:
        evidence["whale_behavior"].append("CVD缺失，主买/主卖强度需要继续补数。")
    evidence["whale_behavior"].append(
        tag_sentence(tags, ("OI增加", "OI减少", "OI暴增", "OI暴减", "吸筹观察", "资金试探", "诱多风险", "合约推动"))
    )

    evidence["capital_quality"].append(metric_sentence("24h成交量", num(row.get("volume_24h"))))
    if volume_delta is not None:
        evidence["capital_quality"].append(metric_sentence("成交量相对上一条快照变化", volume_delta, "%"))
    if spot_volume and futures_volume:
        share = spot_volume / max(spot_volume + futures_volume, 1) * 100
        evidence["capital_quality"].append(metric_sentence("现货成交占总成交估算", share, "%"))
    else:
        evidence["capital_quality"].append("现货/合约成交结构不完整，资金质量只能弱判断。")

    evidence["leverage"].append(metric_sentence("Funding Rate", funding, "%"))
    if funding is not None and previous_funding is not None:
        evidence["leverage"].append(metric_sentence("Funding相对上一条快照变化", funding - previous_funding, "pct"))
    evidence["leverage"].append(metric_sentence("强平总额", num(row.get("liquidation_total"))))
    if futures_volume_delta is not None:
        evidence["leverage"].append(metric_sentence("合约成交量相对上一条快照变化", futures_volume_delta, "%"))
    evidence["leverage"].append(tag_sentence(tags, ("OI增加", "OI减少", "Funding升高", "Funding降低", "多头过热", "杠杆释放")))

    evidence["retail"].append(metric_sentence("多空比", long_short_ratio))
    evidence["retail"].append(tag_sentence(tags, ("散户偏多", "散户偏空")))

    if row.get("asset") == "WLD":
        evidence["tokenomics"].append("WLD供应/解锁数据尚未接入，Tokenomics暂按中性偏谨慎处理。")
    else:
        evidence["tokenomics"].append("供应结构数据尚未接入，Tokenomics暂按中性处理。")

    rel = relative_strength_tag(row, context, first_number(change_24h, price_delta))
    if rel:
        evidence["relative_strength"].append(f"相对强弱标签：{rel}。")
    else:
        evidence["relative_strength"].append("缺少同日BTC/ETH参照或强弱差异不足，暂不输出相对强弱标签。")

    return {key: clean_evidence(value) for key, value in evidence.items()}


def build_daily_conclusion(assets: dict[str, Any], date_key: str) -> dict[str, Any]:
    ranked = sorted(
        assets.values(),
        key=lambda item: abs(item.get("scores", {}).get("composite", 50) - 50),
        reverse=True,
    )
    top = ranked[0] if ranked else None
    summaries = []
    for asset in ASSETS:
        analysis = assets.get(asset)
        if analysis:
            summaries.append(f"{asset}：{analysis['phase']}，{analysis['summary']}")
    biggest = top.get("biggest_change") if top else "暂无足够快照生成今日变化。"
    return {
        "date": date_key,
        "headline": biggest,
        "summary": "；".join(summaries) if summaries else "暂无行为画像。",
        "focus_asset": top.get("asset") if top else None,
    }


def build_score_history(analyses: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    history = {asset: [] for asset in ASSETS}
    latest_by_day: dict[tuple[str, str], dict[str, Any]] = {}
    for analysis in analyses:
        key = (analysis["asset"], analysis["date"])
        current = latest_by_day.get(key)
        if not current or str(analysis.get("timestamp", "")) >= str(current.get("timestamp", "")):
            latest_by_day[key] = analysis
    for (asset, date_key), analysis in sorted(latest_by_day.items()):
        item = {"date": date_key}
        item.update(analysis.get("scores", {}))
        history[asset].append(item)
    return history


def build_historical_validation(events: list[dict[str, Any]]) -> dict[str, Any]:
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "windows": defaultdict(list)})
    for event in events:
        tags = event.get("tags") or ["未知"]
        outcome = event.get("outcome") or {}
        for tag in tags:
            stats[tag]["count"] += 1
            for window, result in outcome.items():
                if isinstance(result, dict) and result.get("change_pct") is not None:
                    stats[tag]["windows"][window].append(float(result["change_pct"]))

    tag_stats = {}
    for tag, payload in stats.items():
        windows = {}
        for window, values in payload["windows"].items():
            if not values:
                continue
            wins = [value for value in values if value > 0]
            windows[window] = {
                "samples": len(values),
                "success_rate": round(len(wins) / len(values) * 100, 2),
                "avg_change_pct": round(sum(values) / len(values), 4),
                "max_drawdown_pct": round(min(values), 4),
                "max_gain_pct": round(max(values), 4),
            }
        tag_stats[tag] = {"count": payload["count"], "windows": windows}
    return {"tags": dict(sorted(tag_stats.items()))}


def normalize_snapshots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        item = dict(row)
        asset = str(item.get("asset") or "").upper()
        if asset not in ASSETS or not item.get("timestamp"):
            continue
        item["asset"] = asset
        for key in (
            "price",
            "change_24h",
            "volume_24h",
            "oi",
            "oi_change_rate",
            "funding_rate",
            "liquidation_total",
            "long_liquidation",
            "short_liquidation",
            "long_short_ratio",
            "cvd",
            "spot_volume",
            "futures_volume",
        ):
            item[key] = num(item.get(key))
        normalized.append(item)
    return sorted(normalized, key=lambda item: item.get("timestamp") or "")


def build_price_ranges(by_asset: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, float]]:
    ranges = {}
    for asset, rows in by_asset.items():
        prices = [row["price"] for row in rows if row.get("price") is not None]
        if prices:
            ranges[asset] = {"low": min(prices), "high": max(prices)}
    return ranges


def latest_context_by_asset(
    by_asset: dict[str, list[dict[str, Any]]],
    timestamp: str | None,
) -> dict[str, dict[str, Any] | None]:
    context = {}
    if not timestamp:
        return {asset: None for asset in ASSETS}
    for asset, rows in by_asset.items():
        candidates = [row for row in rows if str(row.get("timestamp") or "") <= timestamp]
        context[asset] = candidates[-1] if candidates else None
    return context


def relative_strength_tag(
    row: dict[str, Any],
    context: dict[str, dict[str, Any] | None],
    direction: float | None,
) -> str | None:
    asset = row.get("asset")
    if direction is None or asset == "BTC":
        return None
    btc = context.get("BTC") or {}
    btc_change = num(btc.get("change_24h"))
    if btc_change is None:
        return None
    diff = direction - btc_change
    if asset == "ETH":
        if diff >= 3:
            return "ETH相对强势"
        if diff <= -3:
            return "ETH相对弱势"
    if asset == "WLD":
        if diff >= 4:
            return "AI板块强于BTC"
        if diff <= -4:
            return "AI板块弱于BTC"
    return None


def infer_phase(tags: list[str], scores: dict[str, int]) -> str:
    if "多头过热" in tags or "诱多风险" in tags:
        return "多头过热"
    if scores["trend"] >= 68 and scores["leverage_health"] >= 48:
        return "趋势延续"
    if scores["trend"] <= 38 and "空头衰减" not in tags:
        return "下降趋势"
    if "吸筹观察" in tags or "资金试探" in tags:
        return "吸筹观察"
    if "空头衰减" in tags:
        return "等待确认"
    if "震荡" in tags:
        return "震荡"
    return "等待确认"


def infer_biggest_change(
    row: dict[str, Any],
    previous: dict[str, Any] | None,
    tags: list[str],
    scores: dict[str, int],
    oi_delta: float | None,
    volume_delta: float | None,
    cvd_delta: float | None,
) -> str:
    asset = row.get("asset")
    if not previous:
        return f"{asset} 建立第一条行为基准，后续将用于比较趋势、OI、Funding和成交结构。"
    candidates = []
    if oi_delta is not None:
        candidates.append((abs(oi_delta), f"{asset} OI变化 {fmt(oi_delta, '%')}，新增仓位状态发生变化。"))
    if volume_delta is not None:
        candidates.append((abs(volume_delta), f"{asset} 成交量变化 {fmt(volume_delta, '%')}，换手强度出现变化。"))
    if cvd_delta is not None:
        candidates.append((min(abs(cvd_delta) / 1_000_000, 100), f"{asset} CVD变化 {fmt(cvd_delta)}，主动买卖方向需要关注。"))
    if tags:
        candidates.append((12, f"{asset} 新行为标签：{'、'.join(tags[:3])}。"))
    candidates.append((abs(scores.get("composite", 50) - 50), f"{asset} 综合行为评分为 {scores.get('composite')} /100。"))
    return max(candidates, key=lambda item: item[0])[1]


def summarize_behavior(asset: str, phase: str, tags: list[str], scores: dict[str, int]) -> str:
    positives = [tag for tag in tags if tag in {"空头衰减", "趋势转强", "放量上涨", "吸筹观察", "资金试探", "杠杆释放"}]
    risks = [tag for tag in tags if tag in {"趋势转弱", "加速下跌", "多头过热", "诱多风险", "AI板块弱于BTC", "ETH相对弱势"}]
    if positives and risks:
        return f"{'、'.join(positives[:2])}，但{'、'.join(risks[:2])}仍需验证。"
    if positives:
        return f"{'、'.join(positives[:3])}，综合评分 {scores['composite']} /100。"
    if risks:
        return f"{'、'.join(risks[:3])}，综合评分 {scores['composite']} /100。"
    return f"综合评分 {scores['composite']} /100。"


def metric_sentence(label: str, value: float | None, suffix: str = "") -> str:
    if value is None:
        return f"{label}缺失。"
    return f"{label}: {fmt(value, suffix)}。"


def tag_sentence(tags: list[str], selected: tuple[str, ...]) -> str:
    found = [tag for tag in tags if tag in selected]
    return f"行为标签: {'、'.join(found)}。" if found else "未触发该组明确行为标签。"


def clean_evidence(lines: list[str]) -> list[str]:
    return [line for line in lines if line and "None" not in line]


def pct_delta(previous: dict[str, Any] | None, row: dict[str, Any], key: str) -> float | None:
    if not previous:
        return None
    start = num(previous.get(key))
    end = num(row.get(key))
    if start in (None, 0) or end is None:
        return None
    return pct_change(start, end)


def first_number(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None


def num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clamp(value: float, low: float = 0, high: float = 100) -> int:
    return int(round(max(low, min(high, value))))


def fmt(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "-"
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B{suffix}"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M{suffix}"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.2f}K{suffix}"
    return f"{value:.4g}{suffix}"


def score_to_stars(score: int) -> str:
    filled = max(1, min(5, round(score / 20)))
    return "★" * filled + "☆" * (5 - filled)


def day(value: str | None) -> str:
    if not value:
        return ""
    try:
        return parse_datetime(value).date().isoformat()
    except ValueError:
        return str(value)[:10]


def dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
