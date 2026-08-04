from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from app.services.read_model import health, latest_bundle, list_symbols, recent_news_articles

DATABASE_PATH = Path(os.getenv("MARKET_AI_DATABASE", "data/market_ai.db"))

st.set_page_config(page_title="Market AI Control Center", page_icon="📈", layout="wide")
st.title("Market AI Control Center")
st.caption("Decision support only. The dashboard reads persisted engine outputs; it does not execute trades.")

try:
    database_health = health(DATABASE_PATH)
except Exception as exc:
    st.error(f"Database unavailable: {exc}")
    st.stop()

with st.sidebar:
    st.header("Controls")
    available = list_symbols(DATABASE_PATH)
    symbol_options = sorted({row["symbol"] for row in available}) or ["GC=F", "EURUSD=X"]
    symbol = st.selectbox("Instrument", symbol_options)
    intervals = sorted({row["interval"] for row in available if row["symbol"] == symbol}) or ["1h"]
    interval = st.selectbox("Interval", intervals)
    candle_limit = st.slider("Chart candles", min_value=50, max_value=1000, value=300, step=50)
    auto_refresh = st.toggle("Refresh every 60 seconds", value=False)
    if auto_refresh:
        st.markdown("<meta http-equiv='refresh' content='60'>", unsafe_allow_html=True)
    st.divider()
    st.write(f"Database: `{DATABASE_PATH}`")
    st.write(f"Integrity: **{database_health['integrity']}**")

bundle = latest_bundle(symbol, interval, candle_limit, DATABASE_PATH)
market = bundle["market"]
news = bundle["news"]
decision = bundle["decision"]
risk = bundle["risk"]
candle_rows = bundle["candles"]

if not candle_rows:
    st.warning("No candles found for the selected instrument and interval.")
else:
    candles_df = pd.DataFrame(candle_rows)
    candles_df["timestamp_utc"] = pd.to_datetime(candles_df["timestamp_utc"], utc=True)
    candles_df = candles_df.set_index("timestamp_utc")
    st.subheader(f"{symbol} price")
    st.line_chart(candles_df[["close"]], height=330)

metric_columns = st.columns(6)
metric_columns[0].metric("Last price", f"{market['last_price']:.5f}" if market else "—")
metric_columns[1].metric("Market bias", market["bias"].upper() if market else "—")
metric_columns[2].metric("Market confidence", f"{market['confidence']:.1%}" if market else "—")
metric_columns[3].metric("News bias", news["bias"].upper() if news else "—")
metric_columns[4].metric("Decision", decision["preferred_action"].replace("_", " ").upper() if decision else "—")
metric_columns[5].metric("Risk gate", ("APPROVED" if risk and risk["approved"] else "REJECTED") if risk else "—")

summary_tab, technical_tab, news_tab, scenarios_tab, risk_tab, audit_tab = st.tabs(
    ["Summary", "Technicals", "News & Macro", "Scenarios", "Risk", "Audit"]
)

with summary_tab:
    if decision:
        if decision["preferred_action"] == "wait":
            st.warning(decision["summary"])
        else:
            st.info(decision["summary"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Combined bias", decision["combined_bias"].upper())
        c2.metric("Confidence", f"{decision['confidence']:.1%}")
        c3.metric("Alignment", decision["alignment"].replace("_", " "))
        c4.metric("Risk level", decision["risk_level"].upper())
        if decision["no_trade_reasons"]:
            st.subheader("No-trade reasons")
            for reason in decision["no_trade_reasons"]:
                st.write(f"• {reason}")
    else:
        st.info("Run Engine 3 to create a decision record.")

with technical_tab:
    if market:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("EMA 20", f"{market['ema20']:.5f}")
        c2.metric("EMA 50", f"{market['ema50']:.5f}")
        c3.metric("RSI 14", f"{market['rsi14']:.2f}")
        c4.metric("ATR 14", f"{market['atr14']:.5f}")
        st.write(f"**Trend:** {market['trend']}  |  **Regime:** {market['market_regime']}  |  **Data quality:** {market['data_quality']}")
        levels = pd.DataFrame(
            {
                "Support": pd.Series(market["support_levels"]),
                "Resistance": pd.Series(market["resistance_levels"]),
            }
        )
        st.dataframe(levels, use_container_width=True, hide_index=True)
        st.subheader("Engine reasoning")
        for reason in market["reasons"]:
            st.write(f"• {reason}")
    else:
        st.info("Run Engine 1 to create a market analysis record.")

with news_tab:
    if news:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Relevant articles", news["relevant_article_count"])
        c2.metric("Sources", news["source_count"])
        c3.metric("High impact", news["high_impact_count"])
        c4.metric("Confidence", f"{news['confidence']:.1%}")
        st.write(news["summary"])
        if news["warnings"]:
            for warning in news["warnings"]:
                st.warning(warning)
        if news["drivers"]:
            st.dataframe(pd.DataFrame(news["drivers"]), use_container_width=True, hide_index=True)
        else:
            st.info("No relevant news drivers were retained for this analysis.")
    else:
        st.info("Run Engine 2 to create a news analysis record.")

    st.subheader("Recently collected articles")
    articles = recent_news_articles(30, DATABASE_PATH)
    if articles:
        st.dataframe(pd.DataFrame(articles), use_container_width=True, hide_index=True)
    else:
        st.caption("No news articles stored yet.")

with scenarios_tab:
    if decision:
        left, middle, right = st.columns(3)
        with left:
            st.subheader("Bullish")
            st.json(decision["bullish_scenario"])
        with middle:
            st.subheader("Neutral / wait")
            st.json(decision["neutral_scenario"])
        with right:
            st.subheader("Bearish")
            st.json(decision["bearish_scenario"])
    else:
        st.info("Run Engine 3 to generate scenarios.")

with risk_tab:
    if risk:
        if risk["approved"]:
            st.success(risk["summary"])
        else:
            st.error(risk["summary"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Maximum loss", f"${risk['maximum_loss_amount']:,.2f}")
        c2.metric("Position units", f"{risk['position_units']:,.4f}")
        c3.metric("Reward / risk", f"{risk['reward_risk_ratio']:.2f}" if risk["reward_risk_ratio"] is not None else "—")
        c4.metric("Decision age", f"{risk['decision_age_hours']:.2f} h")
        if risk["rejection_reasons"]:
            st.subheader("Rejection reasons")
            for reason in risk["rejection_reasons"]:
                st.write(f"• {reason}")
        st.subheader("Deterministic checks")
        checks = risk["checks"]
        if isinstance(checks, dict):
            st.dataframe(
                pd.DataFrame([{"check": key, "result": value} for key, value in checks.items()]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.json(checks)
    else:
        st.info("Run the Risk Engine to create a risk evaluation record.")

with audit_tab:
    st.write("Latest persisted record IDs and timestamps")
    audit_rows = []
    for engine_name, record, time_field in (
        ("Engine 1", market, "analyzed_at_utc"),
        ("Engine 2", news, "analyzed_at_utc"),
        ("Engine 3", decision, "decided_at_utc"),
        ("Risk", risk, "evaluated_at_utc"),
    ):
        audit_rows.append(
            {
                "component": engine_name,
                "record_id": record.get("id") if record else None,
                "timestamp_utc": record.get(time_field) if record else None,
                "data_quality": record.get("data_quality") if record else None,
            }
        )
    st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
    with st.expander("Raw latest bundle"):
        st.json(bundle)
