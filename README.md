# Crypto Behavior Archive / 加密资产行为档案系统

本项目是一个本地可运行的加密资产行为档案 MVP。它不做自动交易，也不预测价格；目标是长期记录 BTC、ETH、WLD 等资产的市场行为、异常事件、后续表现与复盘结论。

第一阶段聚焦：

- 手动录入或 CSV 导入 BTC / ETH / WLD 每日快照
- 记录异常事件与行为标签
- 计算事件后 1h、4h、24h、3d、7d 的价格变化
- 查询历史事件
- 生成 Markdown 日报

## 快速开始

```bash
python3 -m src.cli init
python3 -m src.cli add-snapshot --asset BTC --price 65000 --change-24h 2.1 --volume-24h 35000000000 --note "manual test"
python3 -m src.cli add-event --asset BTC --event-time 2026-06-23T12:00:00+08:00 --event-type volume_spike --price 65000 --title "放量突破测试" --tags 放量突破 合约推动
python3 -m src.cli list-events --asset BTC
python3 -m src.cli generate-report --date 2026-06-23
```

生成的日报会保存在 `reports/`。

## 常用命令

初始化目录：

```bash
python3 -m src.cli init
```

录入每日快照：

```bash
python3 -m src.cli add-snapshot \
  --asset WLD \
  --price 3.25 \
  --change-24h -1.2 \
  --volume-24h 180000000 \
  --oi 95000000 \
  --oi-change 8.4 \
  --funding-rate 0.018 \
  --liquidation-total 1200000 \
  --long-liquidation 900000 \
  --short-liquidation 300000 \
  --long-short-ratio 1.35 \
  --spot-volume 75000000 \
  --futures-volume 260000000 \
  --note "资金费率偏热"
```

导入快照 CSV：

```bash
python3 -m src.cli import-snapshots data/raw/snapshots.csv
```

录入价格点，用于计算事件后收益：

```bash
python3 -m src.cli add-price --asset WLD --time 2026-06-23T12:00:00+08:00 --price 3.25
python3 -m src.cli add-price --asset WLD --time 2026-06-23T16:00:00+08:00 --price 3.41
```

从 Binance K 线自动补齐价格点：

```bash
python3 -m src.cli backfill-prices \
  --asset BTC \
  --interval 1h \
  --start 2026-06-01T00:00:00+08:00 \
  --end 2026-06-23T00:00:00+08:00

python3 -m src.cli backfill-prices \
  --asset WLD \
  --interval 1h \
  --start 2026-06-01T00:00:00+08:00 \
  --end 2026-06-23T00:00:00+08:00
```

从 Binance 24h ticker 写入一个基础快照：

```bash
python3 -m src.cli fetch-binance-snapshot --asset BTC
python3 -m src.cli fetch-binance-snapshot --asset WLD
```

抓取 CoinGlass 页面并保存原始页面/解析结果：

```bash
python3 -m src.cli fetch-coinglass --asset BTC
python3 -m src.cli fetch-coinglass --asset WLD
```

如果页面解析出了 OI、Funding、爆仓或多空比，可以同时写入快照。若页面没有解析出价格，需要手动传入价格：

```bash
python3 -m src.cli fetch-coinglass --asset WLD --write-snapshot --price 3.25
```

每日采集一条龙：补最近 24 根 Binance K 线价格点，并写入合并后的 BTC/ETH/WLD 快照。CoinGlass 抓取失败时会保留 Binance 数据，不会中断另一个标的。

```bash
python3 -m src.cli daily-collect
```

只跑 Binance：

```bash
python3 -m src.cli daily-collect --skip-coinglass
```

记录异常事件：

```bash
python3 -m src.cli add-event \
  --asset WLD \
  --event-time 2026-06-23T12:00:00+08:00 \
  --event-type funding_hot \
  --price 3.25 \
  --title "Funding 过热" \
  --description "Funding 升高，OI 同步增加" \
  --tags Funding异常升高 合约推动
```

更新事件后表现：

```bash
python3 -m src.cli update-outcomes --event-id EVT-20260623-120000-WLD
```

查询事件：

```bash
python3 -m src.cli list-events --asset WLD --tag 合约推动
python3 -m src.cli query --asset WLD --tag Funding异常升高 --days 30
```

生成日报：

```bash
python3 -m src.cli generate-report --date 2026-06-23
```

生成静态仪表板：

```bash
python3 -m src.cli generate-dashboard
```

仪表板会生成到 `docs/index.html`，适合用 GitHub Pages 免费发布。

