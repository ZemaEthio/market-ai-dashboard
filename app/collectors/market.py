from __future__ import annotations

import pandas as pd
import yfinance as yf


REQUIRED_COLUMNS = ["Open", "High", "Low", "Close"]


def fetch_prices(symbol: str, period: str = "6mo", interval: str = "1h") -> pd.DataFrame:
    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if df.empty:
        raise RuntimeError(f"No data returned for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.title)
    return normalize_and_validate_prices(df)


def normalize_and_validate_prices(df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing OHLC columns: {', '.join(missing)}")

    clean = df.copy()
    index = pd.to_datetime(clean.index, utc=True, errors="coerce")
    clean.index = index
    clean.index.name = "timestamp_utc"
    clean = clean[~clean.index.isna()]
    clean = clean[~clean.index.duplicated(keep="last")]

    numeric_columns = [column for column in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if column in clean.columns]
    for column in numeric_columns:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")

    clean = clean.dropna(subset=REQUIRED_COLUMNS)
    valid_ohlc = (
        (clean["High"] >= clean[["Open", "Close", "Low"]].max(axis=1))
        & (clean["Low"] <= clean[["Open", "Close", "High"]].min(axis=1))
        & (clean[REQUIRED_COLUMNS] > 0).all(axis=1)
    )
    clean = clean.loc[valid_ohlc].sort_index()
    if clean.empty:
        raise RuntimeError("All downloaded price rows failed validation")
    return clean
