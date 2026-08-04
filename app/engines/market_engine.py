from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MarketAnalysis:
    symbol: str
    interval: str
    candle_timestamp_utc: str
    last_price: float
    ema20: float
    ema50: float
    ema200: float | None
    rsi14: float
    atr14: float
    atr_percent: float
    trend: str
    market_regime: str
    bias: str
    confidence: float
    support_levels: list[float]
    resistance_levels: list[float]
    invalidation_level: float | None
    data_quality: str
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_columns(df: pd.DataFrame) -> None:
    required = {"Open", "High", "Low", "Close"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing OHLC columns: {', '.join(sorted(missing))}")
    if len(df) < 60:
        raise ValueError(f"At least 60 candles are required; received {len(df)}")


def _rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(100.0).where(avg_gain.ne(0), 0.0)


def _atr_wilder(df: pd.DataFrame, period: int = 14) -> pd.Series:
    previous_close = df["Close"].shift(1)
    true_range = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - previous_close).abs(),
            (df["Low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _levels(df: pd.DataFrame, lookback: int = 120) -> tuple[list[float], list[float]]:
    recent = df.tail(min(lookback, len(df)))
    current = float(recent["Close"].iloc[-1])

    rolling_low = recent["Low"].rolling(5, center=True).min()
    rolling_high = recent["High"].rolling(5, center=True).max()
    swing_lows = recent.loc[recent["Low"].eq(rolling_low), "Low"]
    swing_highs = recent.loc[recent["High"].eq(rolling_high), "High"]

    supports = [float(value) for value in swing_lows if value < current]
    resistances = [float(value) for value in swing_highs if value > current]

    if not supports:
        supports = [float(recent["Low"].quantile(0.10)), float(recent["Low"].quantile(0.25))]
    if not resistances:
        resistances = [float(recent["High"].quantile(0.75)), float(recent["High"].quantile(0.90))]

    def distinct(values: list[float], descending: bool) -> list[float]:
        result: list[float] = []
        threshold = max(current * 0.001, 1e-8)
        for value in sorted(values, reverse=descending):
            if all(abs(value - existing) >= threshold for existing in result):
                result.append(value)
            if len(result) == 2:
                break
        return [round(value, 5) for value in result]

    return distinct(supports, True), distinct(resistances, False)


def _data_quality(df: pd.DataFrame) -> str:
    nulls = int(df[["Open", "High", "Low", "Close"]].isna().sum().sum())
    duplicates = int(df.index.duplicated().sum())
    invalid = int(
        ((df["High"] < df[["Open", "Close", "Low"]].max(axis=1)) |
         (df["Low"] > df[["Open", "Close", "High"]].min(axis=1))).sum()
    )
    if nulls or duplicates or invalid:
        return f"warning:nulls={nulls},duplicates={duplicates},invalid_ohlc={invalid}"
    return "ok"


def analyze_market(df: pd.DataFrame, symbol: str, interval: str = "1h") -> MarketAnalysis:
    """Calculate deterministic technical analysis from chronological OHLC candles."""
    _require_columns(df)
    x = df.copy().sort_index()
    for column in ["Open", "High", "Low", "Close"]:
        x[column] = pd.to_numeric(x[column], errors="coerce")
    x = x.dropna(subset=["Open", "High", "Low", "Close"])
    _require_columns(x)

    x["ema20"] = x["Close"].ewm(span=20, adjust=False).mean()
    x["ema50"] = x["Close"].ewm(span=50, adjust=False).mean()
    x["ema200"] = x["Close"].ewm(span=200, adjust=False).mean() if len(x) >= 200 else np.nan
    x["rsi14"] = _rsi_wilder(x["Close"], 14)
    x["atr14"] = _atr_wilder(x, 14)

    row = x.iloc[-1]
    price = float(row["Close"])
    atr = float(row["atr14"])
    atr_percent = atr / price if price else 0.0
    ema20 = float(row["ema20"])
    ema50 = float(row["ema50"])
    ema200 = None if pd.isna(row["ema200"]) else float(row["ema200"])
    rsi = float(row["rsi14"])

    if ema20 > ema50 and (ema200 is None or ema50 > ema200):
        trend = "uptrend"
        trend_score = 1.0
    elif ema20 < ema50 and (ema200 is None or ema50 < ema200):
        trend = "downtrend"
        trend_score = -1.0
    else:
        trend = "mixed"
        trend_score = 0.0

    ema_separation = abs(ema20 - ema50) / price if price else 0.0
    if atr_percent >= 0.012:
        regime = "high_volatility"
    elif ema_separation >= 0.004:
        regime = "trending"
    elif atr_percent <= 0.003:
        regime = "low_volatility_range"
    else:
        regime = "ranging"

    if rsi >= 60:
        momentum_score = 1.0
    elif rsi <= 40:
        momentum_score = -1.0
    elif rsi >= 53:
        momentum_score = 0.4
    elif rsi <= 47:
        momentum_score = -0.4
    else:
        momentum_score = 0.0

    price_score = 1.0 if price > ema20 else -1.0
    combined = 0.55 * trend_score + 0.25 * momentum_score + 0.20 * price_score
    bias = "bullish" if combined >= 0.25 else "bearish" if combined <= -0.25 else "neutral"

    confidence = 0.50 + min(abs(combined) * 0.30, 0.30)
    if trend != "mixed" and regime == "trending":
        confidence += 0.08
    if regime == "high_volatility":
        confidence -= 0.08
    if 48 <= rsi <= 52:
        confidence -= 0.04
    confidence = round(float(np.clip(confidence, 0.35, 0.90)), 4)

    support, resistance = _levels(x)
    invalidation = support[0] if bias == "bullish" and support else resistance[0] if bias == "bearish" and resistance else None

    timestamp = x.index[-1]
    timestamp_text = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)
    quality = _data_quality(x)
    reasons = [
        f"EMA20 ({ema20:.5f}) is {'above' if ema20 > ema50 else 'below'} EMA50 ({ema50:.5f}).",
        f"RSI14 is {rsi:.2f}, indicating {'positive' if rsi > 53 else 'negative' if rsi < 47 else 'neutral'} momentum.",
        f"ATR14 is {atr:.5f} ({atr_percent:.2%} of price); regime is {regime}.",
        f"Last close is {'above' if price > ema20 else 'below'} EMA20.",
    ]

    return MarketAnalysis(
        symbol=symbol,
        interval=interval,
        candle_timestamp_utc=timestamp_text,
        last_price=round(price, 5),
        ema20=round(ema20, 5),
        ema50=round(ema50, 5),
        ema200=None if ema200 is None else round(ema200, 5),
        rsi14=round(rsi, 4),
        atr14=round(atr, 5),
        atr_percent=round(atr_percent, 6),
        trend=trend,
        market_regime=regime,
        bias=bias,
        confidence=confidence,
        support_levels=support,
        resistance_levels=resistance,
        invalidation_level=invalidation,
        data_quality=quality,
        reasons=reasons,
    )
