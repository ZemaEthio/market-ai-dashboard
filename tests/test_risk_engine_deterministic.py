from datetime import datetime, timezone
from types import SimpleNamespace

from app.engines.risk_engine import RiskPolicy, evaluate_risk


def decision(**overrides):
    values = dict(
        id=10,
        symbol="GC=F",
        interval="1h",
        preferred_action="wait_for_long_confirmation",
        combined_bias="bullish",
        confidence=0.70,
        data_quality="ok",
        decided_at_utc=datetime.now(timezone.utc),
        bullish_scenario_json="{}",
        bearish_scenario_json="{}",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def market(**overrides):
    values = dict(last_price=100.0, invalidation_level=98.0)
    values.update(overrides)
    return SimpleNamespace(**values)


def test_approved_position_size_and_rr():
    result = evaluate_risk(decision(), market(), account_balance=10_000)
    assert result.approved is True
    assert result.maximum_loss_amount == 50.0
    assert result.position_units == 25.0
    assert result.target_price == 104.0
    assert result.reward_risk_ratio == 2.0


def test_wait_is_rejected():
    result = evaluate_risk(decision(preferred_action="wait"), market(), account_balance=10_000)
    assert result.approved is False
    assert any("preferred action" in reason for reason in result.rejection_reasons)


def test_daily_loss_lockout():
    result = evaluate_risk(decision(), market(), account_balance=10_000, daily_pnl=-250)
    assert result.approved is False
    assert any("loss limit" in reason for reason in result.rejection_reasons)


def test_event_lockout():
    result = evaluate_risk(decision(), market(), account_balance=10_000, minutes_to_high_impact_event=15)
    assert result.approved is False
    assert any("High-impact event" in reason for reason in result.rejection_reasons)


def test_limited_quality_rejected_by_default():
    result = evaluate_risk(decision(data_quality="limited"), market(), account_balance=10_000)
    assert result.approved is False


def test_limited_quality_can_be_allowed_for_testing():
    policy = RiskPolicy(require_good_data_quality=False)
    result = evaluate_risk(decision(data_quality="limited"), market(), account_balance=10_000, policy=policy)
    assert result.approved is True
