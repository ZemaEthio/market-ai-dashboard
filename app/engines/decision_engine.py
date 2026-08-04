from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


BIAS_VALUE = {"bullish": 1.0, "bearish": -1.0, "mixed": 0.0, "neutral": 0.0}


@dataclass(slots=True)
class DecisionAnalysis:
    symbol: str
    interval: str
    decided_at_utc: str
    market_analysis_id: int
    news_analysis_id: int | None
    market_bias: str
    news_bias: str
    combined_bias: str
    preferred_action: str
    confidence: float
    alignment: str
    risk_level: str
    data_quality: str
    summary: str
    bullish_scenario: dict[str, Any]
    bearish_scenario: dict[str, Any]
    neutral_scenario: dict[str, Any]
    no_trade_reasons: list[str]
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _loads(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _freshness_hours(timestamp: datetime | None) -> float:
    if timestamp is None:
        return 10_000.0
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds() / 3600.0)


def _level_text(level: float | None, symbol: str) -> str | None:
    if level is None:
        return None
    decimals = 5 if "USD=X" in symbol or symbol.upper().startswith(("EUR", "GBP")) else 2
    return f"{level:.{decimals}f}"


def combine_analyses(market, news=None) -> DecisionAnalysis:
    if market is None:
        raise ValueError("Engine 1 analysis is required before Engine 3 can run.")

    symbol = market.symbol
    market_bias = str(market.bias).lower()
    news_bias = str(news.bias).lower() if news is not None else "neutral"
    market_conf = max(0.0, min(1.0, float(market.confidence)))
    news_conf = max(0.0, min(1.0, float(news.confidence))) if news is not None else 0.0
    news_quality = str(news.data_quality).lower() if news is not None else "missing"

    # Engine 1 is the primary signal. Engine 2 modifies confidence only when coverage is credible.
    market_weight = 0.72
    news_weight = 0.28 if news is not None and news_quality == "ok" else 0.10 if news is not None else 0.0
    market_component = BIAS_VALUE.get(market_bias, 0.0) * market_conf * market_weight
    news_component = BIAS_VALUE.get(news_bias, 0.0) * news_conf * news_weight
    combined_score = market_component + news_component

    if combined_score >= 0.18:
        combined_bias = "bullish"
    elif combined_score <= -0.18:
        combined_bias = "bearish"
    else:
        combined_bias = "neutral"

    directional_market = market_bias in {"bullish", "bearish"}
    directional_news = news_bias in {"bullish", "bearish"}
    if directional_market and directional_news and market_bias == news_bias:
        alignment = "aligned"
    elif directional_market and directional_news and market_bias != news_bias:
        alignment = "conflicting"
    elif directional_market:
        alignment = "market_only"
    else:
        alignment = "unclear"

    reasons: list[str] = [
        f"Engine 1 bias is {market_bias} at {market_conf:.1%} confidence.",
        f"Market regime is {market.market_regime}; trend classification is {market.trend}.",
    ]
    no_trade: list[str] = []

    if news is None:
        reasons.append("No Engine 2 analysis is available; the decision relies on technical evidence only.")
        no_trade.append("News and macro analysis is missing.")
    else:
        reasons.append(f"Engine 2 bias is {news_bias} at {news_conf:.1%} confidence with {news.relevant_article_count} relevant articles.")
        if news_quality != "ok":
            no_trade.append("News coverage is limited or low quality.")
        if news.high_impact_count > 0 and news_conf < 0.50:
            no_trade.append("High-impact news exists but its directional evidence is weak.")

    if alignment == "aligned":
        confidence = 0.70 * market_conf + 0.30 * news_conf + 0.08
        reasons.append("Technical and news engines point in the same direction.")
    elif alignment == "conflicting":
        confidence = 0.62 * market_conf + 0.18 * news_conf - 0.18
        no_trade.append("Technical and news engines conflict.")
        reasons.append("Conflicting engines reduce conviction.")
    elif alignment == "market_only":
        confidence = 0.72 * market_conf + 0.08 * news_conf - (0.08 if news_quality != "ok" else 0.0)
    else:
        confidence = 0.55 * market_conf + 0.10 * news_conf - 0.12
        no_trade.append("The directional signal is unclear.")

    if market.data_quality != "ok":
        confidence -= 0.15
        no_trade.append("Engine 1 data quality is not acceptable.")
    market_age = _freshness_hours(market.analyzed_at_utc)
    news_age = _freshness_hours(news.analyzed_at_utc) if news is not None else 10_000.0
    if market_age > 3:
        confidence -= 0.12
        no_trade.append(f"Market analysis is stale ({market_age:.1f} hours old).")
    if news is not None and news_age > 24:
        confidence -= 0.08
        no_trade.append(f"News analysis is stale ({news_age:.1f} hours old).")

    regime = str(market.market_regime).lower()
    if "range" in regime or regime == "ranging":
        confidence -= 0.05
        reasons.append("A ranging regime lowers breakout reliability.")
    if "high_volatility" in regime:
        no_trade.append("Volatility is elevated; position risk requires extra caution.")

    confidence = round(max(0.05, min(0.92, confidence)), 4)
    if confidence < 0.55:
        no_trade.append("Combined confidence is below the 55% decision threshold.")

    supports = _loads(market.support_levels_json, [])
    resistances = _loads(market.resistance_levels_json, [])
    support = supports[0] if supports else None
    resistance = resistances[0] if resistances else None
    invalidation = market.invalidation_level

    bullish_scenario = {
        "condition": f"Price holds above {_level_text(support, symbol) or 'nearest support'} and closes above {_level_text(resistance, symbol) or 'nearest resistance'} with improving momentum.",
        "confirmation": "RSI strengthens above 50 and EMA20 remains or moves above EMA50.",
        "invalidation": f"Close below {_level_text(invalidation or support, symbol) or 'the identified support zone'}.",
        "stance": "consider_long_only_after_confirmation",
    }
    bearish_scenario = {
        "condition": f"Price closes below {_level_text(support, symbol) or 'nearest support'} and momentum weakens.",
        "confirmation": "RSI falls below 45 and price remains below EMA20.",
        "invalidation": f"Recovery above {_level_text(resistance, symbol) or 'the identified resistance zone'}.",
        "stance": "consider_short_only_after_confirmation",
    }
    neutral_scenario = {
        "condition": "Price remains between nearby support and resistance or the engines continue to disagree.",
        "stance": "wait",
        "reason": "Preserve capital until direction and reward-to-risk improve.",
    }

    unique_no_trade = list(dict.fromkeys(no_trade))
    if unique_no_trade or combined_bias == "neutral" or confidence < 0.55:
        preferred_action = "wait"
    elif combined_bias == "bullish":
        preferred_action = "wait_for_long_confirmation"
    else:
        preferred_action = "wait_for_short_confirmation"

    if alignment == "conflicting" or confidence < 0.45 or market.data_quality != "ok":
        risk_level = "high"
    elif "high_volatility" in regime or news_quality != "ok" or confidence < 0.65:
        risk_level = "medium"
    else:
        risk_level = "low"

    data_quality = "ok" if market.data_quality == "ok" and news is not None and news_quality == "ok" else "limited"
    summary = (
        f"{symbol} decision bias is {combined_bias} at {confidence:.1%} confidence. "
        f"Engine alignment is {alignment}; preferred action is {preferred_action.replace('_', ' ')}."
    )
    if unique_no_trade:
        summary += " Main caution: " + unique_no_trade[0]

    return DecisionAnalysis(
        symbol=symbol,
        interval=market.interval,
        decided_at_utc=datetime.now(timezone.utc).isoformat(),
        market_analysis_id=int(market.id),
        news_analysis_id=int(news.id) if news is not None else None,
        market_bias=market_bias,
        news_bias=news_bias,
        combined_bias=combined_bias,
        preferred_action=preferred_action,
        confidence=confidence,
        alignment=alignment,
        risk_level=risk_level,
        data_quality=data_quality,
        summary=summary,
        bullish_scenario=bullish_scenario,
        bearish_scenario=bearish_scenario,
        neutral_scenario=neutral_scenario,
        no_trade_reasons=unique_no_trade,
        reasons=reasons,
    )
