from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.services.read_model import (
    candles,
    health,
    latest_bundle,
    latest_decision,
    latest_market,
    latest_news,
    latest_risk,
    list_symbols,
    recent_news_articles,
)

DATABASE_PATH = Path(os.getenv("MARKET_AI_DATABASE", "data/market_ai.db"))

app = FastAPI(
    title="Market AI Decision Support API",
    version="1.0.0",
    description="Read-only API for persisted Market AI engine results.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def call_reader(function, *args, **kwargs) -> Any:
    try:
        return function(*args, database_path=DATABASE_PATH, **kwargs)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database read failed: {exc}") from exc


@app.get("/health", tags=["system"])
def get_health() -> dict[str, Any]:
    return call_reader(health)


@app.get("/symbols", tags=["market"])
def get_symbols() -> list[dict[str, Any]]:
    return call_reader(list_symbols)


@app.get("/candles/{symbol}", tags=["market"])
def get_candles(
    symbol: str,
    interval: str = Query("1h"),
    limit: int = Query(300, ge=1, le=5000),
) -> list[dict[str, Any]]:
    return call_reader(candles, symbol, interval, limit)


@app.get("/market/{symbol}", tags=["engines"])
def get_market(symbol: str, interval: str = Query("1h")) -> dict[str, Any] | None:
    return call_reader(latest_market, symbol, interval)


@app.get("/news/{symbol}", tags=["engines"])
def get_news(symbol: str) -> dict[str, Any] | None:
    return call_reader(latest_news, symbol)


@app.get("/decision/{symbol}", tags=["engines"])
def get_decision(symbol: str, interval: str = Query("1h")) -> dict[str, Any] | None:
    return call_reader(latest_decision, symbol, interval)


@app.get("/risk/{symbol}", tags=["engines"])
def get_risk(symbol: str, interval: str = Query("1h")) -> dict[str, Any] | None:
    return call_reader(latest_risk, symbol, interval)


@app.get("/news-articles", tags=["news"])
def get_news_articles(limit: int = Query(50, ge=1, le=500)) -> list[dict[str, Any]]:
    return call_reader(recent_news_articles, limit)


@app.get("/latest/{symbol}", tags=["dashboard"])
def get_latest(
    symbol: str,
    interval: str = Query("1h"),
    candle_limit: int = Query(300, ge=1, le=5000),
) -> dict[str, Any]:
    return call_reader(latest_bundle, symbol, interval, candle_limit)
