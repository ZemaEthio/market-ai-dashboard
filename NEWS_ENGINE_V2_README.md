# ZEMA News Engine v2

This patch upgrades Engine 2 into an instrument-aware market-impact engine.

## What changed

- Expanded official feeds: Fed, ECB, Bank of England, BIS, U.S. Treasury, BLS CPI, and BLS employment.
- Instrument-specific GDELT searches for Gold, EUR/USD, and GBP/USD.
- Event categories: central bank, inflation, employment, growth, rates/credit, geopolitics, energy/commodities, and currency.
- Relevance scoring separates trustworthy sources from actually relevant stories.
- Directional scoring is instrument-specific.
- Freshness decay reduces the influence of old headlines.
- Duplicate-event capping prevents syndicated copies from dominating the result.
- Confidence now considers coverage, source diversity, event diversity, official-source share, directional agreement, and score strength.
- Stored driver JSON now includes category, freshness, and event key.

## Install

Extract this package, then copy its contents over the matching files in `E:\MarketAI`.

From PowerShell:

```powershell
Set-Location "E:\MarketAI"
Copy-Item "<EXTRACTED_FOLDER>\app\collectors\news.py" ".\app\collectors\news.py" -Force
Copy-Item "<EXTRACTED_FOLDER>\app\engines\news_engine.py" ".\app\engines\news_engine.py" -Force
Copy-Item "<EXTRACTED_FOLDER>\app\db\repository.py" ".\app\db\repository.py" -Force
Copy-Item "<EXTRACTED_FOLDER>\run_news_engine.py" ".\run_news_engine.py" -Force
```

No database migration is required.

## Test

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q .\tests\test_news_engine_v2.py
python .\run_news_engine.py --symbols GC=F EURUSD=X --lookback-hours 72
```

Then rerun the downstream engines:

```powershell
python .\run_decision_engine.py
python .\run_risk_engine.py
python -m streamlit run .\streamlit_app.py --server.port 8501
```

## Git

```powershell
git add app/collectors/news.py app/engines/news_engine.py app/db/repository.py run_news_engine.py tests/test_news_engine_v2.py
git commit -m "Upgrade instrument-aware market news engine"
git pull --rebase --autostash origin main
git push origin main
```

Do not force-push. If `data/market_ai.db` changes while remote automation is also updating it, resolve the binary conflict by keeping the remote database and rerunning the news, decision, and risk engines.
