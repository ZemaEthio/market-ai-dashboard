from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DEFAULT_DATABASE = Path("data/market_ai.db")


@contextmanager
def connect(database_path: str | Path = DEFAULT_DATABASE) -> Iterator[sqlite3.Connection]:
    path = Path(database_path)
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path.resolve()}")
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _decode_json(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _row_to_dict(row: sqlite3.Row | None, json_fields: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for field, default in (json_fields or {}).items():
        result[field.removesuffix("_json")] = _decode_json(result.pop(field, None), default)
    return result


def health(database_path: str | Path = DEFAULT_DATABASE) -> dict[str, Any]:
    with connect(database_path) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
    return {
        "status": "ok" if integrity == "ok" else "degraded",
        "database": str(Path(database_path)),
        "integrity": integrity,
        "tables": tables,
    }


def list_symbols(database_path: str | Path = DEFAULT_DATABASE) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        if not _table_exists(connection, "price_candles"):
            return []
        rows = connection.execute(
            """
            SELECT symbol, interval, COUNT(*) AS candle_count,
                   MIN(timestamp_utc) AS first_candle_utc,
                   MAX(timestamp_utc) AS last_candle_utc
            FROM price_candles
            GROUP BY symbol, interval
            ORDER BY symbol, interval
            """
        ).fetchall()
    return [dict(row) for row in rows]


def candles(
    symbol: str,
    interval: str = "1h",
    limit: int = 500,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 5000))
    with connect(database_path) as connection:
        if not _table_exists(connection, "price_candles"):
            return []
        rows = connection.execute(
            """
            SELECT timestamp_utc, open, high, low, close, volume
            FROM price_candles
            WHERE symbol=? AND interval=?
            ORDER BY timestamp_utc DESC
            LIMIT ?
            """,
            (symbol, interval, safe_limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def latest_market(symbol: str, interval: str = "1h", database_path: str | Path = DEFAULT_DATABASE) -> dict[str, Any] | None:
    with connect(database_path) as connection:
        if not _table_exists(connection, "market_analyses"):
            return None
        row = connection.execute(
            """
            SELECT * FROM market_analyses
            WHERE symbol=? AND interval=?
            ORDER BY analyzed_at_utc DESC, id DESC
            LIMIT 1
            """,
            (symbol, interval),
        ).fetchone()
    return _row_to_dict(
        row,
        {
            "support_levels_json": [],
            "resistance_levels_json": [],
            "reasons_json": [],
        },
    )


def latest_news(symbol: str, database_path: str | Path = DEFAULT_DATABASE) -> dict[str, Any] | None:
    with connect(database_path) as connection:
        if not _table_exists(connection, "news_analyses"):
            return None
        row = connection.execute(
            """
            SELECT * FROM news_analyses
            WHERE symbol=?
            ORDER BY analyzed_at_utc DESC, id DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()
    return _row_to_dict(row, {"drivers_json": [], "warnings_json": []})


def latest_decision(symbol: str, interval: str = "1h", database_path: str | Path = DEFAULT_DATABASE) -> dict[str, Any] | None:
    with connect(database_path) as connection:
        if not _table_exists(connection, "decision_analyses"):
            return None
        row = connection.execute(
            """
            SELECT * FROM decision_analyses
            WHERE symbol=? AND interval=?
            ORDER BY decided_at_utc DESC, id DESC
            LIMIT 1
            """,
            (symbol, interval),
        ).fetchone()
    return _row_to_dict(
        row,
        {
            "bullish_scenario_json": {},
            "bearish_scenario_json": {},
            "neutral_scenario_json": {},
            "no_trade_reasons_json": [],
            "reasons_json": [],
        },
    )


def latest_risk(symbol: str, interval: str = "1h", database_path: str | Path = DEFAULT_DATABASE) -> dict[str, Any] | None:
    with connect(database_path) as connection:
        if not _table_exists(connection, "risk_evaluations"):
            return None
        row = connection.execute(
            """
            SELECT * FROM risk_evaluations
            WHERE symbol=? AND interval=?
            ORDER BY evaluated_at_utc DESC, id DESC
            LIMIT 1
            """,
            (symbol, interval),
        ).fetchone()
    result = _row_to_dict(row, {"rejection_reasons_json": [], "checks_json": {}})
    if result is not None:
        result["approved"] = bool(result.get("approved"))
    return result


def recent_news_articles(limit: int = 50, database_path: str | Path = DEFAULT_DATABASE) -> list[dict[str, Any]]:
    safe_limit = max(1, min(limit, 500))
    with connect(database_path) as connection:
        if not _table_exists(connection, "news_articles"):
            return []
        rows = connection.execute(
            """
            SELECT id, title, url, source, source_type, published_at_utc,
                   summary, reliability
            FROM news_articles
            ORDER BY published_at_utc DESC, id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def latest_bundle(symbol: str, interval: str = "1h", candle_limit: int = 300, database_path: str | Path = DEFAULT_DATABASE) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "interval": interval,
        "market": latest_market(symbol, interval, database_path),
        "news": latest_news(symbol, database_path),
        "decision": latest_decision(symbol, interval, database_path),
        "risk": latest_risk(symbol, interval, database_path),
        "candles": candles(symbol, interval, candle_limit, database_path),
    }
