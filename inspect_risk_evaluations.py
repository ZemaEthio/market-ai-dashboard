from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect saved risk evaluations.")
    parser.add_argument("--database", default="data/market_ai.db")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    path = Path(args.database)
    if not path.exists():
        print(f"Database not found: {path.resolve()}")
        return 1

    conn = sqlite3.connect(path)
    try:
        table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='risk_evaluations'").fetchone()
        if not table:
            print("No risk_evaluations table yet. Run run_risk_engine.py first.")
            return 0
        rows = conn.execute(
            """
            SELECT id, symbol, interval, evaluated_at_utc, status, direction,
                   account_balance, maximum_loss_amount, entry_price, stop_price,
                   target_price, reward_risk_ratio, position_units,
                   decision_age_hours, data_quality, rejection_reasons_json
            FROM risk_evaluations
            ORDER BY id DESC
            LIMIT ?
            """,
            (args.limit,),
        ).fetchall()
        print("LATEST RISK EVALUATIONS")
        for row in rows:
            print(row)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
