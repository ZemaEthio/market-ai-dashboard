from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


SCHEMA = '''
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS backtest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    start_timestamp_utc TEXT NOT NULL,
    end_timestamp_utc TEXT NOT NULL,
    initial_capital REAL NOT NULL,
    spread_bps REAL NOT NULL DEFAULT 0,
    slippage_bps REAL NOT NULL DEFAULT 0,
    model_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS backtest_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_run_id INTEGER NOT NULL,
    decision_timestamp_utc TEXT NOT NULL,
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    direction TEXT NOT NULL,
    confidence REAL,
    market_regime TEXT,
    entry_price REAL NOT NULL,
    stop_price REAL NOT NULL,
    target_price REAL NOT NULL,
    exit_price REAL,
    exit_timestamp_utc TEXT,
    exit_reason TEXT,
    pnl_amount REAL,
    pnl_percent REAL,
    r_multiple REAL,
    maximum_favorable_excursion REAL,
    maximum_adverse_excursion REAL,
    holding_hours REAL,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (backtest_run_id) REFERENCES backtest_runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS backtest_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_run_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    segment_name TEXT,
    segment_value TEXT,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (backtest_run_id) REFERENCES backtest_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_symbol_interval
    ON backtest_runs(symbol, interval);

CREATE INDEX IF NOT EXISTS idx_backtest_trades_run_id
    ON backtest_trades(backtest_run_id);

CREATE INDEX IF NOT EXISTS idx_backtest_trades_decision_time
    ON backtest_trades(decision_timestamp_utc);

CREATE INDEX IF NOT EXISTS idx_backtest_metrics_run_id
    ON backtest_metrics(backtest_run_id);
'''


def initialize_backtesting_schema(database_path: Path) -> None:
    if not database_path.parent.exists():
        raise FileNotFoundError(
            f"Database directory does not exist: {database_path.parent}"
        )

    with sqlite3.connect(database_path) as connection:
        connection.executescript(SCHEMA)
        connection.commit()

        rows = connection.execute(
            '''
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name IN (
                  'backtest_runs',
                  'backtest_trades',
                  'backtest_metrics'
              )
            ORDER BY name
            '''
        ).fetchall()

    created = [row[0] for row in rows]

    if len(created) != 3:
        raise RuntimeError(
            "Backtesting schema validation failed. "
            f"Expected 3 tables, found: {created}"
        )

    print("Backtesting schema is ready.")
    for table in created:
        print(f"  - {table}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the Market AI backtesting tables."
    )
    parser.add_argument(
        "--database",
        default="data/market_ai.db",
        help="Path to the SQLite database.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_path = Path(args.database).resolve()

    if not database_path.exists():
        raise FileNotFoundError(f"Database file not found: {database_path}")

    initialize_backtesting_schema(database_path)


if __name__ == "__main__":
    main()
