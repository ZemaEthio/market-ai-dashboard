from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.repository import (
    get_latest_decision_analysis,
    get_latest_market_analysis,
    save_risk_evaluation,
)
from app.db.session import build_engine, initialize_database, session_factory
from app.engines.risk_engine import RiskPolicy, evaluate_risk


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the deterministic risk engine.")
    parser.add_argument("--symbols", nargs="+", default=["GC=F", "EURUSD=X"])
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--database", default="data/market_ai.db")
    parser.add_argument("--account-balance", type=float, required=True)
    parser.add_argument("--daily-pnl", type=float, default=0.0)
    parser.add_argument("--risk-percent", type=float, default=0.5)
    parser.add_argument("--daily-loss-limit-percent", type=float, default=2.0)
    parser.add_argument("--minimum-reward-risk", type=float, default=2.0)
    parser.add_argument("--maximum-stop-percent", type=float, default=2.0)
    parser.add_argument("--minimum-confidence", type=float, default=0.55)
    parser.add_argument("--maximum-decision-age-hours", type=float, default=2.0)
    parser.add_argument("--event-lockout-minutes", type=int, default=30)
    parser.add_argument("--minutes-to-high-impact-event", type=int)
    parser.add_argument("--value-per-price-unit", type=float, default=1.0)
    parser.add_argument("--maximum-position-units", type=float)
    parser.add_argument("--entry-price", type=float)
    parser.add_argument("--stop-price", type=float)
    parser.add_argument("--target-price", type=float)
    parser.add_argument("--allow-limited-data", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_path = Path(args.database).resolve()
    engine = build_engine(f"sqlite:///{database_path.as_posix()}")
    initialize_database(engine)
    Session = session_factory(engine)

    policy = RiskPolicy(
        risk_percent=args.risk_percent,
        daily_loss_limit_percent=args.daily_loss_limit_percent,
        minimum_reward_risk=args.minimum_reward_risk,
        maximum_stop_percent=args.maximum_stop_percent,
        minimum_decision_confidence=args.minimum_confidence,
        maximum_decision_age_hours=args.maximum_decision_age_hours,
        high_impact_lockout_minutes=args.event_lockout_minutes,
        maximum_position_units=args.maximum_position_units,
        require_good_data_quality=not args.allow_limited_data,
    )

    results: list[dict] = []
    with Session() as session:
        for symbol in args.symbols:
            try:
                decision = get_latest_decision_analysis(session, symbol, args.interval)
                market = get_latest_market_analysis(session, symbol, args.interval)
                evaluation = evaluate_risk(
                    decision,
                    market,
                    account_balance=args.account_balance,
                    daily_pnl=args.daily_pnl,
                    entry_price=args.entry_price,
                    stop_price=args.stop_price,
                    target_price=args.target_price,
                    value_per_price_unit=args.value_per_price_unit,
                    minutes_to_high_impact_event=args.minutes_to_high_impact_event,
                    policy=policy,
                )
                result = evaluation.to_dict()
                if not args.no_save:
                    result["risk_evaluation_id"] = save_risk_evaluation(session, evaluation)
                result["run_status"] = "success"
            except Exception as exc:
                result = {"symbol": symbol, "interval": args.interval, "run_status": "error", "error": str(exc)}
            results.append(result)

    print(json.dumps(results, indent=2))
    return 0 if all(item["run_status"] == "success" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
