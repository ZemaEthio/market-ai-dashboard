from datetime import datetime, timezone
from types import SimpleNamespace

from app.engines.decision_engine import combine_analyses


def market(**overrides):
    values = dict(
        id=1, symbol="GC=F", interval="1h", bias="bullish", confidence=0.70,
        market_regime="trending", trend="uptrend", data_quality="ok",
        analyzed_at_utc=datetime.now(timezone.utc), support_levels_json="[4100.0]",
        resistance_levels_json="[4130.0]", invalidation_level=4090.0,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def news(**overrides):
    values = dict(
        id=2, bias="bullish", confidence=0.70, data_quality="ok",
        analyzed_at_utc=datetime.now(timezone.utc), relevant_article_count=5,
        high_impact_count=1,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_aligned_engines_produce_directional_confirmation():
    result = combine_analyses(market(), news())
    assert result.combined_bias == "bullish"
    assert result.alignment == "aligned"
    assert result.preferred_action == "wait_for_long_confirmation"


def test_conflict_forces_wait():
    result = combine_analyses(market(), news(bias="bearish"))
    assert result.alignment == "conflicting"
    assert result.preferred_action == "wait"
    assert result.no_trade_reasons


def test_missing_news_is_conservative():
    result = combine_analyses(market(), None)
    assert result.data_quality == "limited"
    assert result.preferred_action == "wait"
