from __future__ import annotations

import html
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.models import parse_datetime
from src.storage import REPORTS_DIR, ROOT, load_events, load_prices, load_snapshots

DOCS_DIR = ROOT / "docs"
DASHBOARD_PATH = DOCS_DIR / "index.html"
ASSETS = ("BTC", "ETH", "WLD")
LIVE_SYMBOLS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "WLD": "WLDUSDT",
}
CHART_COLORS = {
    "BTC": "#2458d3",
    "ETH": "#7c3aed",
    "WLD": "#12805c",
}


def generate_dashboard(output_path: Path = DASHBOARD_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    snapshots = load_snapshots()
    prices = load_prices()
    events = load_events()

    latest_snapshots = {asset: latest_by_time([row for row in snapshots if row.get("asset") == asset]) for asset in ASSETS}
    latest_time = max(
        [parse_datetime(row["timestamp"]) for row in snapshots if row.get("timestamp")] or [datetime.now().astimezone()]
    )
    recent_events = sorted(events, key=lambda event: parse_datetime(event.event_time), reverse=True)[:8]
    report = latest_report()
    price_summaries = {asset: price_summary(asset, prices) for asset in ASSETS}
    gpt_context = build_gpt_context(latest_snapshots, price_summaries, recent_events, report)

    output_path.write_text(
        build_html(
            latest_time=latest_time,
            snapshots=latest_snapshots,
            price_summaries=price_summaries,
            events=recent_events,
            report=report,
            gpt_context=gpt_context,
        ),
        encoding="utf-8",
    )
    return output_path


def latest_by_time(rows: list[dict[str, str]]) -> dict[str, str] | None:
    valid = [row for row in rows if row.get("timestamp")]
    if not valid:
        return None
    return sorted(valid, key=lambda row: parse_datetime(row["timestamp"]), reverse=True)[0]


def price_summary(asset: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    asset_rows = [
        row
        for row in rows
        if row.get("asset") == asset and row.get("timestamp") and row.get("price")
    ]
    asset_rows = sorted(asset_rows, key=lambda row: parse_datetime(row["timestamp"]))
    if not asset_rows:
        return {"asset": asset, "points": [], "change_7d": None, "latest_price": None}

    latest = asset_rows[-1]
    latest_time = parse_datetime(latest["timestamp"])
    cutoff = latest_time - timedelta(days=7)
    window = [row for row in asset_rows if parse_datetime(row["timestamp"]) >= cutoff]
    first = window[0] if window else asset_rows[0]
    change_7d = pct(float(first["price"]), float(latest["price"]))
    return {
        "asset": asset,
        "points": [
            {
                "timestamp": row["timestamp"],
                "price": float(row["price"]),
            }
            for row in window[-60:]
        ],
        "change_7d": change_7d,
        "latest_price": float(latest["price"]),
        "latest_time": latest["timestamp"],
    }


def latest_report() -> dict[str, str] | None:
    reports = sorted(REPORTS_DIR.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not reports:
        return None
    path = reports[0]
    text = path.read_text(encoding="utf-8")
    return {
        "title": first_markdown_title(text) or path.stem,
        "path": str(path.relative_to(ROOT)),
        "summary": summarize_markdown(text),
    }


def first_markdown_title(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def summarize_markdown(text: str, max_lines: int = 16) -> str:
    lines = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if clean.startswith("#"):
            continue
        lines.append(clean)
        if len(lines) >= max_lines:
            break
    return "\n".join(lines)


def build_gpt_context(
    snapshots: dict[str, dict[str, str] | None],
    price_summaries: dict[str, dict[str, Any]],
    events: list[Any],
    report: dict[str, str] | None,
) -> str:
    grouped_events = {asset: [event for event in events if event.asset == asset][:3] for asset in ASSETS}
    sections = []
    for asset in ASSETS:
        row = snapshots.get(asset) or {}
        summary = price_summaries.get(asset) or {}
        asset_events = grouped_events[asset]
        section = [
            asset,
            "",
            f"价格: {money(row.get('price'))} / 24h {fmt_pct(row.get('change_24h'))} / 7d {fmt_pct(summary.get('change_7d'))}",
            f"OI: {compact_number(row.get('oi'))}",
            f"Funding: {fmt_pct(row.get('funding_rate'))}",
        ]
        if asset != "WLD":
            section.extend(
                [
                    f"Liquidation: {compact_number(row.get('liquidation_total'))}",
                    f"CVD: {compact_number(row.get('cvd'))}",
                    f"Heatmap: {row.get('heatmap') or '未接入'}",
                    f"状态: {row.get('note') or '待判断'}",
                ]
            )
        else:
            section.extend(
                [
                    f"Liquidation: {compact_number(row.get('liquidation_total'))}",
                    f"CVD: {compact_number(row.get('cvd'))}",
                    f"Heatmap: {row.get('heatmap') or '未接入'}",
                    "异常事件:",
                ]
            )
            if asset_events:
                section.extend(
                    [
                        f"- {event.title} | 标签: {', '.join(event.tags)} | 结果: {compact_outcome(event.outcome)}"
                        for event in asset_events
                    ]
                )
            else:
                section.append("- 暂无")
        sections.append("\n".join(section))

    lines = ["\n\n---\n\n".join(sections)]

    lines.extend(
        [
            "",
            "---",
            "",
            "当前假设",
            "- BTC/ETH/WLD 当前结构需要结合 OI、Funding、成交量、异常事件和 BTC 大盘环境判断。",
            f"- BTC 近期事件: {event_titles(grouped_events['BTC'])}",
            f"- ETH 近期事件: {event_titles(grouped_events['ETH'])}",
            f"- WLD 近期事件: {event_titles(grouped_events['WLD'])}",
            "",
            "已验证",
            f"- 最新档案时间: {latest_context_time(snapshots)}",
            f"- 已记录事件后表现: {verified_outcomes(events)}",
            "",
            "待验证",
            "- CVD 目前使用 Binance Futures taker buy/sell 近似值，需要后续接更精细订单流。",
            "- Heatmap / 清算地图仍需接入稳定数据源。",
            "- CoinGlass 全市场 Funding、爆仓、多空比需要更稳定接口；当前优先使用 Binance Futures 公共数据补齐。",
            "- 观察异常事件后 1h / 4h / 24h / 3d / 7d 表现是否支持当前标签。",
            "",
            "请基于以上上下文分析 BTC/ETH/WLD 的资金行为、异常事件、相对强弱、风险和下一步待验证假设。不要给自动交易指令。",
        ]
    )
    if report:
        lines.extend(["", "最近报告摘要", report["summary"]])
    return "\n".join(lines)


def event_titles(events: list[Any]) -> str:
    if not events:
        return "暂无"
    return "；".join(event.title for event in events[:3])


def verified_outcomes(events: list[Any]) -> str:
    verified = [event for event in events if compact_outcome(event.outcome) != "-"]
    if not verified:
        return "暂无"
    return "；".join(f"{event.asset} {event.title}: {compact_outcome(event.outcome)}" for event in verified[:3])


def latest_context_time(snapshots: dict[str, dict[str, str] | None]) -> str:
    times = [row.get("timestamp") for row in snapshots.values() if row and row.get("timestamp")]
    if not times:
        return "-"
    return max(times, key=lambda value: parse_datetime(value))


def compact_outcome(outcome: dict[str, Any]) -> str:
    parts = []
    for window in ("1h", "4h", "24h", "3d", "7d"):
        result = outcome.get(window) if isinstance(outcome, dict) else None
        if isinstance(result, dict) and "change_pct" in result:
            parts.append(f"{window}:{result['change_pct']}%")
    return " ".join(parts) if parts else "-"


def build_html(
    latest_time: datetime,
    snapshots: dict[str, dict[str, str] | None],
    price_summaries: dict[str, dict[str, Any]],
    events: list[Any],
    report: dict[str, str] | None,
    gpt_context: str,
) -> str:
    chart_data = json.dumps({asset: price_summaries[asset]["points"] for asset in ASSETS}, ensure_ascii=False)
    chart_colors = json.dumps(CHART_COLORS, ensure_ascii=False)
    live_symbols = json.dumps(
        {
            asset: {
                "symbol": LIVE_SYMBOLS[asset],
                "priceId": f"live{asset}",
                "changeId": f"live{asset}Change",
                "dotId": f"liveDot{asset}",
            }
            for asset in ASSETS
        },
        ensure_ascii=False,
    )
    snapshot_data = json.dumps(
        {
            asset: {
                "price": value_of(snapshots.get(asset), "price"),
                "change24h": value_of(snapshots.get(asset), "change_24h"),
                "timestamp": value_of(snapshots.get(asset), "timestamp"),
            }
            for asset in ASSETS
        },
        ensure_ascii=False,
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Crypto Behavior Archive</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #15171a;
      --muted: #69707a;
      --line: #e4e7eb;
      --green: #12805c;
      --red: #c23b3b;
      --blue: #2458d3;
      --soft-blue: #eef3ff;
      --shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      padding: 22px 16px 12px;
      max-width: 1080px;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0;
      font-size: 26px;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 18px;
    }}
    h3 {{
      margin: 0 0 8px;
      font-size: 16px;
    }}
    .subtitle {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }}
    main {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 8px 16px 36px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .single {{
      margin-top: 14px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 14px;
    }}
    .market {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .live-bar {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}
    .live-dot {{
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #9aa3af;
      margin-right: 6px;
    }}
    .live-dot.ok {{ background: var(--green); }}
    .live-dot.bad {{ background: var(--red); }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfe;
      min-width: 0;
    }}
    .label {{
      color: var(--muted);
      font-size: 12px;
    }}
    .value {{
      margin-top: 2px;
      font-size: 18px;
      font-weight: 700;
      overflow-wrap: anywhere;
    }}
    .positive {{ color: var(--green); }}
    .negative {{ color: var(--red); }}
    .asset-title {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 10px;
    }}
    .asset-title strong {{ font-size: 20px; }}
    .pill {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--soft-blue);
      color: var(--blue);
      font-size: 12px;
      font-weight: 600;
    }}
    .kv {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }}
    .note {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }}
    .sparkline {{
      width: 100%;
      height: 74px;
      margin-top: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
    }}
    .event {{
      padding: 10px 0;
      border-top: 1px solid var(--line);
    }}
    .event:first-of-type {{ border-top: 0; padding-top: 0; }}
    .event-meta {{
      color: var(--muted);
      font-size: 12px;
    }}
    .tags {{
      margin-top: 5px;
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }}
    .tag {{
      padding: 2px 7px;
      border-radius: 999px;
      background: #f0f2f5;
      color: #3e4651;
      font-size: 12px;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      padding: 12px;
      background: #0f172a;
      color: #e5e7eb;
      border-radius: 8px;
      max-height: 360px;
      overflow: auto;
      font-size: 13px;
    }}
    button {{
      appearance: none;
      border: 0;
      border-radius: 8px;
      background: var(--blue);
      color: #fff;
      font-weight: 700;
      padding: 10px 12px;
      cursor: pointer;
    }}
    .section-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 10px;
    }}
    .report-summary {{
      color: #31363d;
      white-space: pre-wrap;
    }}
    footer {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 0 16px 24px;
      color: var(--muted);
      font-size: 12px;
    }}
    @media (max-width: 760px) {{
      header {{ padding-top: 18px; }}
      h1 {{ font-size: 22px; }}
      main {{ padding-left: 12px; padding-right: 12px; }}
      .grid {{ grid-template-columns: 1fr; gap: 12px; }}
      .market {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .live-bar {{ grid-template-columns: 1fr; }}
      .kv {{ grid-template-columns: 1fr 1fr; }}
      .card {{ padding: 12px; }}
      .value {{ font-size: 16px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Crypto Behavior Archive</h1>
    <div class="subtitle">静态行为档案仪表板 · 最新数据时间 {escape(latest_time.isoformat(timespec="seconds"))}</div>
  </header>
  <main>
    <section class="card">
      <h2>今日市场总览</h2>
      <div class="market">
        {overview_metrics(snapshots, price_summaries)}
      </div>
      <div class="live-bar">
        {live_price_cards(snapshots)}
      </div>
      <div class="note" id="liveUpdated">先显示档案快照，正在尝试读取实时价格；若 Binance 访问失败，会自动保留快照价。</div>
    </section>

    <section class="grid single">
      {asset_cards(snapshots, price_summaries)}
    </section>

    <section class="grid single">
      <div class="card">
        <h2>OI / Funding / 爆仓 / 成交量</h2>
        {market_structure_table(snapshots)}
      </div>
      <div class="card">
        <h2>最近7天价格变化</h2>
        {price_change_block(price_summaries)}
        <canvas class="sparkline" id="priceChart" width="680" height="148" aria-label="最近价格线"></canvas>
      </div>
    </section>

    <section class="grid single">
      <div class="card">
        <h2>最近异常事件</h2>
        {events_block(events)}
      </div>
      <div class="card">
        <h2>最近报告摘要</h2>
        {report_block(report)}
      </div>
    </section>

    <section class="card single">
      <div class="section-head">
        <h2>GPT Context</h2>
        <button type="button" id="copyContext">一键复制</button>
      </div>
      <pre id="gptContext">{escape(gpt_context)}</pre>
    </section>
  </main>
  <footer>
    本页面由本地 CSV / JSONL / Markdown 自动生成，仅用于研究复盘，不构成交易建议。
  </footer>
  <script>
    const chartData = {chart_data};
    const chartColors = {chart_colors};
    const snapshotData = {snapshot_data};
    const canvas = document.getElementById('priceChart');
    const ctx = canvas.getContext('2d');
    function drawLine(points, color) {{
      if (!points.length) return;
      const pad = 16;
      const values = points.map(p => Number(p.price));
      const min = Math.min(...values);
      const max = Math.max(...values);
      const span = max - min || 1;
      ctx.beginPath();
      points.forEach((point, index) => {{
        const x = pad + (canvas.width - pad * 2) * (index / Math.max(points.length - 1, 1));
        const y = canvas.height - pad - ((Number(point.price) - min) / span) * (canvas.height - pad * 2);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }});
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.stroke();
    }}
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    Object.entries(chartData).forEach(([asset, points]) => drawLine(points || [], chartColors[asset] || '#2458d3'));

    const liveBases = [
      'https://api.binance.com',
      'https://api1.binance.com',
      'https://api2.binance.com',
      'https://api3.binance.com',
      'https://data-api.binance.vision'
    ];
    const liveSymbols = {live_symbols};
    Object.keys(liveSymbols).forEach(asset => liveSymbols[asset].fallback = snapshotData[asset]);
    function formatLiveMoney(value) {{
      const number = Number(value);
      if (!Number.isFinite(number)) return '-';
      if (number >= 100) return '$' + number.toLocaleString(undefined, {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
      return '$' + number.toFixed(4);
    }}
    function formatLivePct(value) {{
      const number = Number(value);
      if (!Number.isFinite(number)) return '-';
      return (number > 0 ? '+' : '') + number.toFixed(2) + '%';
    }}
    async function fetchWithTimeout(url, timeoutMs) {{
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {{
        const response = await fetch(url, {{ cache: 'no-store', signal: controller.signal }});
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return await response.json();
      }} finally {{
        clearTimeout(timer);
      }}
    }}
    async function fetchBinanceTicker(symbol) {{
      let lastError;
      for (const base of liveBases) {{
        try {{
          return await fetchWithTimeout(base + '/api/v3/ticker/24hr?symbol=' + symbol, 6000);
        }} catch (error) {{
          lastError = error;
        }}
      }}
      throw lastError || new Error('No live endpoint available');
    }}
    function showFallback(cfg) {{
      const fallback = cfg.fallback || {{}};
      document.getElementById(cfg.priceId).innerText = formatLiveMoney(fallback.price);
      document.getElementById(cfg.changeId).innerText = '实时失败，使用档案快照 24h: ' + formatLivePct(fallback.change24h);
      document.getElementById(cfg.changeId).className = 'label';
      document.getElementById(cfg.dotId).className = 'live-dot bad';
    }}
    async function refreshLivePrices() {{
      let okCount = 0;
      await Promise.all(Object.entries(liveSymbols).map(async ([asset, cfg]) => {{
        const dot = document.getElementById(cfg.dotId);
        try {{
          const data = await fetchBinanceTicker(cfg.symbol);
          const change = Number(data.priceChangePercent);
          document.getElementById(cfg.priceId).innerText = formatLiveMoney(data.lastPrice);
          const changeNode = document.getElementById(cfg.changeId);
          changeNode.innerText = '24h: ' + formatLivePct(change);
          changeNode.className = 'label ' + (change > 0 ? 'positive' : change < 0 ? 'negative' : '');
          dot.className = 'live-dot ok';
          okCount += 1;
        }} catch (error) {{
          showFallback(cfg);
        }}
      }}));
      const now = new Date().toLocaleString();
      document.getElementById('liveUpdated').innerText = okCount
        ? '实时层更新时间：' + now + '。档案快照由 GitHub Actions 每小时沉淀一次。'
        : '实时层读取失败，当前显示档案快照。可能是手机网络无法访问 Binance；档案快照仍按 GitHub Actions 每小时更新。';
    }}
    refreshLivePrices();
    setInterval(refreshLivePrices, 60000);

    async function copyText(text) {{
      if (navigator.clipboard && window.isSecureContext) {{
        await navigator.clipboard.writeText(text);
        return true;
      }}
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'fixed';
      textarea.style.top = '-1000px';
      document.body.appendChild(textarea);
      textarea.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(textarea);
      return ok;
    }}
    document.getElementById('copyContext').addEventListener('click', async () => {{
      const text = document.getElementById('gptContext').innerText;
      const button = document.getElementById('copyContext');
      const old = button.innerText;
      try {{
        const ok = await copyText(text);
        button.innerText = ok ? '已复制' : '复制失败';
      }} catch (error) {{
        button.innerText = '复制失败';
      }}
      setTimeout(() => button.innerText = old, 1400);
    }});
  </script>
</body>
</html>
"""


def market_metric(label: str, value: str, raw_change: Any = None) -> str:
    return f"""
    <div class="metric">
      <div class="label">{escape(label)}</div>
      <div class="value {change_class(raw_change)}">{escape(value)}</div>
    </div>
    """


def overview_metrics(
    snapshots: dict[str, dict[str, str] | None],
    price_summaries: dict[str, dict[str, Any]],
) -> str:
    blocks = []
    for asset in ASSETS:
        blocks.append(market_metric(f"{asset} 价格", money(value_of(snapshots.get(asset), "price")), price_summaries[asset].get("change_7d")))
    for asset in ASSETS:
        blocks.append(market_metric(f"{asset} 24h", fmt_pct(value_of(snapshots.get(asset), "change_24h")), value_of(snapshots.get(asset), "change_24h")))
    return "\n".join(blocks)


def live_price_cards(snapshots: dict[str, dict[str, str] | None]) -> str:
    blocks = []
    for asset in ASSETS:
        blocks.append(
            f"""
            <div class="metric">
              <div class="label"><span class="live-dot" id="liveDot{asset}"></span>{asset} Binance 实时</div>
              <div class="value" id="live{asset}">{escape(money(value_of(snapshots.get(asset), "price")))}</div>
              <div class="label" id="live{asset}Change">档案快照 24h: {escape(fmt_pct(value_of(snapshots.get(asset), "change_24h")))}</div>
            </div>
            """
        )
    return "\n".join(blocks)


def asset_cards(
    snapshots: dict[str, dict[str, str] | None],
    price_summaries: dict[str, dict[str, Any]],
) -> str:
    return "\n".join(asset_card(asset, snapshots.get(asset), price_summaries[asset]) for asset in ASSETS)


def asset_card(asset: str, row: dict[str, str] | None, summary: dict[str, Any]) -> str:
    if not row:
        return f'<div class="card"><h2>{asset} 状态卡片</h2><p class="note">暂无数据。</p></div>'
    return f"""
    <div class="card">
      <div class="asset-title">
        <strong>{asset} 状态卡片</strong>
        <span class="pill">{escape(short_time(row.get("timestamp")))}</span>
      </div>
      <div class="kv">
        {metric("价格", money(row.get("price")))}
        {metric("24h涨跌", fmt_pct(row.get("change_24h")), row.get("change_24h"))}
        {metric("7天变化", fmt_pct(summary.get("change_7d")), summary.get("change_7d"))}
        {metric("24h成交量", compact_number(row.get("volume_24h")))}
        {metric("OI", compact_number(row.get("oi")))}
        {metric("Funding", fmt_pct(row.get("funding_rate")))}
        {metric("爆仓总额", compact_number(row.get("liquidation_total")))}
        {metric("多空比", fmt_plain(row.get("long_short_ratio")))}
        {metric("CVD", compact_number(row.get("cvd")))}
        {metric("Heatmap", fmt_plain(row.get("heatmap")))}
      </div>
      <div class="note">{escape(row.get("note") or "无备注")}</div>
    </div>
    """


def metric(label: str, value: str, raw_change: Any = None) -> str:
    return f"""
    <div class="metric">
      <div class="label">{escape(label)}</div>
      <div class="value {change_class(raw_change)}">{escape(value)}</div>
    </div>
    """


def market_structure_table(snapshots: dict[str, dict[str, str] | None]) -> str:
    rows = []
    for asset in ASSETS:
        row = snapshots.get(asset) or {}
        rows.append(
            f"""
            <div class="event">
              <h3>{asset}</h3>
              <div class="kv">
                {metric("OI", compact_number(row.get("oi")))}
                {metric("Funding", fmt_pct(row.get("funding_rate")))}
                {metric("爆仓总额", compact_number(row.get("liquidation_total")))}
                {metric("多单爆仓", compact_number(row.get("long_liquidation")))}
                {metric("空单爆仓", compact_number(row.get("short_liquidation")))}
                {metric("24h成交量", compact_number(row.get("volume_24h")))}
                {metric("合约成交量", compact_number(row.get("futures_volume")))}
                {metric("多空比", fmt_plain(row.get("long_short_ratio")))}
                {metric("CVD", compact_number(row.get("cvd")))}
              </div>
            </div>
            """
        )
    return "\n".join(rows)


def price_change_block(price_summaries: dict[str, dict[str, Any]]) -> str:
    return "\n".join(
        [
            f'<div class="metric"><div class="label">{asset} 最近7天</div>'
            f'<div class="value {change_class(price_summaries[asset].get("change_7d"))}">'
            f'{escape(fmt_pct(price_summaries[asset].get("change_7d")))}</div></div>'
            for asset in ASSETS
        ]
    )


def events_block(events: list[Any]) -> str:
    if not events:
        return '<p class="note">暂无异常事件。</p>'
    return "\n".join(
        [
            f"""
            <div class="event">
              <h3>{escape(event.title)}</h3>
              <div class="event-meta">{escape(event.event_time)} · {escape(event.asset)} · {escape(event.event_type)} · 结论：{escape(event.conclusion)}</div>
              <div class="tags">{''.join(f'<span class="tag">{escape(tag)}</span>' for tag in event.tags)}</div>
              <div class="note">{escape(event.description or compact_outcome(event.outcome))}</div>
            </div>
            """
            for event in events
        ]
    )


def report_block(report: dict[str, str] | None) -> str:
    if not report:
        return '<p class="note">暂无 Markdown 报告。</p>'
    return f"""
    <h3>{escape(report["title"])}</h3>
    <div class="event-meta">{escape(report["path"])}</div>
    <div class="report-summary">{escape(report["summary"])}</div>
    """


def value_of(row: dict[str, str] | None, key: str) -> str | None:
    if not row:
        return None
    return row.get(key)


def fmt_plain(value: Any) -> str:
    if value in (None, ""):
        return "-"
    return str(value)


def fmt_pct(value: Any) -> str:
    if value in (None, ""):
        return "-"
    number = float(value)
    return f"{number:.2f}%"


def money(value: Any) -> str:
    if value in (None, ""):
        return "-"
    number = float(value)
    if number >= 100:
        return f"${number:,.2f}"
    return f"${number:.4f}"


def compact_number(value: Any) -> str:
    if value in (None, ""):
        return "-"
    number = float(value)
    sign = "-" if number < 0 else ""
    number = abs(number)
    for suffix, divisor in (("T", 1_000_000_000_000), ("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
        if number >= divisor:
            return f"{sign}{number / divisor:.2f}{suffix}"
    return f"{sign}{number:.4g}"


def pct(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return round((end - start) / start * 100, 4)


def change_class(value: Any) -> str:
    if value in (None, ""):
        return ""
    number = float(value)
    if number > 0:
        return "positive"
    if number < 0:
        return "negative"
    return ""


def short_time(value: str | None) -> str:
    if not value:
        return "-"
    try:
        return parse_datetime(value).strftime("%m-%d %H:%M")
    except ValueError:
        return value


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)
