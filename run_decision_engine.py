from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.repository import (
    get_latest_market_analysis,
    get_latest_news_analysis,
    save_decision_analysis,
)
from app.db.session import build_engine, initialize_database, session_factory
from app.engines.decision_engine import combine_analyses


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Engine 3 decision analysis.")
    parser.add_argument("--symbols", nargs="+", default=["GC=F", "EURUSD=X"])
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--database", default="data/market_ai.db")
    parser.add_argument("--no-save", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_path = Path(args.database).resolve()
    engine = build_engine(f"sqlite:///{database_path.as_posix()}")
    initialize_database(engine)
    Session = session_factory(engine)

    results: list[dict] = []
    with Session() as session:
        for symbol in args.symbols:
            try:
                market = get_latest_market_analysis(session, symbol, args.interval)
                news = get_latest_news_analysis(session, symbol)
                decision = combine_analyses(market, news)
                result = decision.to_dict()
                if not args.no_save:
                    result["decision_id"] = save_decision_analysis(session, decision)
                result["status"] = "success"
            except Exception as exc:
                result = {"symbol": symbol, "interval": args.interval, "status": "error", "error": str(exc)}
            results.append(result)

    print(json.dumps(results, indent=2))
    return 0 if all(item["status"] == "success" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
