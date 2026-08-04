from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
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
    chart_df = candles_df[["close"]].copy()
    chart_df["EMA 20"] = chart_df["close"].ewm(span=20, adjust=False).mean()
    chart_df["EMA 50"] = chart_df["close"].ewm(span=50, adjust=False).mean()
    chart_df.columns = ["Close", "EMA 20", "EMA 50"]
    st.line_chart(chart_df, height=390)

summary_tab, technical_tab, news_tab, scenarios_tab, risk_tab, audit_tab = st.tabs(
    ["Decision", "Technicals", "News & Macro", "Scenarios", "Risk", "Audit"]
)

with summary_tab:
    if not decision:
        st.info("Run Engine 3 to create a decision record.")
    else:
        left, right = st.columns([1.4, 1])
        with left:
            st.markdown("#### Decision rationale")
            if action == "wait":
                st.warning(decision.get("summary", "Wait."))
            else:
                st.info(decision.get("summary", "Decision available."))

            st.markdown("#### What would block a trade")
            reasons = decision.get("no_trade_reasons") or []
            if reasons:
                for reason in reasons:
                    st.markdown(f"- {reason}")
            else:
                st.caption("No explicit no-trade reasons were recorded.")

        with right:
            st.metric("Combined bias", safe_upper(decision.get("combined_bias")))
            st.metric("Confidence", fmt_percent(decision.get("confidence")))
            st.metric("Engine alignment", safe_upper(decision.get("alignment")))
            st.metric("Risk level", safe_upper(decision.get("risk_level")))

