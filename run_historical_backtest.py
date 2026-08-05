from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable


DEFAULT_DATABASE = Path("data/market_ai.db")


@dataclass(frozen=True)
class Candle:
    timestamp: str
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Decision:
    timestamp: str
    action: str
    confidence: float | None
    market_regime: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class SimulatedTrade:
    decision_timestamp: str
    direction: str
    confidence: float | None
    market_regime: str | None
    entry_price: float
    stop_price: float
    target_price: float
    exit_price: float
    exit_timestamp: str
    exit_reason: str
    pnl_amount: float
    pnl_percent: float
    r_multiple: float
    maximum_favorable_excursion: float
    maximum_adverse_excursion: float
    holding_hours: float


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        is not None
    )


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    }


def first_value(record: dict[str, Any], names: Iterable[str]) -> Any:
    for name in names:
        value = record.get(name)
        if value not in (None, ""):
            return value
    return None


def as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def normalize_action(value: Any) -> str:
    text = str(value or "").strip().upper()
    if any(token in text for token in ("BUY", "LONG", "BULL")):
        return "BUY"
    if any(token in text for token in ("SELL", "SHORT", "BEAR")):
        return "SELL"
    return "WAIT"


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def require_schema(connection: sqlite3.Connection) -> None:
    required = {
        "price_candles",
        "decision_analyses",
        "backtest_runs",
        "backtest_trades",
        "backtest_metrics",
    }
    missing = sorted(table for table in required if not table_exists(connection, table))
    if missing:
        raise RuntimeError(
            "Required tables are missing: "
            + ", ".join(missing)
            + ". Run init_backtesting.py first."
        )


def resolve_column(
    columns: set[str],
    candidates: Iterable[str],
    *,
    required: bool = False,
    label: str = "column",
) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    if required:
        raise RuntimeError(
            f"Could not find {label}. Tried: {', '.join(candidates)}. "
            f"Available: {', '.join(sorted(columns))}"
        )
    return None


