from __future__ import annotations

import html
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from app.services.read_model import (
    health,
    latest_bundle,
    list_symbols,
    recent_news_articles,
)

DATABASE_PATH = Path(os.getenv("MARKET_AI_DATABASE", "data/market_ai.db"))

st.set_page_config(
    page_title="ZEMA Market AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --zema-blue: #2563eb;
        --zema-purple: #7c3aed;
        --zema-cyan: #06b6d4;
        --zema-green: #16a34a;
        --zema-red: #dc2626;
        --zema-amber: #d97706;
    }

    .block-container {
        padding-top: 1.1rem;
        padding-bottom: 3rem;
        max-width: 1520px;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 8% 0%, rgba(37,99,235,.12), transparent 26rem),
            radial-gradient(circle at 92% 8%, rgba(124,58,237,.10), transparent 28rem);
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(99,102,241,.22);
        background: linear-gradient(180deg, rgba(37,99,235,.07), rgba(124,58,237,.04));
    }

    .hero {
        position: relative;
        overflow: hidden;
        padding: 1.45rem 1.55rem;
        border: 1px solid rgba(99,102,241,.26);
        border-radius: 22px;
        background:
            linear-gradient(120deg, rgba(37,99,235,.22), rgba(124,58,237,.18), rgba(6,182,212,.12));
        box-shadow: 0 16px 42px rgba(15,23,42,.12);
        margin-bottom: 1rem;
    }

    .hero::after {
        content: "";
        position: absolute;
        width: 240px;
        height: 240px;
        right: -80px;
        top: -115px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,.24), transparent 68%);
    }

    .hero h1 {
        margin: 0;
        font-size: 2.15rem;
        font-weight: 850;
        letter-spacing: -.025em;
    }

    .hero p {
        margin: .42rem 0 0 0;
        opacity: .82;
        max-width: 900px;
    }

    .hero-badges {
        display: flex;
        flex-wrap: wrap;
        gap: .45rem;
        margin-top: .85rem;
    }

    .hero-badge {
        padding: .28rem .62rem;
        border-radius: 999px;
        font-size: .76rem;
        font-weight: 700;
        border: 1px solid rgba(255,255,255,.24);
        background: rgba(255,255,255,.10);
    }

    .status-card {
        border: 1px solid rgba(128,128,128,.18);
        border-radius: 18px;
        padding: 1.05rem 1.08rem;
        min-height: 132px;
        background: linear-gradient(145deg, rgba(255,255,255,.075), rgba(255,255,255,.025));
        box-shadow: 0 10px 24px rgba(15,23,42,.08);
        transition: transform .18s ease, box-shadow .18s ease;
    }

    .status-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 14px 30px rgba(15,23,42,.12);
    }

    .status-label {
        font-size: .75rem;
        text-transform: uppercase;
        letter-spacing: .10em;
        opacity: .66;
        margin-bottom: .42rem;
        font-weight: 750;
    }

    .status-value {
        font-size: 1.48rem;
        font-weight: 850;
        line-height: 1.12;
    }

    .status-sub {
        font-size: .82rem;
        opacity: .72;
        margin-top: .48rem;
        line-height: 1.35;
    }

    .positive {
        border-left: 6px solid var(--zema-green);
        background: linear-gradient(145deg, rgba(22,163,74,.15), rgba(22,163,74,.035));
    }

    .negative {
        border-left: 6px solid var(--zema-red);
        background: linear-gradient(145deg, rgba(220,38,38,.14), rgba(220,38,38,.03));
    }

    .neutral {
        border-left: 6px solid var(--zema-amber);
        background: linear-gradient(145deg, rgba(217,119,6,.15), rgba(217,119,6,.035));
    }

    .info-card {
        border-left: 6px solid var(--zema-blue);
        background: linear-gradient(145deg, rgba(37,99,235,.15), rgba(37,99,235,.035));
    }

    .explain-box {
        padding: .9rem 1rem;
        border-radius: 15px;
        border: 1px solid rgba(6,182,212,.25);
        background: linear-gradient(120deg, rgba(6,182,212,.10), rgba(37,99,235,.07));
        margin: .5rem 0 1rem;
    }

    .explain-title {
        font-weight: 800;
        margin-bottom: .28rem;
    }

    .small-note {
        font-size: .82rem;
        opacity: .72;
        line-height: 1.4;
    }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(99,102,241,.18);
        border-radius: 15px;
        padding: .72rem .84rem;
        background: linear-gradient(145deg, rgba(255,255,255,.065), rgba(255,255,255,.015));
        box-shadow: 0 7px 18px rgba(15,23,42,.055);
    }

    div[data-testid="stMetricLabel"] {
        color: rgba(99,102,241,.92);
        font-weight: 720;
    }

    button[data-baseweb="tab"] {
        font-weight: 700;
    }

    [data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(99,102,241,.15);
    }

    .stProgress > div > div > div > div {
        background-image: linear-gradient(90deg, #2563eb, #7c3aed, #06b6d4);
    }


    .macro-strip {
        padding: .95rem 1rem;
        border: 1px solid rgba(124,58,237,.22);
        border-radius: 16px;
        background: linear-gradient(120deg, rgba(124,58,237,.12), rgba(37,99,235,.08));
        margin: .35rem 0 1rem;
    }

    .macro-strip strong {font-size: 1rem;}

    .source-pill {
        display: inline-block;
        margin: .15rem .25rem .15rem 0;
        padding: .26rem .55rem;
        border-radius: 999px;
        background: rgba(37,99,235,.12);
        border: 1px solid rgba(37,99,235,.24);
        font-size: .75rem;
        font-weight: 700;
    }

    .news-timeline-item {
        padding: .7rem .85rem;
        margin-bottom: .55rem;
        border-radius: 13px;
        border: 1px solid rgba(99,102,241,.16);
        background: rgba(255,255,255,.025);
    }

    .news-timeline-title {
        font-weight: 760;
        line-height: 1.3;
        margin-bottom: .2rem;
    }

    .news-timeline-meta {
        font-size: .76rem;
        opacity: .68;
    }


    .decision-banner {
        padding: 1.05rem 1.15rem;
        border-radius: 17px;
        margin: .4rem 0 1rem;
        border: 1px solid rgba(99,102,241,.22);
        background: linear-gradient(120deg, rgba(37,99,235,.13), rgba(124,58,237,.09));
    }

    .decision-banner-title {
        font-size: 1.05rem;
        font-weight: 850;
        margin-bottom: .25rem;
    }

    .ladder {
        padding: .75rem .9rem;
        border-radius: 14px;
        border: 1px solid rgba(99,102,241,.16);
        background: rgba(255,255,255,.025);
        margin-bottom: .45rem;
    }

    .ladder-label {
        font-size: .74rem;
        text-transform: uppercase;
        letter-spacing: .08em;
        opacity: .65;
        font-weight: 750;
    }

    .ladder-value {
        font-size: 1.05rem;
        font-weight: 800;
        margin-top: .14rem;
    }

    .audit-health {
        padding: .8rem .95rem;
        border-radius: 14px;
        border: 1px solid rgba(22,163,74,.22);
        background: linear-gradient(120deg, rgba(22,163,74,.10), rgba(6,182,212,.06));
        margin-bottom: .8rem;
    }

    @media (max-width: 800px) {
        .hero h1 {font-size: 1.65rem;}
        .status-card {min-height: 112px;}
        .status-value {font-size: 1.2rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def safe_upper(value: Any, fallback: str = "—") -> str:
    return str(value).replace("_", " ").upper() if value not in (None, "") else fallback


def fmt_number(value: Any, decimals: int = 5, fallback: str = "—") -> str:
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return fallback


def fmt_percent(value: Any, fallback: str = "—") -> str:
    try:
        return f"{float(value):.1%}"
    except (TypeError, ValueError):
        return fallback


def parse_utc(value: Any) -> pd.Timestamp | None:
    if not value:
        return None
    try:
        stamp = pd.Timestamp(value)
        if stamp.tzinfo is None:
            stamp = stamp.tz_localize("UTC")
        else:
            stamp = stamp.tz_convert("UTC")
        return stamp
    except Exception:
        return None


def age_text(value: Any) -> tuple[str, float | None]:
    stamp = parse_utc(value)
    if stamp is None:
        return "Unknown", None
    age_hours = max(
        0.0,
        (pd.Timestamp.now(tz="UTC") - stamp).total_seconds() / 3600,
    )
    if age_hours < 1:
        return f"{age_hours * 60:.0f} min", age_hours
    if age_hours < 48:
        return f"{age_hours:.1f} h", age_hours
    return f"{age_hours / 24:.1f} d", age_hours


def card(label: str, value: str, sub: str, style: str = "info-card") -> str:
    return f"""
    <div class="status-card {style}">
      <div class="status-label">{label}</div>
      <div class="status-value">{value}</div>
      <div class="status-sub">{sub}</div>
    </div>
    """



def normalize_direction(value: Any) -> str:
    text = str(value or "").strip().lower()
    if any(word in text for word in ("bull", "positive", "up", "supportive", "hawkish")):
        return "bullish"
    if any(word in text for word in ("bear", "negative", "down", "adverse", "dovish")):
        return "bearish"
    return "neutral"


def impact_label(value: Any) -> str:
    text = str(value or "unknown").replace("_", " ").strip().title()
    return text or "Unknown"


def article_age(value: Any) -> str:
    label, _ = age_text(value)
    return label


def driver_card(driver: dict[str, Any], rank: int) -> str:
    title = html.escape(str(driver.get("title") or "Untitled market driver"))
    source_name = html.escape(str(driver.get("source") or "Unknown source"))
    impact = impact_label(driver.get("impact") or driver.get("importance"))
    direction = normalize_direction(
        driver.get("direction")
        or driver.get("bias")
        or driver.get("effect")
        or driver.get("score")
    )
    published = article_age(
        driver.get("published_at_utc")
        or driver.get("published_at")
        or driver.get("timestamp_utc")
    )
    url = str(driver.get("url") or "").strip()
    style = {
        "bullish": "positive",
        "bearish": "negative",
        "neutral": "neutral",
    }[direction]
    link = (
        f'<a href="{html.escape(url)}" target="_blank">Open source ↗</a>'
        if url
        else ""
    )
    return f"""
    <div class="status-card {style}">
      <div class="status-label">#{rank} · {html.escape(impact)} impact · {html.escape(direction.upper())}</div>
      <div class="status-value" style="font-size:1.02rem">{title}</div>
      <div class="status-sub">{source_name} · {html.escape(published)} old<br>{link}</div>
    </div>
    """



def confidence_band(value: Any) -> tuple[str, str]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Unknown", "neutral"
    if number >= 0.75:
        return "High", "positive"
    if number >= 0.55:
        return "Moderate", "info-card"
    return "Low", "neutral"


def scenario_field(scenario: Any, *keys: str) -> Any:
    if not isinstance(scenario, dict):
        return None
    for key in keys:
        if key in scenario and scenario[key] not in (None, ""):
            return scenario[key]
    return None


def render_scenario_panel(
    title: str,
    scenario: Any,
    style: str,
    probability_hint: str,
) -> None:
    if isinstance(scenario, dict):
        trigger = scenario_field(scenario, "trigger", "condition", "setup")
        target = scenario_field(scenario, "target", "objective", "outcome")
        invalidation = scenario_field(
            scenario, "invalidation", "invalidated_by", "failure_condition"
        )
        narrative = scenario_field(
            scenario, "summary", "description", "reasoning", "narrative"
        )
    else:
        trigger = target = invalidation = None
        narrative = scenario

    st.markdown(
        card(
            title,
            probability_hint,
            str(narrative or "Scenario details are available below."),
            style,
        ),
        unsafe_allow_html=True,
    )

    if trigger:
        st.markdown(f"**Trigger:** {trigger}")
    if target:
        st.markdown(f"**Expected path:** {target}")
    if invalidation:
        st.markdown(f"**Invalidation:** {invalidation}")

    if isinstance(scenario, dict):
        remaining = {
            key: value
            for key, value in scenario.items()
            if key
            not in {
                "trigger", "condition", "setup",
                "target", "objective", "outcome",
                "invalidation", "invalidated_by", "failure_condition",
                "summary", "description", "reasoning", "narrative",
            }
        }
        if remaining:
            with st.expander("More scenario details"):
                for key, value in remaining.items():
                    label = str(key).replace("_", " ").title()
                    st.markdown(f"**{label}:** {value}")



def table_exists(database_path: Path, table_name: str) -> bool:
    try:
        with sqlite3.connect(database_path) as connection:
            row = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False


def load_backtest_frames(
    database_path: Path,
    selected_symbol: str,
    selected_interval: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required = ("backtest_runs", "backtest_trades", "backtest_metrics")
    if not all(table_exists(database_path, table) for table in required):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    with sqlite3.connect(database_path) as connection:
        runs = pd.read_sql_query(
            """
            SELECT *
            FROM backtest_runs
            WHERE symbol = ? AND interval = ?
            ORDER BY id DESC
            """,
            connection,
            params=(selected_symbol, selected_interval),
        )

        if runs.empty:
            return runs, pd.DataFrame(), pd.DataFrame()

        run_ids = runs["id"].astype(int).tolist()
        placeholders = ",".join("?" for _ in run_ids)

        trades = pd.read_sql_query(
            f"""
            SELECT *
            FROM backtest_trades
            WHERE backtest_run_id IN ({placeholders})
            ORDER BY decision_timestamp_utc
            """,
            connection,
            params=run_ids,
        )

        metrics = pd.read_sql_query(
            f"""
            SELECT *
            FROM backtest_metrics
            WHERE backtest_run_id IN ({placeholders})
            ORDER BY backtest_run_id DESC, metric_name
            """,
            connection,
            params=run_ids,
        )

    for frame, columns in (
        (
            runs,
            (
                "start_timestamp_utc",
                "end_timestamp_utc",
                "started_at_utc",
                "completed_at_utc",
            ),
        ),
        (
            trades,
            (
                "decision_timestamp_utc",
                "exit_timestamp_utc",
                "created_at_utc",
            ),
        ),
        (metrics, ("created_at_utc",)),
    ):
        for column in columns:
            if column in frame.columns:
                frame[column] = pd.to_datetime(
                    frame[column], utc=True, errors="coerce"
                )

    return runs, trades, metrics


def calculate_performance_summary(
    trades: pd.DataFrame,
    initial_capital: float,
) -> dict[str, float]:
    if trades.empty:
        return {
            "total_trades": 0.0,
            "win_rate": 0.0,
            "net_pnl": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "max_drawdown": 0.0,
        }

    pnl = pd.to_numeric(trades.get("pnl_amount"), errors="coerce").fillna(0.0)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]

    gross_profit = float(wins.sum())
    gross_loss = abs(float(losses.sum()))
    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else (float("inf") if gross_profit > 0 else 0.0)
    )

    equity = float(initial_capital) + pnl.cumsum()
    rolling_peak = equity.cummax()
    drawdown = equity - rolling_peak

    return {
        "total_trades": float(len(trades)),
        "win_rate": float((pnl > 0).mean()),
        "net_pnl": float(pnl.sum()),
        "profit_factor": float(profit_factor),
        "expectancy": float(pnl.mean()),
        "max_drawdown": abs(float(drawdown.min())) if not drawdown.empty else 0.0,
    }


def render_scenario(title: str, scenario: Any, icon: str) -> None:
    st.markdown(f"### {icon} {title}")
    if isinstance(scenario, dict):
        for key, value in scenario.items():
            label = str(key).replace("_", " ").title()
            st.markdown(f"**{label}:** {value}")
    elif scenario:
        st.write(scenario)
    else:
        st.caption("No scenario available.")


st.markdown(
    """
    <div class="hero">
      <h1>📈 ZEMA Market AI Control Center</h1>
      <p>Technical structure, macro news, scenario intelligence, and deterministic risk controls in one research dashboard.</p>
      <div class="hero-badges">
        <span class="hero-badge">🟡 Gold</span>
        <span class="hero-badge">💱 EUR/USD</span>
        <span class="hero-badge">🧠 3 Analysis Engines</span>
        <span class="hero-badge">🛡️ Rule-Based Risk Gate</span>
        <span class="hero-badge">🔄 Auto Refresh Every 4 Hours</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    database_health = health(DATABASE_PATH)
except Exception as exc:
    st.error(f"Database unavailable: {exc}")
    st.stop()

with st.sidebar:
    st.markdown("## 📈 ZEMA Market AI")
    st.caption("Research-grade market intelligence")
    st.markdown(
        """
        <div class="small-note">
        Four-layer pipeline: market structure, macro news, decision intelligence,
        and deterministic risk control.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.header("Market controls")
    available = list_symbols(DATABASE_PATH)
    symbol_options = sorted({row["symbol"] for row in available}) or ["GC=F", "EURUSD=X"]
    symbol = st.selectbox("Instrument", symbol_options)

    intervals = sorted(
        {row["interval"] for row in available if row["symbol"] == symbol}
    ) or ["1h"]
    interval = st.selectbox("Interval", intervals)
    candle_limit = st.slider("Chart candles", 50, 1000, 300, 50)

    auto_refresh = st.toggle("Refresh page every 60 seconds", value=False)
    if auto_refresh:
        st.markdown(
            "<meta http-equiv='refresh' content='60'>",
            unsafe_allow_html=True,
        )

    if st.button("↻ Refresh now", use_container_width=True):
        st.rerun()

    st.divider()
    st.caption("System")
    st.write(f"Database integrity: **{database_health.get('integrity', 'unknown')}**")
    st.write(f"Database: `{DATABASE_PATH}`")
    st.caption("GitHub Actions refreshes the persisted database every four hours.")

bundle = latest_bundle(symbol, interval, candle_limit, DATABASE_PATH)
market = bundle.get("market")
news = bundle.get("news")
decision = bundle.get("decision")
risk = bundle.get("risk")
candle_rows = bundle.get("candles") or []

candles_df = pd.DataFrame()
latest_candle_timestamp = None
if candle_rows:
    candles_df = pd.DataFrame(candle_rows)
    candles_df["timestamp_utc"] = pd.to_datetime(
        candles_df["timestamp_utc"], utc=True, errors="coerce"
    )
    candles_df = candles_df.dropna(subset=["timestamp_utc"]).sort_values("timestamp_utc")
    latest_candle_timestamp = candles_df["timestamp_utc"].max()
    candles_df = candles_df.set_index("timestamp_utc")

candle_age_label, candle_age_hours = age_text(latest_candle_timestamp)
decision_age_label, _ = age_text(
    decision.get("decided_at_utc") if decision else None
)

if candle_age_hours is None:
    st.error("No current candle timestamp is available.")
elif candle_age_hours > 8:
    st.error(
        f"Market data is stale: latest candle is {candle_age_label} old. "
        "Do not use this output for a current trading decision."
    )
elif candle_age_hours > 3:
    st.warning(f"Market data is {candle_age_label} old. Confirm freshness before acting.")
else:
    st.success(f"Data freshness looks healthy. Latest candle age: {candle_age_label}.")

with st.sidebar:
    st.caption("Live snapshot")
    if candle_age_hours is None:
        st.error("Data age unknown")
    elif candle_age_hours <= 3:
        st.success(f"Market data fresh · {candle_age_label}")
    elif candle_age_hours <= 8:
        st.warning(f"Market data aging · {candle_age_label}")
    else:
        st.error(f"Market data stale · {candle_age_label}")

    latest_action = safe_upper(decision.get("preferred_action") if decision else None)
    st.metric("Current decision", latest_action)
    st.metric(
        "Risk gate",
        "APPROVED" if risk and risk.get("approved") else ("REJECTED" if risk else "NOT RUN"),
    )

action = decision.get("preferred_action") if decision else None
approved = bool(risk and risk.get("approved"))
if action in ("long", "buy") and approved:
    executive_value, executive_style = "BUY CANDIDATE", "positive"
elif action in ("short", "sell") and approved:
    executive_value, executive_style = "SELL CANDIDATE", "negative"
else:
    executive_value, executive_style = "WAIT / NO TRADE", "neutral"

row = st.columns(4)
row[0].markdown(
    card(
        "Executive decision",
        executive_value,
        decision.get("summary", "No Engine 3 output available.") if decision else "Run Engine 3.",
        executive_style,
    ),
    unsafe_allow_html=True,
)
row[1].markdown(
    card(
        "Combined confidence",
        fmt_percent(decision.get("confidence") if decision else None),
        f"Alignment: {safe_upper(decision.get('alignment') if decision else None)}",
        "info-card",
    ),
    unsafe_allow_html=True,
)
row[2].markdown(
    card(
        "Risk gate",
        "APPROVED" if approved else ("REJECTED" if risk else "NOT RUN"),
        risk.get("summary", "Run the deterministic risk engine.") if risk else "No risk evaluation.",
        "positive" if approved else "negative",
    ),
    unsafe_allow_html=True,
)
row[3].markdown(
    card(
        "Data age",
        candle_age_label,
        f"Decision age: {decision_age_label}",
        "positive" if candle_age_hours is not None and candle_age_hours <= 3 else "neutral",
    ),
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="explain-box">
      <div class="explain-title">How to read this dashboard</div>
      <div class="small-note">
        A trade candidate appears only when Engine 3 identifies a directional setup
        <strong>and</strong> the deterministic Risk Engine approves it. Confidence measures
        agreement and evidence quality—not the probability of profit. A WAIT result is a
        valid safety decision, not a system failure.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

confidence_left, confidence_right = st.columns(2)
with confidence_left:
    st.caption("Combined decision confidence")
    decision_confidence = float(decision.get("confidence", 0.0)) if decision else 0.0
    st.progress(max(0.0, min(1.0, decision_confidence)))
    st.caption(
        "Higher values indicate stronger agreement between technical and macro evidence."
    )

with confidence_right:
    st.caption("Technical confidence")
    technical_confidence = float(market.get("confidence", 0.0)) if market else 0.0
    st.progress(max(0.0, min(1.0, technical_confidence)))
    st.caption(
        "Based on trend structure, momentum, volatility, levels, and data quality."
    )

st.markdown("### Market overview")
metrics = st.columns(6)
metrics[0].metric("Last price", fmt_number(market.get("last_price") if market else None))
metrics[1].metric("Technical bias", safe_upper(market.get("bias") if market else None))
metrics[2].metric("Market confidence", fmt_percent(market.get("confidence") if market else None))
metrics[3].metric("News bias", safe_upper(news.get("bias") if news else None))
metrics[4].metric("RSI 14", fmt_number(market.get("rsi14") if market else None, 2))
metrics[5].metric("Market regime", safe_upper(market.get("market_regime") if market else None))

trend_text = safe_upper(market.get("trend") if market else None)
news_text = safe_upper(news.get("bias") if news else None)
alignment_text = safe_upper(decision.get("alignment") if decision else None)

st.caption(
    f"Quick read: technical trend is **{trend_text}**, news bias is **{news_text}**, "
    f"and engine alignment is **{alignment_text}**."
)

if candles_df.empty:
    st.warning("No candles found for the selected instrument and interval.")
else:
    chart_data = candles_df.copy().sort_index()
    chart_data["EMA 20"] = chart_data["close"].ewm(span=20, adjust=False).mean()
    chart_data["EMA 50"] = chart_data["close"].ewm(span=50, adjust=False).mean()
    chart_data["EMA 200"] = chart_data["close"].ewm(span=200, adjust=False).mean()

    # Volatility envelope and momentum indicator.
    rolling_mean = chart_data["close"].rolling(20).mean()
    rolling_std = chart_data["close"].rolling(20).std()
    chart_data["BB Upper"] = rolling_mean + (2 * rolling_std)
    chart_data["BB Lower"] = rolling_mean - (2 * rolling_std)

    price_delta = chart_data["close"].diff()
    average_gain = price_delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    average_loss = (-price_delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    relative_strength = average_gain / average_loss.replace(0, pd.NA)
    chart_data["RSI 14"] = (100 - (100 / (1 + relative_strength))).fillna(50)
    chart_data["Return %"] = chart_data["close"].pct_change().mul(100)

    controls = st.columns([1.2, 1, 1, 1, 1.25])
    chart_style = controls[0].selectbox(
        "Chart style",
        ["Candles", "Line"],
        index=0,
        key="market_overview_chart_style",
    )
    show_emas = controls[1].toggle("EMA trend", value=True, key="market_show_emas")
    show_bands = controls[2].toggle("Bollinger", value=False, key="market_show_bands")
    show_levels = controls[3].toggle("S/R levels", value=True, key="market_show_levels")
    lower_panel = controls[4].selectbox(
        "Lower panel",
        ["RSI", "Volume", "Returns"],
        index=0,
        key="market_lower_panel",
    )

    volume_available = "volume" in chart_data.columns and chart_data["volume"].notna().any()
    if lower_panel == "Volume" and not volume_available:
        st.caption("Volume is unavailable for this feed, so the lower panel is showing RSI instead.")
        lower_panel = "RSI"

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.045,
        row_heights=[0.72, 0.28],
    )

    if chart_style == "Candles":
        fig.add_trace(
            go.Candlestick(
                x=chart_data.index,
                open=chart_data["open"],
                high=chart_data["high"],
                low=chart_data["low"],
                close=chart_data["close"],
                name="Price",
                increasing_line_color="#16a34a",
                decreasing_line_color="#dc2626",
                increasing_fillcolor="#16a34a",
                decreasing_fillcolor="#dc2626",
                hovertext=[
                    f"O {o:.5f}<br>H {h:.5f}<br>L {l:.5f}<br>C {c:.5f}"
                    for o, h, l, c in zip(
                        chart_data["open"], chart_data["high"], chart_data["low"], chart_data["close"]
                    )
                ],
                hoverinfo="text+x",
            ),
            row=1,
            col=1,
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data["close"],
                mode="lines",
                name="Close",
                line={"color": "#38bdf8", "width": 2.2},
                fill="tozeroy",
                fillcolor="rgba(56,189,248,.08)",
            ),
            row=1,
            col=1,
        )

    if show_emas:
        for label, color, width in (
            ("EMA 20", "#06b6d4", 1.7),
            ("EMA 50", "#8b5cf6", 1.8),
            ("EMA 200", "#f59e0b", 2.1),
        ):
            fig.add_trace(
                go.Scatter(
                    x=chart_data.index,
                    y=chart_data[label],
                    mode="lines",
                    name=label,
                    line={"color": color, "width": width},
                    hovertemplate=f"{label}: %{{y:.5f}}<extra></extra>",
                ),
                row=1,
                col=1,
            )

    if show_bands:
        fig.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data["BB Upper"],
                mode="lines",
                name="BB upper",
                line={"color": "rgba(148,163,184,.75)", "width": 1, "dash": "dot"},
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data["BB Lower"],
                mode="lines",
                name="BB lower",
                line={"color": "rgba(148,163,184,.75)", "width": 1, "dash": "dot"},
                fill="tonexty",
                fillcolor="rgba(148,163,184,.08)",
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )

    support_levels = (market or {}).get("support_levels") or []
    resistance_levels = (market or {}).get("resistance_levels") or []
    if show_levels:
        for index, level in enumerate(support_levels[:4], start=1):
            try:
                numeric_level = float(level)
                fig.add_hline(
                    y=numeric_level,
                    row=1,
                    col=1,
                    line_dash="dot",
                    line_color="#22c55e",
                    opacity=0.62,
                    annotation_text=f"S{index} {numeric_level:.5f}",
                    annotation_position="bottom left",
                )
            except (TypeError, ValueError):
                pass

        for index, level in enumerate(resistance_levels[:4], start=1):
            try:
                numeric_level = float(level)
                fig.add_hline(
                    y=numeric_level,
                    row=1,
                    col=1,
                    line_dash="dot",
                    line_color="#ef4444",
                    opacity=0.62,
                    annotation_text=f"R{index} {numeric_level:.5f}",
                    annotation_position="top left",
                )
            except (TypeError, ValueError):
                pass

    trade_levels = (
        ("Entry", (risk or {}).get("entry_price"), "#2563eb", "solid"),
        ("Stop", (risk or {}).get("stop_price"), "#dc2626", "dash"),
        ("Target", (risk or {}).get("target_price"), "#16a34a", "dash"),
    )
    for label, value, color, dash in trade_levels:
        try:
            if value is not None:
                numeric_value = float(value)
                fig.add_hline(
                    y=numeric_value,
                    row=1,
                    col=1,
                    line_dash=dash,
                    line_color=color,
                    line_width=2,
                    annotation_text=f"{label} {numeric_value:.5f}",
                    annotation_position="top right",
                )
        except (TypeError, ValueError):
            pass

    latest_price = float(chart_data["close"].iloc[-1])
    fig.add_hline(
        y=latest_price,
        row=1,
        col=1,
        line_color="rgba(226,232,240,.55)",
        line_width=1,
        annotation_text=f"Last {latest_price:.5f}",
        annotation_position="bottom right",
    )

    if lower_panel == "RSI":
        fig.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data["RSI 14"],
                mode="lines",
                name="RSI 14",
                line={"color": "#a78bfa", "width": 2},
                hovertemplate="RSI: %{y:.1f}<extra></extra>",
            ),
            row=2,
            col=1,
        )
        fig.add_hrect(y0=70, y1=100, row=2, col=1, fillcolor="rgba(239,68,68,.08)", line_width=0)
        fig.add_hrect(y0=0, y1=30, row=2, col=1, fillcolor="rgba(34,197,94,.08)", line_width=0)
        fig.add_hline(y=70, row=2, col=1, line_dash="dot", line_color="#ef4444", opacity=.65)
        fig.add_hline(y=30, row=2, col=1, line_dash="dot", line_color="#22c55e", opacity=.65)
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
    elif lower_panel == "Volume":
        up_volume = chart_data["close"] >= chart_data["open"]
        volume_colors = ["#16a34a" if value else "#dc2626" for value in up_volume]
        fig.add_trace(
            go.Bar(
                x=chart_data.index,
                y=chart_data["volume"],
                name="Volume",
                marker_color=volume_colors,
                opacity=.65,
                hovertemplate="Volume: %{y:,.0f}<extra></extra>",
            ),
            row=2,
            col=1,
        )
        fig.update_yaxes(title_text="Volume", row=2, col=1)
    else:
        return_colors = ["#16a34a" if value >= 0 else "#dc2626" for value in chart_data["Return %"].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=chart_data.index,
                y=chart_data["Return %"],
                name="Return %",
                marker_color=return_colors,
                opacity=.72,
                hovertemplate="Return: %{y:.3f}%<extra></extra>",
            ),
            row=2,
            col=1,
        )
        fig.add_hline(y=0, row=2, col=1, line_color="rgba(226,232,240,.45)")
        fig.update_yaxes(title_text="Return %", row=2, col=1)

    fig.update_layout(
        title={
            "text": f"{symbol} · {interval} market structure",
            "x": 0.01,
            "xanchor": "left",
        },
        height=720,
        margin={"l": 10, "r": 10, "t": 72, "b": 10},
        hovermode="x unified",
        template="plotly_dark",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
        xaxis_rangeslider_visible=False,
        xaxis2={
            "rangeselector": {
                "buttons": [
                    {"count": 24, "label": "1D", "step": "hour", "stepmode": "backward"},
                    {"count": 7, "label": "1W", "step": "day", "stepmode": "backward"},
                    {"count": 1, "label": "1M", "step": "month", "stepmode": "backward"},
                    {"step": "all", "label": "All"},
                ]
            }
        },
    )
    fig.update_yaxes(title_text="Price", row=1, col=1, showgrid=True, gridcolor="rgba(148,163,184,.12)")
    fig.update_xaxes(showgrid=False)

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "scrollZoom": True,
            "responsive": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        },
    )

    recent_window = chart_data.tail(min(24, len(chart_data)))
    recent_change = (
        (recent_window["close"].iloc[-1] / recent_window["close"].iloc[0] - 1) * 100
        if len(recent_window) > 1
        else 0.0
    )
    recent_range = ((recent_window["high"].max() - recent_window["low"].min()) / latest_price) * 100
    chart_stats = st.columns(4)
    chart_stats[0].metric("Visible change", f"{recent_change:+.2f}%")
    chart_stats[1].metric("Visible range", f"{recent_range:.2f}%")
    chart_stats[2].metric("RSI now", f"{chart_data['RSI 14'].iloc[-1]:.1f}")
    chart_stats[3].metric(
        "EMA structure",
        "Bullish" if chart_data["EMA 20"].iloc[-1] > chart_data["EMA 50"].iloc[-1] else "Bearish",
    )

    with st.expander("How to read this chart", expanded=False):
        st.markdown(
            """
            - **Candles/line:** switch between detailed price action and a cleaner trend view.
            - **EMA 20/50/200:** short-, medium-, and long-term trend structure.
            - **Bollinger Bands:** a volatility envelope; widening bands indicate expanding volatility.
            - **RSI:** momentum above 70 can be stretched; below 30 can be deeply sold.
            - **Support/resistance:** dotted levels calculated by the market engine.
            - **Entry/stop/target:** the current risk plan, when one is available.
            """
        )

