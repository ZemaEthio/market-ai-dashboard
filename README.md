# Zero-Cost Gold & Forex Market AI

A full decision-support system for gold and forex analysis using free data sources, deterministic technical analysis, news and macro scoring, scenario generation, strict risk controls, a Streamlit dashboard, a FastAPI service, and scheduled GitHub Actions refreshes.

> Research and paper-trading support only. This project does not execute trades and is not financial advice.

## Live dashboard

**Streamlit app:** https://zema-ai-trading-dashboard.streamlit.app

## System architecture

```text
Yahoo Finance + official central-bank RSS feeds
                    ↓
           Data collection and validation
                    ↓
              SQLite persistence
                    ↓
      Engine 1 — Market and technical analysis
                    ↓
      Engine 2 — News and macro analysis
                    ↓
      Engine 3 — Decision and explanation
                    ↓
       Deterministic Risk Engine
                    ↓
         Streamlit dashboard + FastAPI
```

## Main components

### Engine 1 — Market analysis
Calculates EMA 20/50/200, RSI 14, ATR 14, trend, regime, support/resistance, bias, confidence, invalidation, and data quality. Results are stored in `market_analyses`.

### Engine 2 — News and macro analysis
Collects Federal Reserve, ECB, and Bank of England RSS releases, with optional GDELT discovery and optional Ollama summaries. It deduplicates, filters relevance, scores impact, and stores results in `news_articles` and `news_analyses`.

### Engine 3 — Decision and explanation
Combines the latest valid market and news analyses to produce overall bias, confidence, engine alignment, preferred action, bullish/bearish/neutral scenarios, invalidation conditions, no-trade reasons, and risk level. Results are stored in `decision_analyses`.

### Deterministic Risk Engine
Rule-based final gatekeeper with 0.5% max risk per trade, 2% daily-loss lockout, 2:1 minimum reward-to-risk, 2% maximum stop distance, 55% minimum decision confidence, 2-hour staleness limit, 30-minute high-impact-event lockout, and automatic rejection of `wait` decisions. Results are stored in `risk_evaluations`.

## Free data stack

- Price research data: Yahoo Finance through `yfinance`
- Gold symbol: `GC=F`
- EUR/USD symbol: `EURUSD=X`
- Official news: Federal Reserve, ECB, and Bank of England RSS
- Broader news discovery: optional GDELT DOC API
- Optional local LLM: Ollama
- Default database: SQLite
- Optional database target: Microsoft SQL Server

## Database

Default database:

```text
data/market_ai.db
```

Core tables:

```text
price_candles
collection_runs
market_analyses
news_articles
news_analyses
decision_analyses
risk_evaluations
```

Verify:

```powershell
python inspect_database.py
```

## Local setup

Python 3.12 is recommended.

```powershell
Set-Location "E:\MarketAI"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

## Collect market data

```powershell
python collect_data.py `
  --symbols "GC=F" "EURUSD=X" `
  --period 6mo `
  --interval 1h `
  --database-url "sqlite:///./data/market_ai.db"
```

## Run the full pipeline

```powershell
python collect_data.py --symbols "GC=F" "EURUSD=X" --period 6mo --interval 1h --database-url "sqlite:///./data/market_ai.db"
python run_market_engine.py --symbols "GC=F" "EURUSD=X" --interval 1h
python run_news_engine.py --symbols "GC=F" "EURUSD=X" --lookback-hours 168 --no-gdelt
python run_decision_engine.py --symbols "GC=F" "EURUSD=X" --interval 1h
python run_risk_engine.py --symbols "GC=F" "EURUSD=X" --interval 1h --account-balance 10000
```

## Inspect engine outputs

```powershell
python inspect_market_analysis.py
python inspect_news_analysis.py
python inspect_decision_analysis.py
python inspect_risk_evaluations.py
```

## Streamlit dashboard

Run locally:

```powershell
python -m streamlit run streamlit_app.py
```

Local URL:

```text
http://localhost:8501
```

The dashboard shows price history, technical indicators, news drivers, Engine 3 scenarios, confidence, final risk approval/rejection, position sizing, data-quality warnings, and audit IDs.

## FastAPI service

Start:

```powershell
python -m uvicorn app.api.main:app --reload
```

Docs:

```text
http://127.0.0.1:8000/docs
```

Endpoints:

```text
GET /health
GET /symbols
GET /candles/{symbol}
GET /market/{symbol}
GET /news/{symbol}
GET /decision/{symbol}
GET /risk/{symbol}
GET /news-articles
GET /latest/{symbol}
```

## Automatic refresh

Workflow file:

```text
.github/workflows/refresh-market-data.yml
```

The workflow runs every four hours and can also be triggered manually. It validates the database, refreshes prices, runs all engines, verifies outputs, commits `data/market_ai.db` to `main`, and triggers a Streamlit redeploy.

Cron:

```yaml
cron: "17 */4 * * *"
```

GitHub Actions uses UTC. Repository workflow permissions must allow **Read and write permissions**.

## Streamlit Community Cloud deployment

```text
Repository: ZemaEthio/market-ai-dashboard
Branch: main
Main file path: streamlit_app.py
Python version: 3.12
```

Deployed app:

```text
https://zema-ai-trading-dashboard.streamlit.app
```

## Optional Ollama summaries

```powershell
ollama pull llama3.2:3b
```

```env
USE_OLLAMA=true
OLLAMA_MODEL=llama3.2:3b
OLLAMA_URL=http://localhost:11434
```

Ollama improves summary wording only. Directional scoring and risk decisions remain deterministic.

## SQL Server option

Execute:

```text
app/db/sqlserver_schema.sql
```

Example:

```env
DATABASE_URL=mssql+pyodbc://USER:PASSWORD@SERVER/MarketAI?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

## Security

Do not commit:

```text
.env
.venv/
.streamlit/secrets.toml
API keys
Database passwords
Broker credentials
```

The repository is public, so do not store confidential account or trading data in the committed SQLite database.

## Important limitations

- Yahoo Finance data may be delayed.
- Free RSS and news sources may be incomplete.
- GDELT may rate-limit requests.
- Confidence scores are engineering heuristics, not calibrated profit probabilities.
- Backtests can overfit.
- Slippage, transaction costs, and broker contract specifications require separate modeling.
- Position sizing depends on correct broker-specific value-per-price-unit settings.
- Automatic order execution is intentionally not included.

## Recommended next improvements

- Candlestick chart with EMA overlays
- Data-freshness banner
- BUY, SELL, and WAIT status cards
- Support and resistance overlays
- Confidence and risk gauges
- Economic-calendar integration
- Walk-forward backtesting
- Paper-trading performance tracking
- Signal-change alerts
- Persistent cloud database

## Disclaimer

Use this project at your own risk. It is for educational, research, and paper-trading purposes and does not constitute financial or investment advice.