def load_candles(
    connection: sqlite3.Connection,
    symbol: str,
    interval: str,
    start: str | None,
    end: str | None,
) -> list[Candle]:
    columns = table_columns(connection, "price_candles")
    timestamp_col = resolve_column(
        columns,
        ("timestamp_utc", "timestamp", "datetime_utc"),
        required=True,
        label="price timestamp column",
    )

    clauses = ["symbol = ?", "interval = ?"]
    params: list[Any] = [symbol, interval]

    if start:
        clauses.append(f"{quote_identifier(timestamp_col)} >= ?")
        params.append(start)
    if end:
        clauses.append(f"{quote_identifier(timestamp_col)} <= ?")
        params.append(end)

    query = f"""
        SELECT
            {quote_identifier(timestamp_col)} AS timestamp_utc,
            open,
            high,
            low,
            close
        FROM price_candles
        WHERE {' AND '.join(clauses)}
        ORDER BY {quote_identifier(timestamp_col)}
    """
    rows = connection.execute(query, params).fetchall()

    return [
        Candle(
            timestamp=str(row["timestamp_utc"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
        )
        for row in rows
    ]


def load_decisions(
    connection: sqlite3.Connection,
    symbol: str,
    interval: str,
    start: str | None,
    end: str | None,
    minimum_confidence: float,
) -> list[Decision]:
    columns = table_columns(connection, "decision_analyses")

    timestamp_col = resolve_column(
        columns,
        ("decided_at_utc", "analyzed_at_utc", "created_at_utc", "timestamp_utc"),
        required=True,
        label="decision timestamp column",
    )
    action_col = resolve_column(
        columns,
        ("preferred_action", "action", "recommended_action", "decision", "signal"),
        required=True,
        label="decision action column",
    )
    confidence_col = resolve_column(
        columns,
        ("confidence", "decision_confidence", "combined_confidence"),
    )
    regime_col = resolve_column(
        columns,
        ("market_regime", "regime"),
    )

    clauses = ["symbol = ?"]
    params: list[Any] = [symbol]

    if "interval" in columns:
        clauses.append("interval = ?")
        params.append(interval)
    if start:
        clauses.append(f"{quote_identifier(timestamp_col)} >= ?")
        params.append(start)
    if end:
        clauses.append(f"{quote_identifier(timestamp_col)} <= ?")
        params.append(end)

    rows = connection.execute(
        f"""
        SELECT *
        FROM decision_analyses
        WHERE {' AND '.join(clauses)}
        ORDER BY {quote_identifier(timestamp_col)}, id
        """,
        params,
    ).fetchall()

    decisions: list[Decision] = []
    for row in rows:
        raw = dict(row)
        action = normalize_action(raw.get(action_col))
        confidence = as_float(raw.get(confidence_col)) if confidence_col else None

        if action == "WAIT":
            continue
        if confidence is not None and confidence < minimum_confidence:
            continue

        decisions.append(
            Decision(
                timestamp=str(raw[timestamp_col]),
                action=action,
                confidence=confidence,
                market_regime=(
                    str(raw.get(regime_col))
                    if regime_col and raw.get(regime_col) not in (None, "")
                    else None
                ),
                raw=raw,
            )
        )

    return decisions


def nearest_next_candle_index(candles: list[Candle], timestamp: str) -> int | None:
    for index, candle in enumerate(candles):
        if candle.timestamp > timestamp:
            return index
    return None


def infer_stop_target(
    decision: Decision,
    direction: str,
    entry: float,
    candles: list[Candle],
    entry_index: int,
    stop_atr_multiple: float,
    reward_risk: float,
) -> tuple[float, float]:
    raw = decision.raw

    explicit_stop = as_float(
        first_value(
            raw,
            (
                "stop_price",
                "stop_loss",
                "suggested_stop",
                "recommended_stop",
            ),
        )
    )
    explicit_target = as_float(
        first_value(
            raw,
            (
                "target_price",
                "take_profit",
                "suggested_target",
                "recommended_target",
            ),
        )
    )

    if explicit_stop is not None and explicit_target is not None:
        valid = (
            explicit_stop < entry < explicit_target
            if direction == "BUY"
            else explicit_target < entry < explicit_stop
        )
        if valid:
            return explicit_stop, explicit_target

    atr = as_float(
        first_value(
            raw,
            ("atr_14", "atr", "average_true_range"),
        )
    )

    if atr is None or atr <= 0:
        lookback = candles[max(0, entry_index - 14) : entry_index]
        ranges = [c.high - c.low for c in lookback if c.high >= c.low]
        atr = mean(ranges) if ranges else entry * 0.005

    stop_distance = max(atr * stop_atr_multiple, entry * 0.0001)

    if direction == "BUY":
        return entry - stop_distance, entry + stop_distance * reward_risk
    return entry + stop_distance, entry - stop_distance * reward_risk


def apply_entry_cost(
    direction: str,
    raw_entry: float,
    spread_bps: float,
    slippage_bps: float,
) -> float:
    total_bps = spread_bps / 2 + slippage_bps
    multiplier = 1 + total_bps / 10_000 if direction == "BUY" else 1 - total_bps / 10_000
    return raw_entry * multiplier


def apply_exit_cost(
    direction: str,
    raw_exit: float,
    spread_bps: float,
    slippage_bps: float,
) -> float:
    total_bps = spread_bps / 2 + slippage_bps
    multiplier = 1 - total_bps / 10_000 if direction == "BUY" else 1 + total_bps / 10_000
    return raw_exit * multiplier


def simulate_trade(
    decision: Decision,
    candles: list[Candle],
    entry_index: int,
    account_balance: float,
    risk_percent: float,
    spread_bps: float,
    slippage_bps: float,
    holding_candles: int,
    stop_atr_multiple: float,
    reward_risk: float,
) -> SimulatedTrade | None:
    raw_entry = candles[entry_index].open
    entry = apply_entry_cost(
        decision.action,
        raw_entry,
        spread_bps,
        slippage_bps,
    )
    stop, target = infer_stop_target(
        decision,
        decision.action,
        entry,
        candles,
        entry_index,
        stop_atr_multiple,
        reward_risk,
    )

    stop_distance = abs(entry - stop)
    if stop_distance <= 0:
        return None

    risk_amount = account_balance * risk_percent / 100
    units = risk_amount / stop_distance

    max_favorable = 0.0
    max_adverse = 0.0
    last_index = min(len(candles) - 1, entry_index + holding_candles)

    raw_exit = candles[last_index].close
    exit_reason = "TIMEOUT"
    exit_index = last_index

    for index in range(entry_index, last_index + 1):
        candle = candles[index]

        if decision.action == "BUY":
            favorable = max(0.0, candle.high - entry)
            adverse = max(0.0, entry - candle.low)
            stop_hit = candle.low <= stop
            target_hit = candle.high >= target
        else:
            favorable = max(0.0, entry - candle.low)
            adverse = max(0.0, candle.high - entry)
            stop_hit = candle.high >= stop
            target_hit = candle.low <= target

        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)

        # Conservative rule: if both occur in one hourly candle, stop wins.
        if stop_hit:
            raw_exit = stop
            exit_reason = "STOP"
            exit_index = index
            break
        if target_hit:
            raw_exit = target
            exit_reason = "TARGET"
            exit_index = index
            break

    exit_price = apply_exit_cost(
        decision.action,
        raw_exit,
        spread_bps,
        slippage_bps,
    )

    multiplier = 1 if decision.action == "BUY" else -1
    pnl_amount = (exit_price - entry) * units * multiplier
    pnl_percent = pnl_amount / account_balance if account_balance else 0.0
    r_multiple = pnl_amount / risk_amount if risk_amount else 0.0

    entry_time = datetime.fromisoformat(candles[entry_index].timestamp.replace("Z", "+00:00"))
    exit_time = datetime.fromisoformat(candles[exit_index].timestamp.replace("Z", "+00:00"))
    holding_hours = max(0.0, (exit_time - entry_time).total_seconds() / 3600)

    return SimulatedTrade(
        decision_timestamp=decision.timestamp,
        direction=decision.action,
        confidence=decision.confidence,
        market_regime=decision.market_regime,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        exit_price=exit_price,
        exit_timestamp=candles[exit_index].timestamp,
        exit_reason=exit_reason,
        pnl_amount=pnl_amount,
        pnl_percent=pnl_percent,
        r_multiple=r_multiple,
        maximum_favorable_excursion=max_favorable * units,
        maximum_adverse_excursion=max_adverse * units,
        holding_hours=holding_hours,
    )


def maximum_drawdown(equity_values: list[float]) -> float:
    peak = equity_values[0]
    worst = 0.0
    for value in equity_values:
        peak = max(peak, value)
        worst = max(worst, peak - value)
    return worst


def calculate_metrics(
    trades: list[SimulatedTrade],
    initial_capital: float,
) -> dict[str, float]:
    if not trades:
        return {
            "total_trades": 0.0,
            "win_rate": 0.0,
            "net_pnl": 0.0,
            "net_return": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "maximum_drawdown": 0.0,
            "average_r_multiple": 0.0,
            "sharpe_like": 0.0,
        }

    pnls = [trade.pnl_amount for trade in trades]
    returns = [trade.pnl_percent for trade in trades]
    wins = [value for value in pnls if value > 0]
    losses = [value for value in pnls if value < 0]

    equity = [initial_capital]
    current = initial_capital
    for pnl in pnls:
        current += pnl
        equity.append(current)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return_std = pstdev(returns) if len(returns) > 1 else 0.0

    return {
        "total_trades": float(len(trades)),
        "win_rate": len(wins) / len(trades),
        "net_pnl": sum(pnls),
        "net_return": sum(pnls) / initial_capital,
        "average_win": mean(wins) if wins else 0.0,
        "average_loss": mean(losses) if losses else 0.0,
        "profit_factor": (
            gross_profit / gross_loss
            if gross_loss > 0
            else (999.0 if gross_profit > 0 else 0.0)
        ),
        "expectancy": mean(pnls),
        "maximum_drawdown": maximum_drawdown(equity),
        "average_r_multiple": mean([trade.r_multiple for trade in trades]),
        "sharpe_like": (
            mean(returns) / return_std * math.sqrt(len(returns))
            if return_std > 0
            else 0.0
        ),
    }


def insert_metric(
    connection: sqlite3.Connection,
    run_id: int,
    name: str,
    value: float,
    segment_name: str | None = None,
    segment_value: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO backtest_metrics (
            backtest_run_id,
            metric_name,
            metric_value,
            segment_name,
            segment_value,
            created_at_utc
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            name,
            value,
            segment_name,
            segment_value,
            utc_now(),
        ),
    )


def persist_results(
    connection: sqlite3.Connection,
    *,
    symbol: str,
    interval: str,
    start: str,
    end: str,
    initial_capital: float,
    spread_bps: float,
    slippage_bps: float,
    model_version: str,
    trades: list[SimulatedTrade],
    notes: str,
) -> tuple[int, dict[str, float]]:
    started = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO backtest_runs (
            symbol,
            interval,
            start_timestamp_utc,
            end_timestamp_utc,
            initial_capital,
            spread_bps,
            slippage_bps,
            model_version,
            status,
            started_at_utc,
            completed_at_utc,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?)
        """,
        (
            symbol,
            interval,
            start,
            end,
            initial_capital,
            spread_bps,
            slippage_bps,
            model_version,
            started,
            utc_now(),
            notes,
        ),
    )
    run_id = int(cursor.lastrowid)

    for trade in trades:
        connection.execute(
            """
            INSERT INTO backtest_trades (
                backtest_run_id,
                decision_timestamp_utc,
                symbol,
                interval,
                direction,
                confidence,
                market_regime,
                entry_price,
                stop_price,
                target_price,
                exit_price,
                exit_timestamp_utc,
                exit_reason,
                pnl_amount,
                pnl_percent,
                r_multiple,
                maximum_favorable_excursion,
                maximum_adverse_excursion,
                holding_hours,
                created_at_utc
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                run_id,
                trade.decision_timestamp,
                symbol,
                interval,
                trade.direction,
                trade.confidence,
                trade.market_regime,
                trade.entry_price,
                trade.stop_price,
                trade.target_price,
                trade.exit_price,
                trade.exit_timestamp,
                trade.exit_reason,
                trade.pnl_amount,
                trade.pnl_percent,
                trade.r_multiple,
                trade.maximum_favorable_excursion,
                trade.maximum_adverse_excursion,
                trade.holding_hours,
                utc_now(),
            ),
        )

    metrics = calculate_metrics(trades, initial_capital)
    for name, value in metrics.items():
        insert_metric(connection, run_id, name, value)

    for direction in ("BUY", "SELL"):
        subset = [trade for trade in trades if trade.direction == direction]
        if subset:
            segmented = calculate_metrics(subset, initial_capital)
            for name in ("total_trades", "win_rate", "net_pnl", "average_r_multiple"):
                insert_metric(
                    connection,
                    run_id,
                    name,
                    segmented[name],
                    "direction",
                    direction,
                )

    connection.commit()
    return run_id, metrics


