from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.repository import load_price_candles, save_market_analysis
from app.db.session import build_engine, initialize_database, session_factory
from app.engines.market_engine import analyze_market


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Engine 1 market analysis from stored candles.")
    parser.add_argument("--symbols", nargs="+", default=["GC=F", "EURUSD=X"])
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--database", default="data/market_ai.db")
    parser.add_argument("--no-save", action="store_true", help="Calculate without saving results.")
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
                candles = load_price_candles(session, symbol, args.interval, args.limit)
                analysis = analyze_market(candles, symbol, args.interval)
                result = analysis.to_dict()
                if not args.no_save:
                    result["analysis_id"] = save_market_analysis(session, analysis)
                result["candles_used"] = len(candles)
                result["status"] = "success"
            except Exception as exc:
                result = {"symbol": symbol, "interval": args.interval, "status": "error", "error": str(exc)}
            results.append(result)

    print(json.dumps(results, indent=2))
    return 0 if all(item["status"] == "success" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