with technical_tab:
    if not market:
        st.info("Run Engine 1 to create a market analysis record.")
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("EMA 20", fmt_number(market.get("ema20")))
        c2.metric("EMA 50", fmt_number(market.get("ema50")))
        c3.metric("EMA 200", fmt_number(market.get("ema200")))
        c4.metric("RSI 14", fmt_number(market.get("rsi14"), 2))
        c5.metric("ATR 14", fmt_number(market.get("atr14")))

        level_left, level_right = st.columns(2)
        with level_left:
            st.markdown("#### Support")
            supports = market.get("support_levels") or []
            if supports:
                st.dataframe(
                    pd.DataFrame({"Support level": supports}),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("No support levels.")
        with level_right:
            st.markdown("#### Resistance")
            resistance = market.get("resistance_levels") or []
            if resistance:
                st.dataframe(
                    pd.DataFrame({"Resistance level": resistance}),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.caption("No resistance levels.")

        st.markdown(
            f"**Trend:** {safe_upper(market.get('trend'))} · "
            f"**Regime:** {safe_upper(market.get('market_regime'))} · "
            f"**Invalidation:** {fmt_number(market.get('invalidation_level'))} · "
            f"**Quality:** {safe_upper(market.get('data_quality'))}"
        )
        with st.expander("Indicator guide"):
            st.markdown(
                """
                - **EMA 20 / 50 / 200:** short-, medium-, and long-term trend structure.
                - **RSI 14:** momentum; extreme readings can warn of stretched conditions.
                - **ATR 14:** recent volatility, useful for judging stop distance.
                - **Support / resistance:** nearby zones where price may react.
                - **Invalidation:** the level or condition that weakens the current thesis.
                """
            )

        st.markdown("#### Engine reasoning")
        for reason in market.get("reasons") or []:
            st.markdown(f"- {reason}")

with news_tab:
    if not news:
        st.info("Run Engine 2 to create a news analysis record.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Relevant articles", news.get("relevant_article_count", 0))
        c2.metric("Distinct sources", news.get("source_count", 0))
        c3.metric("High-impact items", news.get("high_impact_count", 0))
        c4.metric("News confidence", fmt_percent(news.get("confidence")))

        quality = str(news.get("data_quality", "")).lower()
        if quality == "ok":
            st.success(news.get("summary", "News analysis complete."))
        else:
            st.warning(news.get("summary", "News coverage is limited."))

        for warning in news.get("warnings") or []:
            st.warning(warning)

        drivers = news.get("drivers") or []
        st.markdown("#### Main market drivers")
        if drivers:
            driver_df = pd.DataFrame(drivers)
            preferred = [
                column
                for column in [
                    "title",
                    "source",
                    "impact",
                    "importance",
                    "relevance",
                    "score",
                    "published_at_utc",
                    "url",
                ]
                if column in driver_df.columns
            ]
            st.dataframe(
                driver_df[preferred] if preferred else driver_df,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No relevant news drivers were retained.")

    st.markdown("#### Recently collected articles")
    articles = recent_news_articles(30, DATABASE_PATH)
    if articles:
        article_df = pd.DataFrame(articles)
        preferred = [
            column
            for column in ["published_at_utc", "source", "title", "url"]
            if column in article_df.columns
        ]
        st.dataframe(
            article_df[preferred] if preferred else article_df,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No news articles stored yet.")

with scenarios_tab:
    if not decision:
        st.info("Run Engine 3 to generate scenarios.")
    else:
        bullish, neutral, bearish = st.columns(3)
        with bullish:
            render_scenario("Bullish case", decision.get("bullish_scenario"), "🟢")
        with neutral:
            render_scenario("Wait case", decision.get("neutral_scenario"), "🟡")
        with bearish:
            render_scenario("Bearish case", decision.get("bearish_scenario"), "🔴")

with risk_tab:
    if not risk:
        st.info("Run the deterministic Risk Engine to create a risk evaluation.")
    else:
        if approved:
            st.success(risk.get("summary", "Risk checks approved."))
        else:
            st.error(risk.get("summary", "Risk checks rejected."))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Maximum loss", f"${float(risk.get('maximum_loss_amount', 0)):,.2f}")
        c2.metric("Position units", fmt_number(risk.get("position_units"), 4))
        c3.metric("Reward / risk", fmt_number(risk.get("reward_risk_ratio"), 2))
        c4.metric("Decision age", f"{float(risk.get('decision_age_hours', 0)):.2f} h")

        trade = st.columns(3)
        trade[0].metric("Entry", fmt_number(risk.get("entry_price")))
        trade[1].metric("Stop", fmt_number(risk.get("stop_price")))
        trade[2].metric("Target", fmt_number(risk.get("target_price")))

        st.info(
            "Risk approval means the setup passed the configured sizing, staleness, "
            "confidence, reward-to-risk, and event-risk rules. It does not guarantee a profitable outcome."
        )

        rejection_reasons = risk.get("rejection_reasons") or []
        if rejection_reasons:
            st.markdown("#### Rejection reasons")
            for reason in rejection_reasons:
                st.markdown(f"- {reason}")

        checks = risk.get("checks")
        st.markdown("#### Deterministic checks")
        if isinstance(checks, dict):
            check_rows = []
            for key, value in checks.items():
                passed = value if isinstance(value, bool) else None
                check_rows.append(
                    {
                        "check": str(key).replace("_", " ").title(),
                        "result": value,
                        "status": "PASS" if passed is True else ("FAIL" if passed is False else "INFO"),
                    }
                )
            st.dataframe(pd.DataFrame(check_rows), use_container_width=True, hide_index=True)
        else:
            st.json(checks)

with audit_tab:
    st.markdown("#### Latest persisted records")
    audit_rows = []
    for engine_name, record, time_field in (
        ("Engine 1", market, "analyzed_at_utc"),
        ("Engine 2", news, "analyzed_at_utc"),
        ("Engine 3", decision, "decided_at_utc"),
        ("Risk", risk, "evaluated_at_utc"),
    ):
        age, _ = age_text(record.get(time_field) if record else None)
        audit_rows.append(
            {
                "component": engine_name,
                "record_id": record.get("id") if record else None,
                "timestamp_utc": record.get(time_field) if record else None,
                "age": age,
                "data_quality": record.get("data_quality") if record else None,
            }
        )
    st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

    with st.expander("Raw latest bundle"):
        st.json(bundle)

st.divider()
st.caption(
    "Decision support only. Free market and news feeds may be delayed or incomplete. "
    "No automatic trade execution is included."
)
