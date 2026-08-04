from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.collectors.market import fetch_prices
from app.config import DATABASE_URL, INTERVAL, PERIOD, SYMBOL
from app.db.repository import (
    begin_collection_run,
    finish_collection_run,
    get_data_summary,
    upsert_price_candles,
)
from app.db.session import build_engine, initialize_database, session_factory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the market database and collect OHLC data.")
    parser.add_argument("--symbols", nargs="+", default=[SYMBOL], help="Yahoo symbols, e.g. GC=F EURUSD=X")
    parser.add_argument("--period", default=PERIOD, help="Yahoo period, e.g. 6mo, 1y")
    parser.add_argument("--interval", default=INTERVAL, help="Yahoo interval, e.g. 1h, 1d")
    parser.add_argument("--database-url", default=DATABASE_URL, help="SQLAlchemy database URL")
    return parser.parse_args()


def collect_symbol(symbol: str, period: str, interval: str, database_url: str) -> dict:
    engine = build_engine(database_url)
    initialize_database(engine)
    SessionLocal = session_factory(engine)

    with SessionLocal() as session:
        run = begin_collection_run(session, symbol, interval, period)
        try:
            prices = fetch_prices(symbol, period=period, interval=interval)
            rows_received = len(prices)
            rows_written = upsert_price_candles(session, prices, symbol, interval)
            summary = get_data_summary(session, symbol, interval)
            finish_collection_run(
                session,
                run,
                status="success",
                rows_received=rows_received,
                rows_written=rows_written,
                duplicate_rows=0,
                invalid_rows=0,
                earliest_timestamp_utc=prices.index.min().to_pydatetime(),
                latest_timestamp_utc=prices.index.max().to_pydatetime(),
            )
            return {"symbol": symbol, "status": "success", "written": rows_written, **summary}
        except Exception as exc:
            session.rollback()
            finish_collection_run(session, run, status="failed", error_message=str(exc))
            return {"symbol": symbol, "status": "failed", "error": str(exc)}


def main() -> int:
    args = parse_args()
    if args.database_url.startswith("sqlite:///"):
        db_path = Path(args.database_url.removeprefix("sqlite:///"))
        if db_path.parent != Path("."):
            db_path.parent.mkdir(parents=True, exist_ok=True)

    results = [collect_symbol(symbol, args.period, args.interval, args.database_url) for symbol in args.symbols]
    print(json.dumps(results, indent=2, default=str))
    return 0 if all(result["status"] == "success" for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
