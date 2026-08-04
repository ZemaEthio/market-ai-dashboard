from __future__ import annotations

import argparse
import sqlite3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/market_ai.db")
    args = parser.parse_args()
    with sqlite3.connect(args.database) as connection:
        candles = connection.execute(
            """
            SELECT symbol, interval, COUNT(*) AS rows,
                   MIN(timestamp_utc) AS earliest_utc,
                   MAX(timestamp_utc) AS latest_utc
            FROM price_candles
            GROUP BY symbol, interval
            ORDER BY symbol, interval
            """
        ).fetchall()
        runs = connection.execute(
            """
            SELECT id, symbol, interval, period, status, rows_received,
                   rows_written, started_at_utc, completed_at_utc, error_message
            FROM collection_runs
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()
    print("PRICE DATA")
    print(candles or "No candles collected yet.")
    print("\nLATEST COLLECTION RUNS")
    print(runs or "No collection runs yet.")


if __name__ == "__main__":
    main()
