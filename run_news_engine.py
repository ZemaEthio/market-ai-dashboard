from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.collectors.news import collect_news
from app.db.repository import save_news_analysis, upsert_news_articles
from app.db.session import build_engine, initialize_database, session_factory
from app.engines.news_engine import analyze_news


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Engine 2 news and macro analysis.")
    parser.add_argument("--symbols", nargs="+", default=["GC=F", "EURUSD=X"])
    parser.add_argument("--lookback-hours", type=int, default=72)
    parser.add_argument("--max-per-feed", type=int, default=30)
    parser.add_argument("--gdelt-max-records", type=int, default=100)
    parser.add_argument("--database", default="data/market_ai.db")
    parser.add_argument("--no-gdelt", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--ollama", action="store_true", help="Use local Ollama for the final summary only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_path = Path(args.database).resolve()
    engine = build_engine(f"sqlite:///{database_path.as_posix()}")
    initialize_database(engine)
    Session = session_factory(engine)

    articles, collection_errors = collect_news(
        args.symbols,
        max_per_feed=args.max_per_feed,
        gdelt_max_records=args.gdelt_max_records,
        lookback_hours=args.lookback_hours,
        include_gdelt=not args.no_gdelt,
    )

    results: list[dict] = []
    with Session() as session:
        articles_written = 0 if args.no_save else upsert_news_articles(session, articles)
        for symbol in args.symbols:
            try:
                analysis = analyze_news(articles, symbol, use_ollama=args.ollama)
                result = analysis.to_dict()
                result["status"] = "success"
                result["articles_collected"] = len(articles)
                result["articles_written"] = articles_written
                result["collection_errors"] = collection_errors
                if not args.no_save:
                    result["analysis_id"] = save_news_analysis(session, analysis)
            except Exception as exc:
                result = {"symbol": symbol, "status": "error", "error": str(exc), "collection_errors": collection_errors}
            results.append(result)

    print(json.dumps(results, indent=2))
    return 0 if all(item["status"] == "success" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
