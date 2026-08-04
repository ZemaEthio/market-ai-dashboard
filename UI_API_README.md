# Streamlit Dashboard and FastAPI Service

This patch adds a read-only presentation layer over the existing SQLite database.
It does not modify or delete engine records and contains no `.db` files.

## Run the API

```powershell
Set-Location E:\MarketAI
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.api.main:app --reload
```

Open API documentation at `http://127.0.0.1:8000/docs`.

## Run the dashboard

In another PowerShell window:

```powershell
Set-Location E:\MarketAI
.\.venv\Scripts\Activate.ps1
python -m streamlit run app\ui\dashboard.py
```

Open `http://localhost:8501`.

## API endpoints

- `GET /health`
- `GET /symbols`
- `GET /candles/{symbol}?interval=1h&limit=300`
- `GET /market/{symbol}?interval=1h`
- `GET /news/{symbol}`
- `GET /decision/{symbol}?interval=1h`
- `GET /risk/{symbol}?interval=1h`
- `GET /news-articles?limit=50`
- `GET /latest/{symbol}?interval=1h&candle_limit=300`
