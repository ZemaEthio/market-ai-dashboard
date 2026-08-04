from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class RiskPolicy:
    risk_percent: float = 0.5
    daily_loss_limit_percent: float = 2.0
    minimum_reward_risk: float = 2.0
    maximum_stop_percent: float = 2.0
    minimum_decision_confidence: float = 0.55
    maximum_decision_age_hours: float = 2.0
    high_impact_lockout_minutes: int = 30
    maximum_position_units: float | None = None
    require_good_data_quality: bool = True


@dataclass(slots=True)
class RiskEvaluation:
    symbol: str
    interval: str
    evaluated_at_utc: str
    decision_analysis_id: int
    status: str
    approved: bool
    direction: str
    account_balance: float
    risk_percent: float
    maximum_loss_amount: float
    daily_pnl: float
    daily_loss_limit_amount: float
    entry_price: float | None
    stop_price: float | None
    target_price: float | None
    stop_distance: float | None
    stop_percent: float | None
    reward_distance: float | None
    reward_risk_ratio: float | None
    value_per_price_unit: float
    position_units: float
    notional_value: float | None
    minutes_to_high_impact_event: int | None
    decision_age_hours: float
    data_quality: str
    rejection_reasons: list[str]
    checks: dict[str, Any]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _loads(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _as_utc(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _age_hours(value: datetime | str | None) -> float:
    timestamp = _as_utc(value)
    if timestamp is None:
        return 10_000.0
    return max(0.0, (datetime.now(timezone.utc) - timestamp).total_seconds() / 3600.0)


def _round_units(value: float) -> float:
    if value >= 1000:
        return math.floor(value)
    if value >= 10:
        return math.floor(value * 10) / 10
    return math.floor(value * 100) / 100


def _direction_from_decision(decision) -> str:
    action = str(decision.preferred_action).lower()
    bias = str(decision.combined_bias).lower()
    if "long" in action or bias == "bullish":
        return "long"
    if "short" in action or bias == "bearish":
        return "short"
    return "none"


def _scenario_target(decision, direction: str) -> float | None:
    scenario_json = decision.bullish_scenario_json if direction == "long" else decision.bearish_scenario_json
    scenario = _loads(scenario_json, {})
    for key in ("target", "target_price", "target_level"):
        value = scenario.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def evaluate_risk(
    decision,
    market,
    *,
    account_balance: float,
    daily_pnl: float = 0.0,
    entry_price: float | None = None,
    stop_price: float | None = None,
    target_price: float | None = None,
    value_per_price_unit: float = 1.0,
    minutes_to_high_impact_event: int | None = None,
    policy: RiskPolicy | None = None,
) -> RiskEvaluation:
    if decision is None:
        raise ValueError("Engine 3 decision is required before the risk engine can run.")
    if market is None:
        raise ValueError("Engine 1 market analysis is required for price and stop information.")
    if account_balance <= 0:
        raise ValueError("account_balance must be greater than zero.")
    if value_per_price_unit <= 0:
        raise ValueError("value_per_price_unit must be greater than zero.")

    policy = policy or RiskPolicy()
    direction = _direction_from_decision(decision)
    decision_age = _age_hours(decision.decided_at_utc)
    entry = float(entry_price if entry_price is not None else market.last_price)
    stop = float(stop_price if stop_price is not None else market.invalidation_level) if (stop_price is not None or market.invalidation_level is not None) else None
    target = float(target_price) if target_price is not None else _scenario_target(decision, direction)

    maximum_loss = account_balance * policy.risk_percent / 100.0
    daily_loss_limit = account_balance * policy.daily_loss_limit_percent / 100.0
    rejection_reasons: list[str] = []
    checks: dict[str, Any] = {}

    def check(name: str, passed: bool, detail: str) -> None:
        checks[name] = {"passed": bool(passed), "detail": detail}
        if not passed:
            rejection_reasons.append(detail)

    action = str(decision.preferred_action).lower()
    check("actionable_decision", action != "wait" and direction != "none", "Engine 3 preferred action must provide an actionable long or short confirmation.")
    check(
        "confidence",
        float(decision.confidence) >= policy.minimum_decision_confidence,
        f"Decision confidence must be at least {policy.minimum_decision_confidence:.1%}; actual is {float(decision.confidence):.1%}.",
    )
    quality_ok = str(decision.data_quality).lower() == "ok" or not policy.require_good_data_quality
    check("data_quality", quality_ok, f"Decision data quality must be ok; actual is {decision.data_quality}.")
    check(
        "freshness",
        decision_age <= policy.maximum_decision_age_hours,
        f"Decision age must be at most {policy.maximum_decision_age_hours:.2f} hours; actual is {decision_age:.2f}.",
    )
    check(
        "daily_loss_limit",
        daily_pnl > -daily_loss_limit,
        f"Daily loss limit requires P&L above {-daily_loss_limit:.2f}; actual is {daily_pnl:.2f}.",
    )

    event_ok = minutes_to_high_impact_event is None or minutes_to_high_impact_event > policy.high_impact_lockout_minutes
    check(
        "event_lockout",
        event_ok,
        f"High-impact events must be more than {policy.high_impact_lockout_minutes} minutes away; actual is {minutes_to_high_impact_event}.",
    )

    check("stop_available", stop is not None, "A valid stop or invalidation price must be available.")
    stop_distance: float | None = None
    stop_percent: float | None = None
    reward_distance: float | None = None
    reward_risk: float | None = None
    position_units = 0.0
    notional_value: float | None = None

    if stop is not None:
        directionally_valid = (direction == "long" and stop < entry) or (direction == "short" and stop > entry)
        check("stop_direction", directionally_valid, f"Stop must be on the loss side of entry for a {direction} position; entry={entry}, stop={stop}.")
        stop_distance = abs(entry - stop)
        stop_percent = (stop_distance / entry * 100.0) if entry else None
        check("positive_stop_distance", stop_distance > 0, "Stop distance must be greater than zero.")
        check(
            "maximum_stop_distance",
            stop_percent is not None and stop_percent <= policy.maximum_stop_percent,
            f"Stop distance must be no more than {policy.maximum_stop_percent:.3f}% of entry; actual is {stop_percent:.3f}%.",
        )

        if target is None and stop_distance > 0 and direction in {"long", "short"}:
            target = entry + policy.minimum_reward_risk * stop_distance if direction == "long" else entry - policy.minimum_reward_risk * stop_distance

        if target is not None:
            target_valid = (direction == "long" and target > entry) or (direction == "short" and target < entry)
            check("target_direction", target_valid, f"Target must be on the profit side of entry for a {direction} position; entry={entry}, target={target}.")
            reward_distance = abs(target - entry)
            reward_risk = reward_distance / stop_distance if stop_distance > 0 else None
            check(
                "reward_risk",
                reward_risk is not None and reward_risk >= policy.minimum_reward_risk,
                f"Reward-to-risk must be at least {policy.minimum_reward_risk:.2f}; actual is {reward_risk or 0:.2f}.",
            )
        else:
            check("target_available", False, "No target price could be determined.")

        if stop_distance > 0:
            raw_units = maximum_loss / (stop_distance * value_per_price_unit)
            if policy.maximum_position_units is not None:
                raw_units = min(raw_units, policy.maximum_position_units)
            position_units = max(0.0, _round_units(raw_units))
            notional_value = position_units * entry * value_per_price_unit
            check("position_size", position_units > 0, "Calculated position size must be greater than zero.")

    approved = len(rejection_reasons) == 0
    status = "approved" if approved else "rejected"
    summary = (
        f"{decision.symbol} risk evaluation is {status}. Maximum loss is {maximum_loss:.2f}; "
        f"calculated position size is {position_units:g} units."
    )
    if rejection_reasons:
        summary += " Primary rejection: " + rejection_reasons[0]

    return RiskEvaluation(
        symbol=decision.symbol,
        interval=decision.interval,
        evaluated_at_utc=datetime.now(timezone.utc).isoformat(),
        decision_analysis_id=int(decision.id),
        status=status,
        approved=approved,
        direction=direction,
        account_balance=round(account_balance, 2),
        risk_percent=policy.risk_percent,
        maximum_loss_amount=round(maximum_loss, 2),
        daily_pnl=round(daily_pnl, 2),
        daily_loss_limit_amount=round(daily_loss_limit, 2),
        entry_price=round(entry, 8) if entry is not None else None,
        stop_price=round(stop, 8) if stop is not None else None,
        target_price=round(target, 8) if target is not None else None,
        stop_distance=round(stop_distance, 8) if stop_distance is not None else None,
        stop_percent=round(stop_percent, 6) if stop_percent is not None else None,
        reward_distance=round(reward_distance, 8) if reward_distance is not None else None,
        reward_risk_ratio=round(reward_risk, 4) if reward_risk is not None else None,
        value_per_price_unit=value_per_price_unit,
        position_units=position_units,
        notional_value=round(notional_value, 2) if notional_value is not None else None,
        minutes_to_high_impact_event=minutes_to_high_impact_event,
        decision_age_hours=round(decision_age, 4),
        data_quality=str(decision.data_quality),
        rejection_reasons=list(dict.fromkeys(rejection_reasons)),
        checks=checks,
        summary=summary,
    )
