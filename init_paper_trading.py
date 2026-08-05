from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS paper_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    starting_balance REAL NOT NULL CHECK (starting_balance > 0),
    current_balance REAL NOT NULL CHECK (current_balance >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('BUY', 'SELL')),
    status TEXT NOT NULL DEFAULT 'PLANNED'
        CHECK (status IN ('PLANNED', 'OPEN', 'CLOSED', 'CANCELLED')),
    timeframe TEXT NOT NULL,
    setup_name TEXT,
    market_regime TEXT,
    entry_price REAL NOT NULL CHECK (entry_price > 0),
    stop_price REAL NOT NULL CHECK (stop_price > 0),
    target_price REAL NOT NULL CHECK (target_price > 0),
    risk_percent REAL NOT NULL CHECK (risk_percent > 0),
    risk_amount REAL NOT NULL CHECK (risk_amount >= 0),
    units REAL NOT NULL CHECK (units >= 0),
    reward_risk_ratio REAL NOT NULL,
    planned_at_utc TEXT NOT NULL,
    opened_at_utc TEXT,
    closed_at_utc TEXT,
    exit_price REAL,
    gross_pnl REAL,
    costs REAL NOT NULL DEFAULT 0,
    net_pnl REAL,
    r_multiple REAL,
    confidence REAL,
    thesis TEXT,
    invalidation TEXT,
    pre_trade_checklist TEXT,
    lessons TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_paper_trades_account_status
    ON paper_trades(account_id, status);
CREATE INDEX IF NOT EXISTS idx_paper_trades_symbol
    ON paper_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_paper_trades_planned_at
    ON paper_trades(planned_at_utc);
"""

def initialize(database_path: Path) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"Database file not found: {database_path}")
    with sqlite3.connect(database_path) as connection:
        connection.executescript(SCHEMA)
        connection.commit()
    print("Paper-trading schema is ready.")
    print("  - paper_accounts")
    print("  - paper_trades")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/market_ai.db")
    args = parser.parse_args()
    initialize(Path(args.database).resolve())

if __name__ == "__main__":
    main()
