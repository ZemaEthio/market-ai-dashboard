from __future__ import annotations

import argparse
import sqlite3


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect saved Engine 3 decisions.")
    parser.add_argument("--database", default="data/market_ai.db")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    connection = sqlite3.connect(args.database)
    rows = connection.execute(
        """
        SELECT id, symbol, interval, decided_at_utc, combined_bias,
               preferred_action, ROUND(confidence, 4), alignment,
               risk_level, data_quality, summary
        FROM decision_analyses
        ORDER BY id DESC
        LIMIT ?
        """,
        (args.limit,),
    ).fetchall()
    connection.close()

    print("LATEST ENGINE 3 DECISIONS")
    if not rows:
        print("No decisions saved yet.")
    else:
        for row in rows:
            print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