导出网页读取的静态 JSON 和日报副本：

```bash
python3 -m src.cli export-json
```

导出结果会写入 `docs/data/` 和 `docs/reports/`。GitHub Pages 页面刷新时读取这些静态文件，历史数据仍长期保存在仓库里，不依赖浏览器内存。

## 目录结构

```text
crypto_behavior_archive/
├── data/
│   ├── raw/
│   ├── processed/
│   └── screenshots/
├── assets/
│   ├── BTC/
│   ├── ETH/
│   └── WLD/
├── events/
├── reports/
├── notebooks/
├── src/
│   ├── collectors/
│   ├── analyzers/
│   ├── indicators/
│   ├── event_detector/
│   ├── report_generator/
│   └── utils/
├── config.yaml
├── requirements.txt
└── README.md
```

## 数据文件

- `data/processed/snapshots.csv`: 每日资产快照
- `data/processed/prices.csv`: 手动价格点
- `events/events.jsonl`: 异常事件，每行一个 JSON
- `reports/*.md`: Markdown 日报
- `docs/index.html`: 静态仪表板，适合 GitHub Pages 发布
- `docs/data/snapshots.json`: 网页读取的快照历史
- `docs/data/prices_BTC.json`: BTC 价格历史
- `docs/data/prices_ETH.json`: ETH 价格历史
- `docs/data/prices_WLD.json`: WLD 价格历史
- `docs/data/events.json`: 网页读取的异常事件
- `docs/data/hypotheses.json`: GPT Context 与假设区块数据
- `docs/reports/*.md`: GitHub Pages 可访问的日报副本

## GitHub Pages 部署

目标：用 GitHub Pages 免费地址查看 `docs/index.html`，例如：

```text
https://你的GitHub用户名.github.io/仓库名/
```

### 第一次发布

1. 在 GitHub 新建一个仓库，例如 `crypto-behavior-archive`。
2. 把本项目推送到该仓库。
3. 打开仓库页面，进入 `Settings` -> `Pages`。
4. 在 `Build and deployment` 里选择：
   - Source: `Deploy from a branch`
   - Branch: `main`
   - Folder: `/docs`
5. 点击 `Save`。
6. 等待 1-3 分钟，GitHub 会给出 Pages 访问地址。

### 自动更新

本项目已经包含 GitHub Actions workflow：

```text
.github/workflows/daily-dashboard.yml
```

它会每天自动执行一次，当前设置为北京时间 00:10 左右。注意：GitHub Actions 的定时任务按 UTC 调度，且可能延迟几分钟到几十分钟，不是实时任务。

```bash
python3 -m src.cli daily-collect
python3 -m src.cli update-outcomes --all
python3 -m src.cli generate-report --date "$(date +%F)"
python3 -m src.cli generate-dashboard
python3 -m src.cli export-json
```

然后提交这些文件：

- `data/processed/`
- `docs/data/`
- `docs/reports/`
- `docs/index.html`
- `events/events.jsonl`
- `reports/*.md`

这样 GitHub 仓库会长期保存 CSV / JSON / Markdown 历史数据，GitHub Pages 页面也会随着这些静态文件一起更新。页面刷新时读取的是 `docs/data/*.json`，不是浏览器临时内存，所以可以支持半年、一年甚至更久的回溯。

### 手动触发更新

在 GitHub 仓库页面：

1. 打开 `Actions`。
2. 选择 `Daily Crypto Behavior Dashboard`。
3. 点击 `Run workflow`。
4. 等待运行完成后刷新 Pages 页面。

### 需要你配合的地方

我无法替你在 GitHub 网页里创建仓库或打开 Pages 开关。你需要做两件事：

1. 提供或确认 GitHub 仓库地址。
2. 在 GitHub 仓库 `Settings` -> `Pages` 里选择 `main` 分支的 `/docs` 目录。

如果你还没有仓库，可以先在 GitHub 新建一个空仓库，然后把仓库 URL 发给我，我可以继续指导你执行本地推送步骤。

## 行为标签建议

- 放量突破
- 放量滞涨
- 缩量阴跌
- 恐慌下杀
- 洗盘
- 派发
- 吸筹
- 换手
- 合约推动
- 现货推动
- 大盘拖累
- 独立行情
- KOL影响
- 消息驱动
- 未知

## 后续扩展

- CoinGlass OI / Funding / 爆仓稳定 API 接入
- X/Twitter 与新闻事件接入
- 图表可视化
- 行为模式统计
- 交易复盘模块
