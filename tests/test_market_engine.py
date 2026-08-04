import numpy as np
import pandas as pd

from app.engines.market_engine import analyze_market


def make_candles(direction: int = 1, rows: int = 260) -> pd.DataFrame:
    base = 100 + direction * np.linspace(0, 30, rows)
    index = pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC")
    close = pd.Series(base + np.sin(np.arange(rows) / 5), index=index, dtype=float)
    open_ = close.shift(1).fillna(close.iloc[0])
    high = np.maximum(open_, close) + 1.0
    low = np.minimum(open_, close) - 1.0
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close},
        index=index,
    )


def test_bullish_market():
    result = analyze_market(make_candles(1), "TEST", "1h")
    assert result.bias == "bullish"
    assert result.trend == "uptrend"
    assert 0 <= result.confidence <= 1
    assert result.support_levels


def test_bearish_market():
    result = analyze_market(make_candles(-1), "TEST", "1h")
    assert result.bias == "bearish"
    assert result.trend == "downtrend"
    assert result.resistance_levels
