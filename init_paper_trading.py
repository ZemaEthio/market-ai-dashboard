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
    status TEXT NOT NULL DEFAULT 'PLANNED' CHECK (status IN ('PLANNED','OPEN','CLOSED','CANCELLED')),
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
    decision_analysis_id INTEGER,
    risk_evaluation_id INTEGER,
    evidence_snapshot_json TEXT,
    education_lesson TEXT,
    quiz_score REAL,
    readiness_score REAL,
    user_market_view TEXT,
    engine_market_view TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    FOREIGN KEY (account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS education_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    lesson_key TEXT NOT NULL,
    lesson_title TEXT NOT NULL,
    score REAL NOT NULL,
    passed INTEGER NOT NULL,
    answers_json TEXT NOT NULL,
    completed_at_utc TEXT NOT NULL,
    UNIQUE(account_id, lesson_key),
    FOREIGN KEY (account_id) REFERENCES paper_accounts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_paper_trades_account_status ON paper_trades(account_id,status);
CREATE INDEX IF NOT EXISTS idx_paper_trades_symbol ON paper_trades(symbol);

CREATE INDEX IF NOT EXISTS idx_education_account ON education_progress(account_id,passed);
"""

MIGRATION_COLUMNS = {
    "decision_analysis_id": "INTEGER",
    "risk_evaluation_id": "INTEGER",
    "evidence_snapshot_json": "TEXT",
    "education_lesson": "TEXT",
    "quiz_score": "REAL",
    "readiness_score": "REAL",
    "user_market_view": "TEXT",
    "engine_market_view": "TEXT",
}

def initialize(database_path: Path) -> None:
    if not database_path.exists():
        raise FileNotFoundError(f"Database file not found: {database_path}")
    with sqlite3.connect(database_path) as connection:
        connection.executescript(SCHEMA)
        existing = {row[1] for row in connection.execute("PRAGMA table_info(paper_trades)")}
        for name, sql_type in MIGRATION_COLUMNS.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE paper_trades ADD COLUMN {name} {sql_type}")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_trades_decision "
            "ON paper_trades(decision_analysis_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_paper_trades_decision "
            "ON paper_trades(decision_analysis_id)"
        )
        connection.commit()
    print("Paper-trading and education schema is ready.")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/market_ai.db")
    args = parser.parse_args()
    initialize(Path(args.database).resolve())

if __name__ == "__main__":
    main()