def run(args: argparse.Namespace) -> None:
    database_path = Path(args.database).resolve()
    if not database_path.exists():
        raise FileNotFoundError(f"Database not found: {database_path}")

    with connect(database_path) as connection:
        require_schema(connection)

        candles = load_candles(
            connection,
            args.symbol,
            args.interval,
            args.start,
            args.end,
        )
        if len(candles) < 2:
            raise RuntimeError(
                f"Not enough candles for {args.symbol} {args.interval}. "
                f"Found {len(candles)}."
            )

        decisions = load_decisions(
            connection,
            args.symbol,
            args.interval,
            args.start,
            args.end,
            args.minimum_confidence,
        )

        balance = args.initial_capital
        simulated: list[SimulatedTrade] = []
        used_entry_indices: set[int] = set()

        for decision in decisions:
            entry_index = nearest_next_candle_index(candles, decision.timestamp)
            if entry_index is None or entry_index in used_entry_indices:
                continue

            trade = simulate_trade(
                decision=decision,
                candles=candles,
                entry_index=entry_index,
                account_balance=balance,
                risk_percent=args.risk_percent,
                spread_bps=args.spread_bps,
                slippage_bps=args.slippage_bps,
                holding_candles=args.holding_candles,
                stop_atr_multiple=args.stop_atr_multiple,
                reward_risk=args.reward_risk,
            )
            if trade is None:
                continue

            simulated.append(trade)
            used_entry_indices.add(entry_index)
            balance += trade.pnl_amount

        run_start = args.start or candles[0].timestamp
        run_end = args.end or candles[-1].timestamp

        notes = json.dumps(
            {
                "method": "historical decision replay",
                "entry_rule": "next completed candle open after stored decision",
                "same_candle_conflict": "stop first",
                "holding_candles": args.holding_candles,
                "risk_percent": args.risk_percent,
                "minimum_confidence": args.minimum_confidence,
                "stop_atr_multiple": args.stop_atr_multiple,
                "fallback_reward_risk": args.reward_risk,
                "historical_news_replay": False,
                "decisions_found": len(decisions),
                "trades_simulated": len(simulated),
            },
            sort_keys=True,
        )

        run_id, metrics = persist_results(
            connection,
            symbol=args.symbol,
            interval=args.interval,
            start=run_start,
            end=run_end,
            initial_capital=args.initial_capital,
            spread_bps=args.spread_bps,
            slippage_bps=args.slippage_bps,
            model_version=args.model_version,
            trades=simulated,
            notes=notes,
        )

    print()
    print(f"Backtest run {run_id} completed.")
    print(f"Symbol:          {args.symbol}")
    print(f"Interval:        {args.interval}")
    print(f"Stored decisions:{len(decisions):>8}")
    print(f"Simulated trades:{len(simulated):>8}")
    print(f"Net P&L:         ${metrics['net_pnl']:>11,.2f}")
    print(f"Win rate:        {metrics['win_rate']:>11.1%}")
    print(f"Profit factor:   {metrics['profit_factor']:>11.2f}")
    print(f"Average R:       {metrics['average_r_multiple']:>11.2f}")
    print(f"Max drawdown:    ${metrics['maximum_drawdown']:>11,.2f}")
    print()
    if not simulated:
        print(
            "No trades were generated. This usually means the database has no "
            "historical BUY/SELL decisions for the selected symbol and period."
        )
    else:
        print("Open the dashboard Performance tab to review the saved run.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay stored historical Market AI decisions against later candles "
            "and save results into the backtesting tables."
        )
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--symbol", default="EURUSD=X")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--initial-capital", type=float, default=10_000.0)
    parser.add_argument("--risk-percent", type=float, default=0.5)
    parser.add_argument("--spread-bps", type=float, default=1.0)
    parser.add_argument("--slippage-bps", type=float, default=0.5)
    parser.add_argument("--holding-candles", type=int, default=24)
    parser.add_argument("--stop-atr-multiple", type=float, default=1.5)
    parser.add_argument("--reward-risk", type=float, default=2.0)
    parser.add_argument("--minimum-confidence", type=float, default=0.0)
    parser.add_argument(
        "--model-version",
        default="decision-replay-v1",
    )
    args = parser.parse_args()

    if args.initial_capital <= 0:
        parser.error("--initial-capital must be greater than zero")
    if not 0 < args.risk_percent <= 2:
        parser.error("--risk-percent must be between 0 and 2")
    if args.spread_bps < 0 or args.slippage_bps < 0:
        parser.error("cost assumptions cannot be negative")
    if args.holding_candles < 1:
        parser.error("--holding-candles must be at least 1")
    if args.stop_atr_multiple <= 0 or args.reward_risk <= 0:
        parser.error("stop and reward/risk parameters must be positive")
    if not 0 <= args.minimum_confidence <= 1:
        parser.error("--minimum-confidence must be between 0 and 1")

    return args


if __name__ == "__main__":
    run(parse_args())


