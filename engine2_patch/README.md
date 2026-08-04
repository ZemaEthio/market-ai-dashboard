# Zero-Cost Gold & Forex Market AI

A decision-support MVP with three engines:
1. Technical/market engine (deterministic indicators)
2. News/macro engine (official RSS + GDELT; optional local Ollama)
3. Decision/explanation engine
Plus a deterministic risk engine.

## Zero-cost sources
- Price research data: Yahoo Finance via yfinance (`GC=F`, `EURUSD=X`, `GBPUSD=X`, etc.). Delayed/unofficial; check terms before redistribution.
- News: Federal Reserve, ECB and Bank of England RSS; GDELT DOC API.
- Macro extension: BLS Public Data API v1 (no registration) and public central-bank releases.
- Local language model: Ollama with `llama3.2:3b` or another local model. Optional.

## Run
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app/ui/dashboard.py
```
API:
```bash
uvicorn app.api.main:app --reload
```
Open `http://127.0.0.1:8000/docs`.

## Symbols
- Gold futures proxy: `GC=F`
- EUR/USD: `EURUSD=X`
- GBP/USD: `GBPUSD=X`
- USD/JPY: `JPY=X`

## SQL Server
Change `DATABASE_URL` in `.env` to the SQL Server example. The MVP currently runs without persistence; add SQLAlchemy models/migrations as the next production step.

## Important limitations
This is research and decision support, not financial advice. Free sources can be delayed, rate-limited, incomplete, or governed by terms that prohibit commercial redistribution. Do not enable automatic execution until walk-forward testing, transaction-cost modelling, paper trading, monitoring, and kill switches are complete.

## Create the database and collect price data

The package includes a pre-created SQLite database at `data/market_ai.db`. To recreate it and download six months of hourly gold and forex candles:

```bash
python collect_data.py --symbols "GC=F" "EURUSD=X" --period 6mo --interval 1h
```

The command is idempotent: matching symbol/interval/timestamp rows are replaced rather than duplicated. All timestamps are normalized to UTC, invalid OHLC rows are rejected, and each attempt is recorded in `collection_runs`.

Check the stored data:

```bash
python inspect_database.py
```

For SQL Server, execute `app/db/sqlserver_schema.sql`, install Microsoft's ODBC Driver 18, and set a SQLAlchemy URL such as:

```env
DATABASE_URL=mssql+pyodbc://USER:PASSWORD@SERVER/DATABASE?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

Then run `collect_data.py` with the same arguments.

## Engine 1: technical market analysis

Run Engine 1 against candles already stored in SQLite:

```powershell
python run_market_engine.py --symbols "GC=F" "EURUSD=X" --interval 1h
```

The command calculates EMA20, EMA50, EMA200, Wilder RSI14, Wilder ATR14, trend, market regime, support/resistance, bias, confidence and invalidation. Results are stored in `market_analyses`.

Inspect saved results:

```powershell
python inspect_market_analysis.py
```

Run without persistence:

```powershell
python run_market_engine.py --symbols "GC=F" --interval 1h --no-save
```

## Engine 2: news and macro analysis

Collect official Federal Reserve, ECB and Bank of England RSS items plus recent GDELT-indexed reporting, then score the likely impact separately for gold and EUR/USD:

```powershell
python run_news_engine.py --symbols "GC=F" "EURUSD=X" --lookback-hours 48
```

Inspect stored articles and analyses:

```powershell
python inspect_news_analysis.py
```

Run official feeds only if GDELT is unavailable:

```powershell
python run_news_engine.py --symbols "GC=F" "EURUSD=X" --lookback-hours 168 --no-gdelt
```

Use a local Ollama model only for wording the final summary; deterministic scoring remains the source of the bias and confidence:

```powershell
python run_news_engine.py --symbols "GC=F" "EURUSD=X" --ollama
```

Engine 2 creates `news_articles` and `news_analyses`. Raw articles are deduplicated by canonical URL and normalized title. Each analysis stores source coverage, relevance, high-impact count, directional score, confidence, top drivers, warnings, model name and data-quality status.
