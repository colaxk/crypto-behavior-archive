from __future__ import annotations

from pathlib import Path

from src.report_generator.export_json import DOCS_DIR, export_json

DASHBOARD_PATH = DOCS_DIR / "index.html"


def generate_dashboard(output_path: Path = DASHBOARD_PATH) -> Path:
    export_json()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_html(), encoding="utf-8")
    return output_path


def build_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Crypto Behavior Archive</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #fff;
      --text: #15171a;
      --muted: #68707a;
      --line: #e4e7eb;
      --green: #12805c;
      --red: #c23b3b;
      --blue: #2458d3;
      --purple: #7c3aed;
      --amber: #9a5b13;
      --shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header, main, footer { max-width: 1120px; margin: 0 auto; }
    header { padding: 22px 16px 10px; }
    main { padding: 8px 16px 36px; }
    footer { padding: 0 16px 28px; color: var(--muted); font-size: 12px; }
    h1 { margin: 0; font-size: 25px; letter-spacing: 0; }
    h2 { margin: 0 0 12px; font-size: 18px; }
    h3 { margin: 0 0 8px; font-size: 16px; }
    select, button {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
      background: #fff;
      color: var(--text);
      font: inherit;
    }
    button {
      border: 0;
      background: var(--blue);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }
    .subtitle { margin-top: 6px; color: var(--muted); font-size: 13px; }
    .toolbar {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      align-items: center;
      margin-bottom: 12px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }
    .two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .single { margin-top: 14px; }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      padding: 14px;
      min-width: 0;
    }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfe;
      min-width: 0;
    }
    .label { color: var(--muted); font-size: 12px; }
    .value { margin-top: 2px; font-weight: 750; font-size: 17px; overflow-wrap: anywhere; }
    .positive { color: var(--green); }
    .negative { color: var(--red); }
    .muted { color: var(--muted); }
    .warn { color: var(--amber); }
    .pill {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      background: #eef3ff;
      color: var(--blue);
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }
    .pill.live { background: #e9f8f1; color: var(--green); }
    .asset-head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 10px;
    }
    .live-strip {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 14px;
    }
    .live-cell {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 10px;
    }
    canvas {
      width: 100%;
      height: 220px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfe;
    }
    .event, .report-item {
      padding: 10px 0;
      border-top: 1px solid var(--line);
    }
    .event:first-child, .report-item:first-child { border-top: 0; padding-top: 0; }
    .tags { margin-top: 5px; display: flex; flex-wrap: wrap; gap: 5px; }
    .tag { padding: 2px 7px; border-radius: 999px; background: #f0f2f5; color: #3e4651; font-size: 12px; }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      padding: 12px;
      background: #0f172a;
      color: #e5e7eb;
      border-radius: 8px;
      max-height: 430px;
      overflow: auto;
      font-size: 13px;
    }
    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 10px;
    }
    .behavior-archive {
      margin-bottom: 14px;
      padding: 4px 0 0;
    }
    .behavior-head {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 14px;
      align-items: stretch;
      margin-bottom: 14px;
    }
    .behavior-panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 14px;
      min-width: 0;
    }
    .headline {
      margin-top: 8px;
      font-size: 22px;
      line-height: 1.3;
      font-weight: 800;
    }
    .phase {
      color: var(--blue);
      font-weight: 800;
    }
    .score-total {
      font-size: 32px;
      line-height: 1;
      font-weight: 850;
    }
    .score-row {
      display: grid;
      grid-template-columns: 76px 1fr 48px;
      gap: 8px;
      align-items: center;
      margin-top: 8px;
      font-size: 12px;
    }
    .score-track {
      height: 7px;
      border-radius: 999px;
      background: #edf0f4;
      overflow: hidden;
    }
    .score-fill {
      height: 100%;
      border-radius: inherit;
      background: var(--blue);
    }
    .evidence-list {
      margin: 10px 0 0;
      padding-left: 17px;
      color: #3e4651;
      font-size: 13px;
    }
    .validation-strip {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }
    @media (max-width: 820px) {
      h1 { font-size: 22px; }
      main { padding-left: 12px; padding-right: 12px; }
      .grid, .two, .toolbar, .live-strip, .behavior-head, .validation-strip { grid-template-columns: 1fr; }
      .card { padding: 12px; }
      canvas { height: 180px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Crypto Behavior Archive</h1>
    <div class="subtitle" id="subtitle">正在读取静态历史数据...</div>
  </header>
  <main>
    <section class="toolbar">
      <label>历史日期
        <select id="dateSelect"></select>
      </label>
      <button type="button" id="copyContext">复制 GPT Context</button>
    </section>

    <section class="behavior-archive" id="behaviorArchive"></section>
    <section class="live-strip" id="liveStrip"></section>
    <section class="grid" id="assetCards"></section>

    <section class="card single">
      <h2>行为评分趋势</h2>
      <canvas id="scoreChart" width="1000" height="320"></canvas>
      <div class="subtitle">综合评分来自行为分析引擎，对每条历史快照按同一套规则重算。</div>
    </section>

    <section class="card single">
      <h2>最近30天价格曲线</h2>
      <canvas id="priceChart" width="1000" height="320"></canvas>
      <div class="subtitle">历史曲线来自仓库 docs/data/prices_*.json；最新卡片会叠加浏览器实时 API 数据。</div>
    </section>

    <section class="grid two single">
      <div class="card">
        <h2>历史事件</h2>
        <div id="events"></div>
      </div>
      <div class="card">
        <h2>历史日报</h2>
        <div id="reports"></div>
      </div>
    </section>

    <section class="card single">
      <div class="section-head">
        <h2>GPT Context</h2>
      </div>
      <pre id="gptContext">正在生成...</pre>
    </section>
  </main>
  <footer>GitHub Pages 静态页面。历史数据由 GitHub Actions commit 到仓库；实时层由浏览器直接读取公开 API，不执行交易。</footer>

  <script>
    const ASSETS = ['BTC', 'ETH', 'WLD'];
    const COLORS = { BTC: '#2458d3', ETH: '#7c3aed', WLD: '#12805c' };
    const BINANCE_SYMBOLS = { BTC: 'BTCUSDT', ETH: 'ETHUSDT', WLD: 'WLDUSDT' };
    const OKX_SPOT = { BTC: 'BTC-USDT', ETH: 'ETH-USDT', WLD: 'WLD-USDT' };
    const OKX_SWAP = { BTC: 'BTC-USDT-SWAP', ETH: 'ETH-USDT-SWAP', WLD: 'WLD-USDT-SWAP' };
    const state = {
      snapshots: [],
      prices: {},
      events: [],
      reports: [],
      hypotheses: {},
      behavior: {},
      selectedDate: null,
      live: {},
      liveErrors: {},
      liquidations: {},
      liveTimer: null,
    };

    async function loadJson(path) {
      const response = await fetch(path + '?v=' + Date.now(), { cache: 'no-store' });
      if (!response.ok) throw new Error(path + ' ' + response.status);
      return response.json();
    }

    async function boot() {
      const [snapshots, events, reports, hypotheses, behavior, btc, eth, wld] = await Promise.all([
        loadJson('data/snapshots.json'),
        loadJson('data/events.json'),
        loadJson('data/reports.json'),
        loadJson('data/hypotheses.json'),
        loadJson('data/behavior.json'),
        loadJson('data/prices_BTC.json'),
        loadJson('data/prices_ETH.json'),
        loadJson('data/prices_WLD.json'),
      ]);
      state.snapshots = snapshots;
      state.events = events;
      state.reports = reports;
      state.hypotheses = hypotheses;
      state.behavior = behavior;
      state.prices = { BTC: btc, ETH: eth, WLD: wld };
      state.selectedDate = latestDate(snapshots);
      ASSETS.forEach(asset => {
        state.liquidations[asset] = { total: 0, long: 0, short: 0, count: 0, startedAt: new Date().toISOString() };
      });
      fillDateSelect();
      render();
      startLive();
    }

    function fillDateSelect() {
      const select = document.getElementById('dateSelect');
      const dates = [...new Set(state.snapshots.map(row => day(row.timestamp)).filter(Boolean))].sort();
      select.innerHTML = dates.map(date => `<option value="${date}">${date}</option>`).join('');
      select.value = state.selectedDate;
      select.addEventListener('change', () => {
        state.selectedDate = select.value;
        render();
      });
    }

    function render() {
      const latestDateValue = latestDate(state.snapshots);
      const useLive = state.selectedDate === latestDateValue;
      const latestByAsset = Object.fromEntries(ASSETS.map(asset => {
        const archived = snapshotFor(asset, state.selectedDate);
        return [asset, useLive ? mergeLive(asset, archived) : archived];
      }));
      const liveSummary = ASSETS.map(asset => state.live[asset]?.status || '等待实时数据').join(' / ');
      document.getElementById('subtitle').innerText =
        `历史日期 ${state.selectedDate} · 仓库快照 ${state.hypotheses.latest_snapshot_time || '-'} · 实时层 ${liveSummary}`;
      renderBehaviorArchive();
      renderLiveStrip();
      document.getElementById('assetCards').innerHTML = ASSETS.map(asset => assetCard(asset, latestByAsset[asset], useLive)).join('');
      renderEvents();
      renderReports();
      drawScoreChart();
      drawChart();
      document.getElementById('gptContext').innerText = buildContext(latestByAsset, useLive);
    }

    function behaviorForDate(date) {
      const byDate = state.behavior.by_date || {};
      if (byDate[date]) return byDate[date];
      const dates = Object.keys(byDate).filter(item => item <= date).sort();
      return dates.length ? byDate[dates[dates.length - 1]] : state.behavior.latest || {};
    }

    function renderBehaviorArchive() {
      const payload = behaviorForDate(state.selectedDate);
      const conclusion = payload.conclusion || {};
      const assets = payload.assets || {};
      const focus = conclusion.focus_asset && assets[conclusion.focus_asset] ? assets[conclusion.focus_asset] : Object.values(assets)[0];
      const assetCards = ASSETS.map(asset => behaviorAssetCard(asset, assets[asset])).join('');
      document.getElementById('behaviorArchive').innerHTML = `
        <div class="behavior-head">
          <div class="behavior-panel">
            <div class="label">Behavior Conclusion · ${escapeHtml(payload.date || state.selectedDate)}</div>
            <div class="headline">${escapeHtml(conclusion.headline || '暂无足够数据生成今日最大变化。')}</div>
            <div class="subtitle">${escapeHtml(conclusion.summary || '暂无行为画像。')}</div>
          </div>
          <div class="behavior-panel">
            <div class="label">聚焦资产</div>
            ${focus ? focusAssetBlock(focus) : '<div class="muted">暂无行为评分</div>'}
          </div>
        </div>
        <div class="grid">${assetCards}</div>
        <div class="validation-strip">${validationCards()}</div>
      `;
    }

    function focusAssetBlock(item) {
      return `<div>
        <div class="asset-head"><h2>${escapeHtml(item.asset || '-')}</h2><span class="pill">${escapeHtml(item.phase || '等待确认')}</span></div>
        <div class="score-total">${plain(item.scores?.composite, '-')}<span class="label"> /100</span></div>
        <div class="subtitle">${escapeHtml(item.summary || '')}</div>
        ${scoreRows(item.scores || {})}
      </div>`;
    }

    function behaviorAssetCard(asset, item) {
      if (!item) return `<div class="card"><h2>${asset}</h2><div class="muted">暂无行为画像</div></div>`;
      const evidence = flattenEvidence(item.evidence).slice(0, 4);
      return `<div class="card">
        <div class="asset-head"><h2>${asset}</h2><span class="pill">${escapeHtml(item.phase || '等待确认')}</span></div>
        <div class="score-total">${plain(item.scores?.composite, '-')}<span class="label"> /100</span></div>
        <div class="subtitle">${escapeHtml(item.summary || '')}</div>
        <div class="tags">${(item.tags || []).slice(0, 8).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div>
        ${scoreRows(item.scores || {})}
        <ul class="evidence-list">${evidence.map(line => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
      </div>`;
    }

    function scoreRows(scores) {
      const rows = [
        ['估值', 'valuation'],
        ['趋势', 'trend'],
        ['主力', 'whale_behavior'],
        ['资金', 'capital_quality'],
        ['杠杆', 'leverage_health'],
        ['供应', 'tokenomics'],
      ];
      return rows.map(([label, key]) => scoreRow(label, scores[key])).join('');
    }

    function scoreRow(label, value) {
      const n = Math.max(0, Math.min(100, Number(value) || 0));
      return `<div class="score-row">
        <span class="label">${label}</span>
        <span class="score-track"><span class="score-fill" style="width:${n}%"></span></span>
        <span class="label">${n}</span>
      </div>`;
    }

    function flattenEvidence(evidence) {
      if (!evidence) return [];
      return ['trend', 'whale_behavior', 'capital_quality', 'leverage', 'relative_strength', 'tokenomics']
        .flatMap(key => evidence[key] || []);
    }

    function validationCards() {
      const tags = state.behavior.validations?.tags || {};
      const items = Object.entries(tags)
        .map(([tag, payload]) => ({ tag, ...payload }))
        .sort((a, b) => (b.count || 0) - (a.count || 0))
        .slice(0, 3);
      if (!items.length) return '<div class="behavior-panel"><div class="label">历史验证</div><div class="muted">暂无已验证行为标签</div></div>';
      return items.map(item => {
        const win = item.windows?.['30d'] || item.windows?.['7d'] || item.windows?.['24h'] || {};
        const result = win.samples ? `样本 ${win.samples} · 胜率 ${win.success_rate}% · 均值 ${pct(win.avg_change_pct)}` : `出现 ${item.count} 次，等待后续价格点`;
        return `<div class="behavior-panel">
          <div class="label">历史验证</div>
          <h3>${escapeHtml(item.tag)}</h3>
          <div class="subtitle">${escapeHtml(result)}</div>
        </div>`;
      }).join('');
    }

    function mergeLive(asset, archived) {
      const row = { ...(archived || {}) };
      const live = state.live[asset] || {};
      for (const key of [
        'timestamp', 'price', 'change_24h', 'volume_24h', 'oi', 'funding_rate',
        'liquidation_total', 'long_liquidation', 'short_liquidation',
        'long_short_ratio', 'cvd', 'heatmap', 'spot_volume', 'futures_volume', 'note'
      ]) {
        if (live[key] !== undefined && live[key] !== null && live[key] !== '') row[key] = live[key];
      }
      return row;
    }

    function snapshotFor(asset, date) {
      const rows = state.snapshots
        .filter(row => row.asset === asset && day(row.timestamp) <= date)
        .sort((a, b) => String(a.timestamp).localeCompare(String(b.timestamp)));
      return rows[rows.length - 1] || null;
    }

    function assetCard(asset, row, useLive) {
      if (!row) return `<div class="card"><h2>${asset}</h2><div class="muted">暂无快照</div></div>`;
      const live = state.live[asset] || {};
      const liq = state.liquidations[asset] || {};
      const pillClass = useLive && live.timestamp ? 'pill live' : 'pill';
      const pillText = useLive && live.timestamp ? `实时 ${shortClock(live.timestamp)}` : shortTime(row.timestamp);
      const source = useLive ? live.status || '实时层等待中' : '历史档案';
      return `<div class="card">
        <div class="asset-head"><h2>${asset}</h2><span class="${pillClass}">${escapeHtml(pillText)}</span></div>
        <div class="metric-grid">
          ${metric('价格', money(row.price))}
          ${metric('24h涨跌', pct(row.change_24h), row.change_24h)}
          ${metric('OI', compact(row.oi))}
          ${metric('Funding', pct(row.funding_rate, '未返回'))}
          ${metric('爆仓总额', compact(row.liquidation_total, '0，本页实时'), row.liquidation_total)}
          ${metric('多单爆仓', compact(row.long_liquidation, '0，本页实时'), row.long_liquidation)}
          ${metric('空单爆仓', compact(row.short_liquidation, '0，本页实时'), row.short_liquidation)}
          ${metric('多空比', plain(row.long_short_ratio, '未返回'))}
          ${metric('CVD', compact(row.cvd, '未返回'))}
          ${metric('Heatmap', plain(row.heatmap, '需 CoinGlass API'))}
          ${metric('现货成交量', compact(row.spot_volume))}
          ${metric('合约成交量', compact(row.futures_volume))}
        </div>
        <div class="subtitle">${escapeHtml(source)} · 强平WS累计 ${liq.count || 0} 笔 · ${escapeHtml(row.note || '')}</div>
      </div>`;
    }

    function metric(label, value, raw) {
      const cls = Number(raw) > 0 ? 'positive' : Number(raw) < 0 ? 'negative' : '';
      return `<div class="metric"><div class="label">${label}</div><div class="value ${cls}">${escapeHtml(value)}</div></div>`;
    }

    function renderLiveStrip() {
      document.getElementById('liveStrip').innerHTML = ASSETS.map(asset => {
        const live = state.live[asset] || {};
        const err = state.liveErrors[asset];
        const cls = live.timestamp ? 'positive' : err ? 'negative' : 'warn';
        const text = live.timestamp ? `${money(live.price)} · ${pct(live.change_24h)}` : err || '正在请求公开 API...';
        return `<div class="live-cell">
          <div class="label">${asset} 实时层</div>
          <div class="value ${cls}">${escapeHtml(text)}</div>
          <div class="subtitle">${escapeHtml(live.source || 'Binance 主源，OKX 备用')}</div>
        </div>`;
      }).join('');
    }

    function renderEvents() {
      const selected = state.events
        .filter(event => day(event.event_time) <= state.selectedDate)
        .sort((a, b) => String(b.event_time).localeCompare(String(a.event_time)))
        .slice(0, 20);
      document.getElementById('events').innerHTML = selected.length ? selected.map(event => `
        <div class="event">
          <h3>${escapeHtml(event.title || event.event_id)}</h3>
          <div class="label">${escapeHtml(event.event_time || '')} · ${escapeHtml(event.asset || '')} · ${escapeHtml(event.event_type || '')}</div>
          <div class="tags">${(event.tags || []).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div>
          <div class="subtitle">${escapeHtml(event.description || compactOutcome(event.outcome))}</div>
        </div>`).join('') : '<div class="muted">暂无事件</div>';
    }

    function renderReports() {
      const selected = state.reports
        .filter(report => report.date <= state.selectedDate)
        .sort((a, b) => String(b.date).localeCompare(String(a.date)))
        .slice(0, 12);
      document.getElementById('reports').innerHTML = selected.length ? selected.map(report => `
        <div class="report-item">
          <h3>${escapeHtml(report.title || report.date)}</h3>
          <div class="label">${escapeHtml(report.date || '')}</div>
          <div class="subtitle">${escapeHtml(report.summary || '')}</div>
          <div><a href="${escapeHtml(report.path)}">打开 Markdown 日报</a></div>
        </div>`).join('') : '<div class="muted">暂无日报</div>';
    }

    function drawChart() {
      const canvas = document.getElementById('priceChart');
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const end = new Date(state.selectedDate + 'T23:59:59');
      const start = new Date(end.getTime() - 30 * 24 * 60 * 60 * 1000);
      ASSETS.forEach(asset => {
        const points = (state.prices[asset] || []).filter(row => {
          const time = new Date(row.timestamp);
          return time >= start && time <= end && row.price != null;
        });
        drawLine(ctx, canvas, points, COLORS[asset]);
      });
    }

    function drawScoreChart() {
      const canvas = document.getElementById('scoreChart');
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const end = new Date(state.selectedDate + 'T23:59:59');
      const start = new Date(end.getTime() - 30 * 24 * 60 * 60 * 1000);
      ctx.strokeStyle = '#e4e7eb';
      ctx.lineWidth = 1;
      [25, 50, 75].forEach(score => {
        const y = canvas.height - 18 - (score / 100) * (canvas.height - 36);
        ctx.beginPath();
        ctx.moveTo(18, y);
        ctx.lineTo(canvas.width - 18, y);
        ctx.stroke();
      });
      ASSETS.forEach(asset => {
        const points = (state.behavior.history?.[asset] || []).filter(row => {
          const time = new Date(row.date + 'T12:00:00');
          return time >= start && time <= end && row.composite != null;
        });
        drawScoreLine(ctx, canvas, points, COLORS[asset]);
      });
    }

    function drawScoreLine(ctx, canvas, points, color) {
      if (!points.length) return;
      const pad = 18;
      ctx.beginPath();
      points.forEach((point, index) => {
        const x = pad + (canvas.width - pad * 2) * (index / Math.max(points.length - 1, 1));
        const y = canvas.height - pad - (Number(point.composite) / 100) * (canvas.height - pad * 2);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.stroke();
    }

    function drawLine(ctx, canvas, points, color) {
      if (!points.length) return;
      const pad = 18;
      const values = points.map(p => Number(p.price));
      const min = Math.min(...values);
      const max = Math.max(...values);
      const span = max - min || 1;
      ctx.beginPath();
      points.forEach((point, index) => {
        const x = pad + (canvas.width - pad * 2) * (index / Math.max(points.length - 1, 1));
        const y = canvas.height - pad - ((Number(point.price) - min) / span) * (canvas.height - pad * 2);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.stroke();
    }

    async function startLive() {
      connectLiquidationSockets();
      await refreshLive();
      state.liveTimer = setInterval(refreshLive, 30000);
    }

    async function refreshLive() {
      await Promise.all(ASSETS.map(asset => refreshAsset(asset)));
      render();
    }

    async function refreshAsset(asset) {
      try {
        const [spot, futures, okx] = await Promise.allSettled([
          fetchBinanceSpot(asset),
          fetchBinanceFutures(asset),
          fetchOkxFallback(asset),
        ]);
        const live = {};
        const sources = [];
        if (spot.status === 'fulfilled') {
          Object.assign(live, spot.value);
          sources.push('Binance Spot');
        }
        if (futures.status === 'fulfilled') {
          Object.assign(live, futures.value);
          sources.push('Binance Futures');
        }
        if (okx.status === 'fulfilled') {
          for (const [key, value] of Object.entries(okx.value)) {
            if (live[key] === undefined || live[key] === null || live[key] === '') live[key] = value;
          }
          sources.push('OKX fallback');
        }
        const liq = state.liquidations[asset] || {};
        live.liquidation_total = liq.total || 0;
        live.long_liquidation = liq.long || 0;
        live.short_liquidation = liq.short || 0;
        live.heatmap = live.heatmap || '需 CoinGlass API';
        live.timestamp = new Date().toISOString();
        live.status = sources.length ? '已实时刷新' : '实时源未返回';
        live.source = sources.join(' + ') || '未返回';
        live.note = `实时层：${live.source}；爆仓为本页打开后的 Binance 强平流累计，非24h历史总额`;
        state.live[asset] = live;
        delete state.liveErrors[asset];
      } catch (error) {
        state.liveErrors[asset] = error.message || String(error);
      }
    }

    async function fetchBinanceSpot(asset) {
      const symbol = BINANCE_SYMBOLS[asset];
      const data = await fetchAny([
        `https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}`,
        `https://data-api.binance.vision/api/v3/ticker/24hr?symbol=${symbol}`,
      ]);
      return {
        price: number(data.lastPrice),
        change_24h: number(data.priceChangePercent),
        volume_24h: number(data.quoteVolume),
        spot_volume: number(data.quoteVolume),
      };
    }

    async function fetchBinanceFutures(asset) {
      const symbol = BINANCE_SYMBOLS[asset];
      const [premium, oi, ticker, longShort, taker] = await Promise.allSettled([
        fetchAny([`https://fapi.binance.com/fapi/v1/premiumIndex?symbol=${symbol}`]),
        fetchAny([`https://fapi.binance.com/fapi/v1/openInterest?symbol=${symbol}`]),
        fetchAny([`https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=${symbol}`]),
        fetchAny([`https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=${symbol}&period=5m&limit=1`]),
        fetchAny([`https://fapi.binance.com/futures/data/takerlongshortRatio?symbol=${symbol}&period=1h&limit=24`]),
      ]);
      const p = premium.status === 'fulfilled' ? premium.value : {};
      const open = oi.status === 'fulfilled' ? oi.value : {};
      const t = ticker.status === 'fulfilled' ? ticker.value : {};
      const ls = longShort.status === 'fulfilled' && Array.isArray(longShort.value) ? longShort.value.at(-1) || {} : {};
      const flow = taker.status === 'fulfilled' && Array.isArray(taker.value) ? taker.value : [];
      const mark = number(p.markPrice || t.lastPrice);
      const contracts = number(open.openInterest);
      return {
        funding_rate: number(p.lastFundingRate) * 100,
        oi: mark && contracts ? mark * contracts : contracts,
        futures_volume: number(t.quoteVolume),
        long_short_ratio: number(ls.longShortRatio),
        cvd: flow.reduce((sum, row) => sum + number(row.buyVol) - number(row.sellVol), 0),
      };
    }

    async function fetchOkxFallback(asset) {
      const [spot, funding, oi, swapTicker] = await Promise.allSettled([
        fetchAny([`https://www.okx.com/api/v5/market/ticker?instId=${OKX_SPOT[asset]}`]),
        fetchAny([`https://www.okx.com/api/v5/public/funding-rate?instId=${OKX_SWAP[asset]}`]),
        fetchAny([`https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=${OKX_SWAP[asset]}`]),
        fetchAny([`https://www.okx.com/api/v5/market/ticker?instId=${OKX_SWAP[asset]}`]),
      ]);
      const result = {};
      const s = spot.status === 'fulfilled' ? firstData(spot.value) : {};
      const f = funding.status === 'fulfilled' ? firstData(funding.value) : {};
      const o = oi.status === 'fulfilled' ? firstData(oi.value) : {};
      const sw = swapTicker.status === 'fulfilled' ? firstData(swapTicker.value) : {};
      if (s.last) result.price = number(s.last);
      if (s.sodUtc0 && s.last) result.change_24h = ((number(s.last) - number(s.sodUtc0)) / number(s.sodUtc0)) * 100;
      if (s.volCcy24h && s.last) result.spot_volume = number(s.volCcy24h) * number(s.last);
      if (f.fundingRate) result.funding_rate = number(f.fundingRate) * 100;
      if (o.oiUsd) result.oi = number(o.oiUsd);
      if (sw.volCcy24h && sw.last) result.futures_volume = number(sw.volCcy24h) * number(sw.last);
      return result;
    }

    function connectLiquidationSockets() {
      ASSETS.forEach(asset => {
        const stream = `${BINANCE_SYMBOLS[asset].toLowerCase()}@forceOrder`;
        try {
          const socket = new WebSocket(`wss://fstream.binance.com/ws/${stream}`);
          socket.onmessage = event => {
            const payload = JSON.parse(event.data);
            const order = payload.o || {};
            const qty = number(order.q || order.z);
            const price = number(order.ap || order.p);
            const notional = qty * price;
            if (!Number.isFinite(notional) || notional <= 0) return;
            const liq = state.liquidations[asset];
            liq.total += notional;
            liq.count += 1;
            if (order.S === 'SELL') liq.long += notional;
            if (order.S === 'BUY') liq.short += notional;
            render();
          };
          socket.onerror = () => {
            state.liveErrors[asset] = `${asset} 强平 WebSocket 暂不可用`;
            renderLiveStrip();
          };
        } catch (error) {
          state.liveErrors[asset] = `${asset} 强平 WebSocket 打不开`;
        }
      });
    }

    async function fetchAny(urls) {
      let lastError;
      for (const url of urls) {
        try {
          const controller = new AbortController();
          const timer = setTimeout(() => controller.abort(), 8000);
          const response = await fetch(url, { cache: 'no-store', signal: controller.signal });
          clearTimeout(timer);
          if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
          return response.json();
        } catch (error) {
          lastError = error;
        }
      }
      throw lastError || new Error('all endpoints failed');
    }

    function buildContext(latestByAsset, useLive) {
      const behavior = behaviorForDate(state.selectedDate);
      const behaviorAssets = ASSETS.map(asset => {
        const item = behavior.assets?.[asset];
        if (!item) return `${asset}: 暂无行为画像`;
        return `${asset}: ${item.phase} / 综合评分 ${item.scores?.composite}/100
行为总结: ${item.summary}
行为标签: ${(item.tags || []).join('、')}
关键证据: ${flattenEvidence(item.evidence).slice(0, 5).join('；')}`;
      }).join('\\n\\n');
      const blocks = ASSETS.map(asset => {
        const row = latestByAsset[asset] || {};
        return `${asset}

价格: ${money(row.price)} / 24h ${pct(row.change_24h)} / 时间 ${row.timestamp || '-'}
OI: ${compact(row.oi)}
Funding: ${pct(row.funding_rate, '未返回')}
Liquidation: ${compact(row.liquidation_total, '0，本页实时累计')}
CVD: ${compact(row.cvd, '未返回')}
Heatmap: ${plain(row.heatmap, '需 CoinGlass API')}
状态: ${row.note || '待判断'}`;
      }).join('\\n\\n---\\n\\n');
      const verified = (state.hypotheses.verified || []).map(item => `- ${item.asset} ${item.title}: ${item.outcome}`).join('\\n') || '- 暂无';
      const current = (state.hypotheses.current || []).map(item => `- ${item}`).join('\\n');
      const pending = (state.hypotheses.pending || []).map(item => `- ${item}`).join('\\n');
      const mode = useLive ? '当前卡片已叠加浏览器实时 API 数据。' : '当前为历史日期回溯，未叠加实时数据。';
      return `Behavior Conclusion
今天最大的变化: ${behavior.conclusion?.headline || '-'}
行为摘要: ${behavior.conclusion?.summary || '-'}

Behavior Summary
${behaviorAssets}

---

原始数据
${blocks}

---

当前假设
${current}

已验证
${verified}

待验证
${pending}

数据说明
- ${mode}
- 爆仓为本页打开后 Binance 强平 WebSocket 捕捉累计，不等于 24h 历史爆仓。
- Heatmap/清算地图需要 CoinGlass API 或其他授权数据源，静态 GitHub Pages 不能稳定抓网页私有数据。

请基于以上上下文分析 BTC/ETH/WLD 的资金行为、异常事件、相对强弱、风险和下一步待验证假设。不要给自动交易指令。`;
    }

    document.getElementById('copyContext').addEventListener('click', async () => {
      const text = document.getElementById('gptContext').innerText;
      try {
        await navigator.clipboard.writeText(text);
        document.getElementById('copyContext').innerText = '已复制';
      } catch (error) {
        const area = document.createElement('textarea');
        area.value = text;
        document.body.appendChild(area);
        area.select();
        document.execCommand('copy');
        area.remove();
        document.getElementById('copyContext').innerText = '已复制';
      }
      setTimeout(() => document.getElementById('copyContext').innerText = '复制 GPT Context', 1200);
    });

    function latestDate(rows) {
      const dates = rows.map(row => day(row.timestamp)).filter(Boolean).sort();
      return dates[dates.length - 1] || new Date().toISOString().slice(0, 10);
    }
    function day(value) { return value ? String(value).slice(0, 10) : ''; }
    function shortTime(value) { return value ? String(value).slice(5, 16).replace('T', ' ') : '-'; }
    function shortClock(value) { return value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '-'; }
    function plain(value, missing = '-') { return value === null || value === undefined || value === '' ? missing : String(value); }
    function pct(value, missing = '-') {
      if (value === null || value === undefined || value === '') return missing;
      const n = Number(value);
      return Number.isFinite(n) ? n.toFixed(3).replace(/\\.000$/, '') + '%' : missing;
    }
    function money(value) {
      if (value === null || value === undefined || value === '') return '-';
      const n = Number(value);
      if (!Number.isFinite(n)) return '-';
      return n >= 100 ? '$' + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '$' + n.toFixed(4);
    }
    function compact(value, missing = '-') {
      if (value === null || value === undefined || value === '') return missing;
      let n = Number(value);
      if (!Number.isFinite(n)) return missing;
      const sign = n < 0 ? '-' : '';
      n = Math.abs(n);
      const units = [['T', 1e12], ['B', 1e9], ['M', 1e6], ['K', 1e3]];
      for (const [suffix, divisor] of units) {
        if (n >= divisor) return sign + (n / divisor).toFixed(2) + suffix;
      }
      return sign + n.toPrecision(4);
    }
    function number(value) {
      const n = Number(value);
      return Number.isFinite(n) ? n : 0;
    }
    function firstData(payload) {
      return payload && Array.isArray(payload.data) && payload.data.length ? payload.data[0] : {};
    }
    function compactOutcome(outcome) {
      if (!outcome) return '';
      return ['1h', '4h', '24h', '3d', '7d', '30d'].map(key => outcome[key]?.change_pct !== undefined ? `${key}:${outcome[key].change_pct}%` : '').filter(Boolean).join(' ');
    }
    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
    }

    boot().catch(error => {
      document.getElementById('subtitle').innerText = '读取 docs/data 失败：' + error.message;
      console.error(error);
    });
  </script>
</body>
</html>
"""