summary_tab, risk_tab, technical_tab, news_tab, scenarios_tab, performance_tab, audit_tab = st.tabs(
    [
        "Decision",
        "Risk",
        "Technicals",
        "News & Macro",
        "Scenarios",
        "Performance",
        "Audit",
    ]
)

with summary_tab:
    st.markdown("### Decision Intelligence")
    st.caption(
        "Engine 3 combines technical structure and macro evidence, then becomes conservative "
        "when the engines disagree or data quality weakens."
    )

    if not decision:
        st.info("Run Engine 3 to create a decision record.")
    else:
        confidence_label, confidence_style = confidence_band(decision.get("confidence"))
        decision_action = safe_upper(decision.get("preferred_action"))
        decision_bias = safe_upper(decision.get("combined_bias"))
        alignment = safe_upper(decision.get("alignment"))
        risk_level = safe_upper(decision.get("risk_level"))

        st.markdown(
            f"""
            <div class="decision-banner">
              <div class="decision-banner-title">Current conclusion: {html.escape(decision_action)}</div>
              <div class="small-note">
                Combined bias: <strong>{html.escape(decision_bias)}</strong> ·
                Alignment: <strong>{html.escape(alignment)}</strong> ·
                Risk level: <strong>{html.escape(risk_level)}</strong>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cards = st.columns(4)
        cards[0].markdown(
            card("Action", decision_action, "Preferred Engine 3 response", executive_style),
            unsafe_allow_html=True,
        )
        cards[1].markdown(
            card(
                "Confidence",
                fmt_percent(decision.get("confidence")),
                f"{confidence_label} confidence band",
                confidence_style,
            ),
            unsafe_allow_html=True,
        )
        cards[2].markdown(
            card("Engine alignment", alignment, "Technical versus macro agreement", "info-card"),
            unsafe_allow_html=True,
        )
        cards[3].markdown(
            card("Risk context", risk_level, "Engine 3 qualitative risk level", "neutral"),
            unsafe_allow_html=True,
        )

        st.caption("Decision confidence")
        st.progress(max(0.0, min(1.0, float(decision.get("confidence", 0.0) or 0.0))))

        left, right = st.columns([1.35, 1])
        with left:
            st.markdown("#### Executive rationale")
            if decision.get("preferred_action") == "wait":
                st.warning(decision.get("summary", "Wait."))
            else:
                st.info(decision.get("summary", "Decision available."))

            st.markdown("#### Evidence chain")
            evidence_rows = [
                {
                    "layer": "Technical",
                    "bias": safe_upper(market.get("bias") if market else None),
                    "confidence": fmt_percent(market.get("confidence") if market else None),
                    "quality": safe_upper(market.get("data_quality") if market else None),
                },
                {
                    "layer": "News & macro",
                    "bias": safe_upper(news.get("bias") if news else None),
                    "confidence": fmt_percent(news.get("confidence") if news else None),
                    "quality": safe_upper(news.get("data_quality") if news else None),
                },
                {
                    "layer": "Combined decision",
                    "bias": decision_bias,
                    "confidence": fmt_percent(decision.get("confidence")),
                    "quality": safe_upper(decision.get("data_quality")),
                },
            ]
            st.dataframe(pd.DataFrame(evidence_rows), use_container_width=True, hide_index=True)

        with right:
            st.markdown("#### No-trade controls")
            reasons = decision.get("no_trade_reasons") or []
            if reasons:
                for reason in reasons:
                    st.error(str(reason), icon="🛑")
            else:
                st.success("No explicit no-trade reasons were recorded.", icon="✅")

            st.markdown("#### Decision checklist")
            checks = [
                ("Technical evidence available", market is not None),
                ("Macro evidence available", news is not None),
                ("Engines aligned", "disagree" not in str(decision.get("alignment", "")).lower()),
                ("Confidence at least 55%", float(decision.get("confidence", 0.0) or 0.0) >= 0.55),
                ("Risk evaluation available", risk is not None),
            ]
            checklist_df = pd.DataFrame(
                [{"check": label, "status": "PASS" if passed else "REVIEW"} for label, passed in checks]
            )
            st.dataframe(checklist_df, use_container_width=True, hide_index=True)

        with st.expander("How Engine 3 reaches a decision"):
            st.markdown(
                """
                Engine 3 considers technical direction, macro direction, confidence,
                data quality, engine agreement, and invalidation conditions. When
                evidence conflicts or confidence is weak, it favors **WAIT**.
                """
            )

with technical_tab:
    st.markdown("### Technical Structure")
    st.caption(
        "Trend, momentum, volatility, and nearby price levels derived from persisted hourly candles."
    )

    if not market:
        st.info("Run Engine 1 to create a market analysis record.")
    else:
        price = market.get("last_price")
        ema20 = market.get("ema20")
        ema50 = market.get("ema50")
        ema200 = market.get("ema200")
        rsi = market.get("rsi14")
        atr = market.get("atr14")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Last price", fmt_number(price))
        c2.metric("EMA 20", fmt_number(ema20))
        c3.metric("EMA 50", fmt_number(ema50))
        c4.metric("EMA 200", fmt_number(ema200))
        c5.metric("ATR 14", fmt_number(atr))

        st.markdown("#### Trend ladder")
        ladder_cols = st.columns(4)
        for column, (label, value) in zip(
            ladder_cols,
            [("Price", price), ("EMA 20", ema20), ("EMA 50", ema50), ("EMA 200", ema200)],
        ):
            column.markdown(
                f"""
                <div class="ladder">
                  <div class="ladder-label">{html.escape(label)}</div>
                  <div class="ladder-value">{html.escape(fmt_number(value))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        trend_alignment = "Mixed"
        try:
            numeric_price = float(price)
            e20 = float(ema20)
            e50 = float(ema50)
            e200 = float(ema200)
            if numeric_price > e20 > e50 > e200:
                trend_alignment = "Strong bullish stack"
            elif numeric_price < e20 < e50 < e200:
                trend_alignment = "Strong bearish stack"
        except (TypeError, ValueError):
            pass

        overview = st.columns(4)
        overview[0].metric("Trend", safe_upper(market.get("trend")))
        overview[1].metric("Regime", safe_upper(market.get("market_regime")))
        overview[2].metric("RSI 14", fmt_number(rsi, 2))
        overview[3].metric("EMA structure", trend_alignment)

        try:
            rsi_value = float(rsi)
            st.caption("RSI momentum scale")
            st.progress(max(0.0, min(1.0, rsi_value / 100.0)))
            if rsi_value >= 70:
                st.warning("RSI is overbought; momentum is strong but price may be stretched.")
            elif rsi_value <= 30:
                st.warning("RSI is oversold; downside momentum is strong but price may be stretched.")
            else:
                st.info("RSI is in a neutral momentum range.")
        except (TypeError, ValueError):
            pass

        level_left, level_right = st.columns(2)
        with level_left:
            st.markdown("#### Support map")
            supports = market.get("support_levels") or []
            if supports:
                support_rows = []
                for level in supports:
                    try:
                        distance = ((float(price) - float(level)) / float(price))
                        distance_text = f"{distance:.2%}"
                    except (TypeError, ValueError, ZeroDivisionError):
                        distance_text = "—"
                    support_rows.append({"level": level, "distance below price": distance_text})
                st.dataframe(pd.DataFrame(support_rows), use_container_width=True, hide_index=True)
            else:
                st.caption("No support levels available.")

        with level_right:
            st.markdown("#### Resistance map")
            resistance = market.get("resistance_levels") or []
            if resistance:
                resistance_rows = []
                for level in resistance:
                    try:
                        distance = ((float(level) - float(price)) / float(price))
                        distance_text = f"{distance:.2%}"
                    except (TypeError, ValueError, ZeroDivisionError):
                        distance_text = "—"
                    resistance_rows.append({"level": level, "distance above price": distance_text})
                st.dataframe(pd.DataFrame(resistance_rows), use_container_width=True, hide_index=True)
            else:
                st.caption("No resistance levels available.")

        st.markdown(
            f"**Invalidation:** {fmt_number(market.get('invalidation_level'))} · "
            f"**Data quality:** {safe_upper(market.get('data_quality'))}"
        )

        st.markdown("#### Engine reasoning")
        reasons = market.get("reasons") or []
        if reasons:
            for reason in reasons:
                st.markdown(f"- {reason}")
        else:
            st.caption("No detailed technical reasons were persisted.")

        with st.expander("Indicator guide"):
            st.markdown(
                """
                - **EMA 20 / 50 / 200:** short-, medium-, and long-term trend structure.
                - **RSI 14:** momentum and potentially stretched conditions.
                - **ATR 14:** recent volatility and a reference for stop distance.
                - **Support / resistance:** nearby zones where price may react.
                - **Invalidation:** the condition that weakens the technical thesis.
                """
            )

with news_tab:
    st.markdown("### News & Macro Intelligence")
    st.caption(
        "Official central-bank releases and retained market news are translated into "
        "instrument-specific directional pressure. This is evidence weighting, not headline trading."
    )

    articles = recent_news_articles(60, DATABASE_PATH)
    article_df = pd.DataFrame(articles) if articles else pd.DataFrame()

    if not news:
        st.info("Run Engine 2 to create a news and macro analysis record.")
    else:
        news_bias = normalize_direction(news.get("bias"))
        bias_style = {
            "bullish": "positive",
            "bearish": "negative",
            "neutral": "neutral",
        }[news_bias]

        headline_row = st.columns(4)
        headline_row[0].markdown(
            card(
                "Macro pressure",
                news_bias.upper(),
                news.get("summary", "No macro summary available."),
                bias_style,
            ),
            unsafe_allow_html=True,
        )
        headline_row[1].markdown(
            card(
                "News confidence",
                fmt_percent(news.get("confidence")),
                f"Data quality: {safe_upper(news.get('data_quality'))}",
                "info-card",
            ),
            unsafe_allow_html=True,
        )
        headline_row[2].markdown(
            card(
                "Coverage",
                str(news.get("relevant_article_count", 0)),
                f"{news.get('source_count', 0)} distinct sources retained",
                "info-card",
            ),
            unsafe_allow_html=True,
        )
        headline_row[3].markdown(
            card(
                "Event risk",
                str(news.get("high_impact_count", 0)),
                "High-impact retained items",
                "negative" if int(news.get("high_impact_count", 0) or 0) > 0 else "positive",
            ),
            unsafe_allow_html=True,
        )

        directional_score = news.get("directional_score")
        score_text = fmt_number(directional_score, 2) if directional_score is not None else "—"
        analyzed_age, _ = age_text(news.get("analyzed_at_utc"))
        st.markdown(
            f"""
            <div class="macro-strip">
              <strong>Macro interpretation for {html.escape(symbol)}</strong><br>
              Bias: <strong>{html.escape(news_bias.upper())}</strong> ·
              Directional score: <strong>{html.escape(score_text)}</strong> ·
              Analysis age: <strong>{html.escape(analyzed_age)}</strong><br>
              <span class="small-note">
                Gold usually reacts to real yields, the U.S. dollar, inflation expectations,
                central-bank policy, and risk aversion. EUR/USD is especially sensitive to the
                relative Fed-versus-ECB policy path and growth expectations.
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        confidence_value = float(news.get("confidence", 0.0) or 0.0)
        st.caption("News and macro evidence confidence")
        st.progress(max(0.0, min(1.0, confidence_value)))
        st.caption(
            "Confidence rises with relevant coverage, source diversity, recency, and consistency. "
            "It falls when feeds are sparse, stale, contradictory, or rate-limited."
        )

        warnings = news.get("warnings") or []
        if warnings:
            st.markdown("#### Coverage warnings")
            for warning in warnings:
                st.warning(str(warning))

        drivers = news.get("drivers") or []
        st.markdown("#### Top market drivers")
        if drivers:
            for row_start in range(0, min(len(drivers), 6), 3):
                columns = st.columns(3)
                for offset, driver in enumerate(drivers[row_start : row_start + 3]):
                    if isinstance(driver, dict):
                        columns[offset].markdown(
                            driver_card(driver, row_start + offset + 1),
                            unsafe_allow_html=True,
                        )
                    else:
                        columns[offset].info(str(driver))
        else:
            st.info(
                "No high-quality directional drivers were retained. A neutral macro result "
                "is preferable to forcing a signal from weak coverage."
            )

        with st.expander("How Engine 2 interprets macro news"):
            st.markdown(
                """
                **Central-bank policy:** rate guidance and balance-sheet language can move currencies,
                yields, and gold.

                **Inflation:** persistent inflation can support higher yields, while falling inflation
                may increase expectations for rate cuts.

                **Growth and labor:** weaker activity may support safe-haven demand but can also change
                expected policy paths.

                **Geopolitical and financial stress:** often increases demand for defensive assets,
                though the U.S. dollar may strengthen at the same time.

                **Source weighting:** official central-bank material is treated as higher quality than
                broad news discovery. Relevance and recency still matter.
                """
            )

    st.markdown("#### Source coverage")
    if not article_df.empty:
        source_column = next(
            (column for column in ("source", "source_name", "publisher") if column in article_df.columns),
            None,
        )
        if source_column:
            source_counts = (
                article_df[source_column]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
                .rename_axis("source")
                .reset_index(name="articles")
            )
            source_cols = st.columns([1.1, 1])
            with source_cols[0]:
                st.dataframe(
                    source_counts,
                    use_container_width=True,
                    hide_index=True,
                )
            with source_cols[1]:
                source_fig = go.Figure(
                    go.Bar(
                        x=source_counts["articles"],
                        y=source_counts["source"],
                        orientation="h",
                        marker_color="#7c3aed",
                        hovertemplate="%{y}: %{x} articles<extra></extra>",
                    )
                )
                source_fig.update_layout(
                    title="Articles by source",
                    height=max(260, 46 * len(source_counts)),
                    margin={"l": 10, "r": 10, "t": 45, "b": 10},
                    xaxis_title="Articles",
                    yaxis_title=None,
                    template="plotly_dark",
                    showlegend=False,
                )
                st.plotly_chart(
                    source_fig,
                    use_container_width=True,
                    config={"displaylogo": False},
                )

    st.markdown("#### Recent news timeline")
    if article_df.empty:
        st.caption("No news articles are currently stored.")
    else:
        timestamp_column = next(
            (
                column
                for column in ("published_at_utc", "published_at", "collected_at_utc")
                if column in article_df.columns
            ),
            None,
        )
        title_column = next(
            (column for column in ("title", "headline") if column in article_df.columns),
            None,
        )
        source_column = next(
            (column for column in ("source", "source_name", "publisher") if column in article_df.columns),
            None,
        )
        url_column = "url" if "url" in article_df.columns else None

        if timestamp_column:
            article_df[timestamp_column] = pd.to_datetime(
                article_df[timestamp_column], utc=True, errors="coerce"
            )
            article_df = article_df.sort_values(timestamp_column, ascending=False)

        timeline_limit = st.slider(
            "Timeline items",
            min_value=5,
            max_value=30,
            value=12,
            step=1,
            key="news_timeline_limit",
        )

        for _, article in article_df.head(timeline_limit).iterrows():
            title = html.escape(str(article.get(title_column) or "Untitled article"))
            source_name = html.escape(str(article.get(source_column) or "Unknown source"))
            published_value = article.get(timestamp_column) if timestamp_column else None
            age = html.escape(article_age(published_value))
            url = str(article.get(url_column) or "").strip() if url_column else ""
            link = (
                f' · <a href="{html.escape(url)}" target="_blank">Read source ↗</a>'
                if url
                else ""
            )
            st.markdown(
                f"""
                <div class="news-timeline-item">
                  <div class="news-timeline-title">{title}</div>
                  <div class="news-timeline-meta">{source_name} · {age} old{link}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.expander("Raw retained news records"):
            preferred = [
                column
                for column in (
                    timestamp_column,
                    source_column,
                    title_column,
                    url_column,
                )
                if column
            ]
            st.dataframe(
                article_df[preferred] if preferred else article_df,
                use_container_width=True,
                hide_index=True,
            )

with scenarios_tab:
    st.markdown("### Scenario Planning")
    st.caption(
        "These are conditional paths, not predictions. Read each as: "
        "if the trigger occurs, that path becomes more plausible."
    )

    if not decision:
        st.info("Run Engine 3 to generate scenarios.")
    else:
        cols = st.columns(3)
        with cols[0]:
            render_scenario_panel(
                "🟢 Bullish case",
                decision.get("bullish_scenario"),
                "positive",
                "Upside path",
            )
        with cols[1]:
            render_scenario_panel(
                "🟡 Neutral / wait case",
                decision.get("neutral_scenario"),
                "neutral",
                "Range or uncertainty",
            )
        with cols[2]:
            render_scenario_panel(
                "🔴 Bearish case",
                decision.get("bearish_scenario"),
                "negative",
                "Downside path",
            )

        st.markdown("#### Scenario comparison")
        rows = []
        for label, scenario in (
            ("Bullish", decision.get("bullish_scenario")),
            ("Neutral", decision.get("neutral_scenario")),
            ("Bearish", decision.get("bearish_scenario")),
        ):
            rows.append(
                {
                    "scenario": label,
                    "trigger": scenario_field(scenario, "trigger", "condition", "setup"),
                    "expected path": scenario_field(scenario, "target", "objective", "outcome"),
                    "invalidation": scenario_field(
                        scenario, "invalidation", "invalidated_by", "failure_condition"
                    ),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.info(
            "Act only on the scenario whose trigger has actually occurred. "
            "Do not treat the bullish and bearish cases as simultaneous signals."
        )

with risk_tab:
    st.markdown("### Deterministic Risk Control")
    st.caption(
        "The final safety gate converts a directional idea into a bounded-risk paper-trade plan "
        "or rejects it."
    )

    if not risk:
        st.info("Run the deterministic Risk Engine to create a risk evaluation.")
    else:
        approved = bool(risk.get("approved"))
        if approved:
            st.success(risk.get("summary", "Risk checks approved."), icon="✅")
        else:
            st.error(risk.get("summary", "Risk checks rejected."), icon="🛑")

        top = st.columns(4)
        top[0].markdown(
            card(
                "Risk status",
                "APPROVED" if approved else "REJECTED",
                "Final deterministic gate",
                "positive" if approved else "negative",
            ),
            unsafe_allow_html=True,
        )
        top[1].markdown(
            card(
                "Maximum loss",
                f"${float(risk.get('maximum_loss_amount', 0) or 0):,.2f}",
                "Configured capital at risk",
                "neutral",
            ),
            unsafe_allow_html=True,
        )
        top[2].markdown(
            card(
                "Position units",
                fmt_number(risk.get("position_units"), 4),
                "Model-calculated paper position",
                "info-card",
            ),
            unsafe_allow_html=True,
        )
        rr_value = float(risk.get("reward_risk_ratio", 0) or 0)
        top[3].markdown(
            card(
                "Reward / risk",
                fmt_number(rr_value, 2),
                "Target reward divided by stop risk",
                "positive" if rr_value >= 2 else "neutral",
            ),
            unsafe_allow_html=True,
        )

        st.markdown("#### Trade plan")
        trade = st.columns(4)
        trade[0].metric("Entry", fmt_number(risk.get("entry_price")))
        trade[1].metric("Stop", fmt_number(risk.get("stop_price")))
        trade[2].metric("Target", fmt_number(risk.get("target_price")))
        trade[3].metric(
            "Decision age",
            f"{float(risk.get('decision_age_hours', 0) or 0):.2f} h",
        )

        try:
            entry = float(risk.get("entry_price"))
            stop = float(risk.get("stop_price"))
            target = float(risk.get("target_price"))
            stop_distance = abs(entry - stop)
            target_distance = abs(target - entry)
            st.dataframe(
                pd.DataFrame(
                    [
                        {"measure": "Stop distance", "value": stop_distance},
                        {"measure": "Target distance", "value": target_distance},
                        {
                            "measure": "Target / stop multiple",
                            "value": target_distance / stop_distance if stop_distance else None,
                        },
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        except (TypeError, ValueError):
            pass

        rejection_reasons = risk.get("rejection_reasons") or []
        if rejection_reasons:
            st.markdown("#### Why the setup was rejected")
            for reason in rejection_reasons:
                st.error(str(reason), icon="⚠️")
        else:
            st.success("No rejection reasons were recorded.", icon="✅")

        st.markdown("#### Deterministic checks")
        checks = risk.get("checks")
        if isinstance(checks, dict):
            rows = []
            pass_count = 0
            fail_count = 0
            for key, value in checks.items():
                passed = value if isinstance(value, bool) else None
                if passed is True:
                    pass_count += 1
                elif passed is False:
                    fail_count += 1
                rows.append(
                    {
                        "check": str(key).replace("_", " ").title(),
                        "result": value,
                        "status": "PASS" if passed is True else ("FAIL" if passed is False else "INFO"),
                    }
                )

            summary_cols = st.columns(3)
            summary_cols[0].metric("Passed checks", pass_count)
            summary_cols[1].metric("Failed checks", fail_count)
            summary_cols[2].metric("Total checks", len(rows))
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.json(checks)

        st.info(
            "Approval means the setup passed sizing, staleness, confidence, reward-to-risk, "
            "event-risk, and data-quality rules. It does not guarantee profit."
        )


with performance_tab:
    st.markdown("### Backtesting & Performance Validation")
    st.caption(
        "Historical validation for the selected instrument and interval. "
        "Results will appear here as the replay and trade-simulation engines populate the backtest tables."
    )

    schema_tables = ("backtest_runs", "backtest_trades", "backtest_metrics")
    schema_ready = all(table_exists(DATABASE_PATH, table) for table in schema_tables)

    if not schema_ready:
        st.error(
            "The backtesting schema is not available in this database. "
            "Run `python init_backtesting.py` against the deployed database."
        )
    else:
        runs_df, trades_df, metrics_df = load_backtest_frames(
            DATABASE_PATH,
            symbol,
            interval,
        )

        if runs_df.empty:
            readiness = st.columns(3)
            readiness[0].markdown(
                card(
                    "Schema status",
                    "READY",
                    "Runs, trades, and metrics tables detected",
                    "positive",
                ),
                unsafe_allow_html=True,
            )
            readiness[1].markdown(
                card(
                    "Backtest runs",
                    "0",
                    f"No runs yet for {symbol} · {interval}",
                    "neutral",
                ),
                unsafe_allow_html=True,
            )
            readiness[2].markdown(
                card(
                    "Next component",
                    "SIMULATOR",
                    "Historical trade replay will populate this tab",
                    "info-card",
                ),
                unsafe_allow_html=True,
            )

            st.info(
                "The dashboard side is ready. There are no simulated trades yet, "
                "so performance statistics cannot be calculated honestly."
            )

            st.markdown("#### What will appear here")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "section": "Core metrics",
                            "outputs": "Trades, win rate, net P&L, profit factor, expectancy, drawdown",
                        },
                        {
                            "section": "Equity analysis",
                            "outputs": "Equity curve and drawdown curve",
                        },
                        {
                            "section": "Calibration",
                            "outputs": "Win rate and average result by confidence band",
                        },
                        {
                            "section": "Segmentation",
                            "outputs": "Performance by direction, regime, and model version",
                        },
                        {
                            "section": "Auditability",
                            "outputs": "Run assumptions, costs, dates, and recent simulated trades",
                        },
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            run_options = {
                int(row["id"]): (
                    f"Run {int(row['id'])} · {row.get('model_version', 'unknown')} · "
                    f"{row.get('start_timestamp_utc', '—')} → {row.get('end_timestamp_utc', '—')}"
                )
                for _, row in runs_df.iterrows()
            }
            selected_run_id = st.selectbox(
                "Backtest run",
                options=list(run_options.keys()),
                format_func=lambda run_id: run_options[run_id],
            )

            selected_run = runs_df[runs_df["id"] == selected_run_id].iloc[0]
            selected_trades = trades_df[
                trades_df["backtest_run_id"] == selected_run_id
            ].copy()
            selected_metrics = metrics_df[
                metrics_df["backtest_run_id"] == selected_run_id
            ].copy()

            initial_capital = float(selected_run.get("initial_capital", 0.0) or 0.0)
            summary = calculate_performance_summary(
                selected_trades,
                initial_capital,
            )

            top = st.columns(6)
            top[0].metric("Trades", int(summary["total_trades"]))
            top[1].metric("Win rate", f"{summary['win_rate']:.1%}")
            top[2].metric("Net P&L", f"${summary['net_pnl']:,.2f}")
            top[3].metric(
                "Profit factor",
                "∞"
                if summary["profit_factor"] == float("inf")
                else f"{summary['profit_factor']:.2f}",
            )
            top[4].metric("Expectancy", f"${summary['expectancy']:,.2f}")
            top[5].metric("Max drawdown", f"${summary['max_drawdown']:,.2f}")

            st.markdown("#### Run assumptions")
            assumptions = pd.DataFrame(
                [
                    {
                        "symbol": selected_run.get("symbol"),
                        "interval": selected_run.get("interval"),
                        "model version": selected_run.get("model_version"),
                        "status": selected_run.get("status"),
                        "initial capital": selected_run.get("initial_capital"),
                        "spread bps": selected_run.get("spread_bps"),
                        "slippage bps": selected_run.get("slippage_bps"),
                        "start": selected_run.get("start_timestamp_utc"),
                        "end": selected_run.get("end_timestamp_utc"),
                    }
                ]
            )
            st.dataframe(assumptions, use_container_width=True, hide_index=True)

            if selected_trades.empty:
                st.warning(
                    "This run exists but contains no simulated trades yet. "
                    "The historical replay may still be incomplete."
                )
            else:
                selected_trades["pnl_amount"] = pd.to_numeric(
                    selected_trades["pnl_amount"],
                    errors="coerce",
                ).fillna(0.0)
                selected_trades = selected_trades.sort_values(
                    "decision_timestamp_utc"
                )
                selected_trades["equity"] = (
                    initial_capital + selected_trades["pnl_amount"].cumsum()
                )
                selected_trades["equity_peak"] = selected_trades["equity"].cummax()
                selected_trades["drawdown"] = (
                    selected_trades["equity"] - selected_trades["equity_peak"]
                )

                chart_left, chart_right = st.columns(2)
                with chart_left:
                    equity_fig = go.Figure()
                    equity_fig.add_trace(
                        go.Scatter(
                            x=selected_trades["exit_timestamp_utc"].fillna(
                                selected_trades["decision_timestamp_utc"]
                            ),
                            y=selected_trades["equity"],
                            mode="lines",
                            name="Equity",
                        )
                    )
                    equity_fig.update_layout(
                        title="Equity curve",
                        height=360,
                        margin={"l": 10, "r": 10, "t": 48, "b": 10},
                        xaxis_title=None,
                        yaxis_title="Account value",
                        template="plotly_dark",
                    )
                    st.plotly_chart(
                        equity_fig,
                        use_container_width=True,
                        config={"displaylogo": False},
                    )

                with chart_right:
                    drawdown_fig = go.Figure()
                    drawdown_fig.add_trace(
                        go.Scatter(
                            x=selected_trades["exit_timestamp_utc"].fillna(
                                selected_trades["decision_timestamp_utc"]
                            ),
                            y=selected_trades["drawdown"],
                            mode="lines",
                            fill="tozeroy",
                            name="Drawdown",
                        )
                    )
                    drawdown_fig.update_layout(
                        title="Drawdown curve",
                        height=360,
                        margin={"l": 10, "r": 10, "t": 48, "b": 10},
                        xaxis_title=None,
                        yaxis_title="Drawdown",
                        template="plotly_dark",
                    )
                    st.plotly_chart(
                        drawdown_fig,
                        use_container_width=True,
                        config={"displaylogo": False},
                    )

                st.markdown("#### Confidence calibration")
                confidence_values = pd.to_numeric(
                    selected_trades.get("confidence"),
                    errors="coerce",
                )
                calibration_df = selected_trades.assign(
                    confidence_numeric=confidence_values
                ).dropna(subset=["confidence_numeric"])

                if calibration_df.empty:
                    st.caption("No confidence values are available for calibration.")
                else:
                    calibration_df["confidence_band"] = pd.cut(
                        calibration_df["confidence_numeric"],
                        bins=[0.0, 0.55, 0.65, 0.75, 0.85, 1.0],
                        labels=[
                            "≤55%",
                            "55–65%",
                            "65–75%",
                            "75–85%",
                            "85–100%",
                        ],
                        include_lowest=True,
                    )
                    calibration = (
                        calibration_df.groupby(
                            "confidence_band",
                            observed=False,
                        )
                        .agg(
                            trades=("id", "count"),
                            win_rate=("pnl_amount", lambda values: (values > 0).mean()),
                            average_pnl=("pnl_amount", "mean"),
                        )
                        .reset_index()
                    )
                    st.dataframe(
                        calibration,
                        use_container_width=True,
                        hide_index=True,
                    )

                st.markdown("#### Performance by direction")
                if "direction" in selected_trades.columns:
                    direction_summary = (
                        selected_trades.groupby("direction", dropna=False)
                        .agg(
                            trades=("id", "count"),
                            win_rate=("pnl_amount", lambda values: (values > 0).mean()),
                            net_pnl=("pnl_amount", "sum"),
                            average_pnl=("pnl_amount", "mean"),
                        )
                        .reset_index()
                    )
                    st.dataframe(
                        direction_summary,
                        use_container_width=True,
                        hide_index=True,
                    )

                st.markdown("#### Recent simulated trades")
                trade_columns = [
                    column
                    for column in (
                        "decision_timestamp_utc",
                        "direction",
                        "confidence",
                        "market_regime",
                        "entry_price",
                        "stop_price",
                        "target_price",
                        "exit_price",
                        "exit_reason",
                        "pnl_amount",
                        "r_multiple",
                        "holding_hours",
                    )
                    if column in selected_trades.columns
                ]
                st.dataframe(
                    selected_trades[trade_columns]
                    .sort_values("decision_timestamp_utc", ascending=False)
                    .head(50),
                    use_container_width=True,
                    hide_index=True,
                )

            if not selected_metrics.empty:
                with st.expander("Persisted backtest metrics"):
                    st.dataframe(
                        selected_metrics,
                        use_container_width=True,
                        hide_index=True,
                    )

        st.caption(
            "Backtest results are research outputs. Accuracy depends on point-in-time data, "
            "realistic costs, conservative stop/target handling, and out-of-sample validation."
        )


with audit_tab:
    st.markdown("### System Audit & Freshness")
    st.caption(
        "A transparent view of the latest persisted records, their ages, quality flags, and system integrity."
    )

    audit_rows = []
    for engine_name, record, time_field in (
        ("Engine 1 · Technical", market, "analyzed_at_utc"),
        ("Engine 2 · News", news, "analyzed_at_utc"),
        ("Engine 3 · Decision", decision, "decided_at_utc"),
        ("Risk Engine", risk, "evaluated_at_utc"),
    ):
        age, age_hours = age_text(record.get(time_field) if record else None)
        if age_hours is None:
            freshness = "MISSING"
        elif age_hours <= 3:
            freshness = "FRESH"
        elif age_hours <= 8:
            freshness = "AGING"
        else:
            freshness = "STALE"

        audit_rows.append(
            {
                "component": engine_name,
                "record_id": record.get("id") if record else None,
                "timestamp_utc": record.get(time_field) if record else None,
                "age": age,
                "freshness": freshness,
                "data_quality": safe_upper(record.get("data_quality")) if record else "MISSING",
            }
        )

    fresh_count = sum(row["freshness"] == "FRESH" for row in audit_rows)
    stale_count = sum(row["freshness"] == "STALE" for row in audit_rows)
    missing_count = sum(row["freshness"] == "MISSING" for row in audit_rows)

    st.markdown(
        f"""
        <div class="audit-health">
          <strong>System snapshot</strong><br>
          Database integrity: <strong>{html.escape(str(database_health.get('integrity', 'unknown')).upper())}</strong> ·
          Fresh components: <strong>{fresh_count}</strong> ·
          Stale components: <strong>{stale_count}</strong> ·
          Missing components: <strong>{missing_count}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    summary_cols = st.columns(4)
    summary_cols[0].metric("Database integrity", safe_upper(database_health.get("integrity")))
    summary_cols[1].metric("Fresh components", fresh_count)
    summary_cols[2].metric("Stale components", stale_count)
    summary_cols[3].metric("Missing components", missing_count)

    st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

    st.markdown("#### What the audit means")
    st.markdown(
        """
        - **Fresh:** produced within the most recent expected operating window.
        - **Aging:** usable for context, but should be refreshed before a current decision.
        - **Stale:** should not be treated as current.
        - **Data quality:** comes from the producing engine and may reveal sparse or degraded inputs.
        """
    )

    with st.expander("Raw latest bundle"):
        st.json(bundle)

st.divider()
st.markdown("### Export current snapshot")
st.caption(
    "Download the currently selected instrument's latest engine outputs for review, "
    "documentation, or paper-trading records."
)

export_left, export_right = st.columns(2)

snapshot_json = json.dumps(bundle, indent=2, default=str)
export_left.download_button(
    label="Download snapshot as JSON",
    data=snapshot_json,
    file_name=f"{symbol.replace('=', '').replace('^', '')}_{interval}_market_ai_snapshot.json",
    mime="application/json",
    use_container_width=True,
)

summary_rows = [
    {
        "symbol": symbol,
        "interval": interval,
        "last_price": market.get("last_price") if market else None,
        "technical_bias": market.get("bias") if market else None,
        "technical_confidence": market.get("confidence") if market else None,
        "news_bias": news.get("bias") if news else None,
        "news_confidence": news.get("confidence") if news else None,
        "decision_action": decision.get("preferred_action") if decision else None,
        "decision_bias": decision.get("combined_bias") if decision else None,
        "decision_confidence": decision.get("confidence") if decision else None,
        "risk_approved": risk.get("approved") if risk else None,
        "entry_price": risk.get("entry_price") if risk else None,
        "stop_price": risk.get("stop_price") if risk else None,
        "target_price": risk.get("target_price") if risk else None,
        "maximum_loss_amount": risk.get("maximum_loss_amount") if risk else None,
        "latest_candle_age": candle_age_label,
    }
]
snapshot_csv = pd.DataFrame(summary_rows).to_csv(index=False)
export_right.download_button(
    label="Download executive summary as CSV",
    data=snapshot_csv,
    file_name=f"{symbol.replace('=', '').replace('^', '')}_{interval}_executive_summary.csv",
    mime="text/csv",
    use_container_width=True,
)

st.caption(
    "Built by ZEMA · Automated refresh every four hours · "
    "Research and paper-trading decision support only."
)
