from __future__ import annotations

import argparse
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument("--database", default="data/market_ai.db")
args = parser.parse_args()

with sqlite3.connect(args.database) as connection:
    rows = connection.execute(
        """
        SELECT id, symbol, interval, candle_timestamp_utc, last_price,
               trend, market_regime, bias, ROUND(confidence, 4),
               ROUND(rsi14, 2), ROUND(atr14, 5), data_quality
        FROM market_analyses
        ORDER BY id DESC
        LIMIT 20
        """
    ).fetchall()

print("LATEST ENGINE 1 ANALYSES")
for row in rows:
    print(row)
if not rows:
    print("No market analyses yet.")
