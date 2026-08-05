from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DB = Path(os.getenv("MARKET_AI_DATABASE", "data/market_ai.db"))

st.set_page_config(page_title="Paper Trading | ZEMA Market AI", page_icon="🧪", layout="wide")
st.title("🧪 Paper Trading Lab")
st.caption("Plan, size, record, and review simulated trades. No broker connection or real-money execution.")

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def ready() -> bool:
    try:
        with connect() as con:
            names = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('paper_accounts','paper_trades')"
            )}
        return names == {"paper_accounts", "paper_trades"}
    except sqlite3.Error:
        return False

def accounts() -> pd.DataFrame:
    with connect() as con:
        return pd.read_sql_query("SELECT * FROM paper_accounts ORDER BY id", con)

def trades(account_id: int) -> pd.DataFrame:
    with connect() as con:
        df = pd.read_sql_query(
            "SELECT * FROM paper_trades WHERE account_id=? ORDER BY planned_at_utc DESC, id DESC",
            con, params=(account_id,)
        )
    for col in ("planned_at_utc", "opened_at_utc", "closed_at_utc"):
        if col in df:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df

def create_account(name: str, balance: float):
    now = now_utc()
    with connect() as con:
        con.execute(
            "INSERT INTO paper_accounts(name,starting_balance,current_balance,created_at_utc,updated_at_utc) "
            "VALUES(?,?,?,?,?)",
            (name.strip(), balance, balance, now, now),
        )
        con.commit()

def calc(direction: str, entry: float, stop: float, target: float, balance: float, risk_pct: float):
    if direction == "BUY":
        valid = stop < entry < target
        stop_distance, reward_distance = entry - stop, target - entry
        message = "BUY requires stop below entry and target above entry."
    else:
        valid = target < entry < stop
        stop_distance, reward_distance = stop - entry, entry - target
        message = "SELL requires target below entry and stop above entry."
    if not valid or stop_distance <= 0:
        return {"valid": False, "message": message, "risk": 0.0, "units": 0.0, "rr": 0.0}
    risk = balance * risk_pct / 100
    return {"valid": True, "message": "Valid structure", "risk": risk,
            "units": risk / stop_distance, "rr": reward_distance / stop_distance}

def save_plan(account_id: int, v: dict, c: dict):
    now = now_utc()
    with connect() as con:
        con.execute(
            """INSERT INTO paper_trades(
                account_id,symbol,direction,status,timeframe,setup_name,market_regime,
                entry_price,stop_price,target_price,risk_percent,risk_amount,units,
                reward_risk_ratio,planned_at_utc,confidence,thesis,invalidation,
                pre_trade_checklist,created_at_utc,updated_at_utc
            ) VALUES(?,?,?,'PLANNED',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                account_id, v["symbol"], v["direction"], v["timeframe"], v["setup"],
                v["regime"], v["entry"], v["stop"], v["target"], v["risk_pct"],
                c["risk"], c["units"], c["rr"], now, v["confidence"], v["thesis"],
                v["invalidation"], json.dumps(v["checklist"]), now, now,
            ),
        )
        con.commit()

def change_status(trade_id: int, account_id: int, status: str, exit_price=None, costs=0.0, lesson=""):
    now = now_utc()
    with connect() as con:
        t = con.execute("SELECT * FROM paper_trades WHERE id=? AND account_id=?", (trade_id, account_id)).fetchone()
        if not t:
            raise ValueError("Trade not found")
        if status == "OPEN":
            con.execute("UPDATE paper_trades SET status='OPEN',opened_at_utc=?,updated_at_utc=? WHERE id=?",
                        (now, now, trade_id))
        elif status == "CANCELLED":
            con.execute("UPDATE paper_trades SET status='CANCELLED',updated_at_utc=? WHERE id=?", (now, trade_id))
        elif status == "CLOSED":
            multiplier = 1 if t["direction"] == "BUY" else -1
            gross = (float(exit_price) - t["entry_price"]) * t["units"] * multiplier
            net = gross - costs
            r_multiple = net / t["risk_amount"] if t["risk_amount"] else 0
            bal = con.execute("SELECT current_balance FROM paper_accounts WHERE id=?", (account_id,)).fetchone()[0]
            con.execute(
                """UPDATE paper_trades SET status='CLOSED',closed_at_utc=?,exit_price=?,gross_pnl=?,
                costs=?,net_pnl=?,r_multiple=?,lessons=?,updated_at_utc=? WHERE id=?""",
                (now, exit_price, gross, costs, net, r_multiple, lesson.strip(), now, trade_id),
            )
            con.execute("UPDATE paper_accounts SET current_balance=?,updated_at_utc=? WHERE id=?",
                        (max(0, bal + net), now, account_id))
        con.commit()

if not ready():
    st.error("Run `python init_paper_trading.py` from the project root first.")
    st.stop()

acc = accounts()
if acc.empty:
    st.info("Create your first simulated account.")
    with st.form("first_account"):
        name = st.text_input("Account name", "Forex Practice")
        starting = st.number_input("Starting balance", min_value=100.0, value=10000.0, step=500.0)
        if st.form_submit_button("Create account"):
            create_account(name, starting)
            st.rerun()
    st.stop()

with st.sidebar:
    st.header("Paper account")
    options = {int(r["id"]): f"{r['name']} · ${r['current_balance']:,.2f}" for _, r in acc.iterrows()}
    account_id = st.selectbox("Active account", list(options), format_func=lambda x: options[x])
    with st.expander("Create another account"):
        with st.form("new_account"):
            new_name = st.text_input("Name")
            new_balance = st.number_input("Starting balance", min_value=100.0, value=10000.0)
            if st.form_submit_button("Create"):
                if new_name.strip():
                    create_account(new_name, new_balance)
                    st.rerun()

account = acc[acc["id"] == account_id].iloc[0]
balance = float(account["current_balance"])
starting_balance = float(account["starting_balance"])
df = trades(account_id)
closed = df[df["status"] == "CLOSED"].copy() if not df.empty else pd.DataFrame()

net_pnl = float(closed["net_pnl"].fillna(0).sum()) if not closed.empty else 0
win_rate = float((closed["net_pnl"].fillna(0) > 0).mean()) if not closed.empty else 0
metrics = st.columns(5)
metrics[0].metric("Balance", f"${balance:,.2f}")
metrics[1].metric("Net P&L", f"${net_pnl:,.2f}")
metrics[2].metric("Closed trades", len(closed))
metrics[3].metric("Win rate", f"{win_rate:.1%}")
metrics[4].metric("Open", int((df["status"] == "OPEN").sum()) if not df.empty else 0)

plan_tab, manage_tab, journal_tab, performance_tab, learn_tab = st.tabs(
    ["Plan Trade", "Manage Trades", "Journal", "Performance", "Learn"]
)

with plan_tab:
    st.subheader("Pre-trade plan and position sizing")
    with st.form("plan"):
        c1, c2, c3, c4 = st.columns(4)
        symbol = c1.selectbox("Symbol", ["EURUSD=X", "GC=F"])
        direction = c2.selectbox("Direction", ["BUY", "SELL"])
        timeframe = c3.selectbox("Timeframe", ["15m", "1h", "4h", "1d"])
        risk_pct = c4.number_input("Risk (%)", 0.1, 2.0, 0.5, 0.1)
        base = 1.1 if symbol == "EURUSD=X" else 2400.0
        p1, p2, p3 = st.columns(3)
        entry = p1.number_input("Entry", min_value=0.00001, value=base, format="%.5f")
        stop = p2.number_input("Stop", min_value=0.00001,
                               value=base * (0.995 if direction == "BUY" else 1.005), format="%.5f")
        target = p3.number_input("Target", min_value=0.00001,
                                 value=base * (1.01 if direction == "BUY" else 0.99), format="%.5f")
        q1, q2, q3 = st.columns(3)
        setup = q1.text_input("Setup", placeholder="Trend pullback...")
        regime = q2.selectbox("Regime", ["Trending", "Ranging", "High volatility", "Low volatility", "Unclear"])
        confidence = q3.slider("Evidence strength", 0.0, 1.0, 0.5, 0.05)
        thesis = st.text_area("Trade thesis")
        invalidation = st.text_area("Invalidation condition")
        a, b, c = st.columns(3)
        checks = {
            "trend_reviewed": a.checkbox("Trend/regime reviewed"),
            "events_checked": a.checkbox("Economic events checked"),
            "structure_checked": b.checkbox("Entry/stop/target logical"),
            "reward_checked": b.checkbox("Reward-to-risk reviewed"),
            "size_checked": c.checkbox("Position size reviewed"),
            "emotion_checked": c.checkbox("No revenge/FOMO trading"),
        }
        submitted = st.form_submit_button("Calculate and save plan", use_container_width=True)

    result = calc(direction, entry, stop, target, balance, risk_pct)
    m = st.columns(4)
    m[0].metric("Risk amount", f"${result['risk']:,.2f}")
    m[1].metric("Units", f"{result['units']:,.2f}")
    m[2].metric("Reward : risk", f"{result['rr']:.2f} R")
    m[3].metric("Risk policy", "PASS" if risk_pct <= 0.5 else "CAUTION")

    if submitted:
        if not result["valid"]:
            st.error(result["message"])
        elif result["rr"] < 1.5:
            st.error("Reward-to-risk must be at least 1.5 R.")
        elif not all(checks.values()):
            st.error("Complete every checklist item.")
        elif not thesis.strip() or not invalidation.strip():
            st.error("Add both thesis and invalidation.")
        else:
            save_plan(account_id, {
                "symbol": symbol, "direction": direction, "timeframe": timeframe,
                "setup": setup, "regime": regime, "entry": entry, "stop": stop,
                "target": target, "risk_pct": risk_pct, "confidence": confidence,
                "thesis": thesis, "invalidation": invalidation, "checklist": checks,
            }, result)
            st.success("Plan saved.")
            st.rerun()

with manage_tab:
    st.subheader("Manage simulated trades")
    actionable = df[df["status"].isin(["PLANNED", "OPEN"])] if not df.empty else pd.DataFrame()
    if actionable.empty:
        st.info("No planned or open trades.")
    for _, trade in actionable.iterrows():
        with st.expander(f"#{int(trade['id'])} · {trade['symbol']} · {trade['direction']} · {trade['status']}"):
            st.write(trade["thesis"] or "No thesis")
            st.caption(f"Entry {trade['entry_price']:.5f} | Stop {trade['stop_price']:.5f} | "
                       f"Target {trade['target_price']:.5f} | Risk ${trade['risk_amount']:.2f}")
            if trade["status"] == "PLANNED":
                x, y = st.columns(2)
                if x.button("Mark open", key=f"open{trade['id']}", use_container_width=True):
                    change_status(int(trade["id"]), account_id, "OPEN")
                    st.rerun()
                if y.button("Cancel", key=f"cancel{trade['id']}", use_container_width=True):
                    change_status(int(trade["id"]), account_id, "CANCELLED")
                    st.rerun()
            else:
                with st.form(f"close{trade['id']}"):
                    exit_price = st.number_input("Exit price", min_value=0.00001,
                                                 value=float(trade["entry_price"]), format="%.5f")
                    costs = st.number_input("Costs", min_value=0.0, value=0.0, step=0.25)
                    lesson = st.text_area("Post-trade lesson")
                    if st.form_submit_button("Close trade"):
                        change_status(int(trade["id"]), account_id, "CLOSED", exit_price, costs, lesson)
                        st.rerun()

with journal_tab:
    st.subheader("Trading journal")
    if df.empty:
        st.info("No entries yet.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("Download CSV", df.to_csv(index=False).encode(),
                           f"paper_journal_{account_id}.csv", "text/csv")

with performance_tab:
    st.subheader("Paper-trading performance")
    if closed.empty:
        st.info("Close at least one trade to generate analytics.")
    else:
        ordered = closed.sort_values("closed_at_utc").copy()
        ordered["net_pnl"] = pd.to_numeric(ordered["net_pnl"], errors="coerce").fillna(0)
        ordered["equity"] = starting_balance + ordered["net_pnl"].cumsum()
        ordered["peak"] = ordered["equity"].cummax()
        ordered["drawdown"] = ordered["equity"] - ordered["peak"]
        gp = ordered.loc[ordered["net_pnl"] > 0, "net_pnl"].sum()
        gl = abs(ordered.loc[ordered["net_pnl"] < 0, "net_pnl"].sum())
        pf = gp / gl if gl > 0 else float("inf")
        z = st.columns(4)
        z[0].metric("Profit factor", "∞" if pf == float("inf") else f"{pf:.2f}")
        z[1].metric("Expectancy", f"${ordered['net_pnl'].mean():,.2f}")
        z[2].metric("Max drawdown", f"${abs(ordered['drawdown'].min()):,.2f}")
        z[3].metric("Average R", f"{ordered['r_multiple'].fillna(0).mean():.2f}")
        fig = go.Figure(go.Scatter(x=ordered["closed_at_utc"], y=ordered["equity"],
                                   mode="lines+markers", name="Equity"))
        fig.update_layout(title="Simulated equity curve", height=380, yaxis_title="Balance")
        st.plotly_chart(fig, use_container_width=True)

with learn_tab:
    st.subheader("Learning workflow")
    st.markdown("""
1. Identify the market regime.
2. Check scheduled economic events.
3. Define entry, stop, target, and invalidation.
4. Size from account risk—not desired profit.
5. Reject weak or poorly rewarded setups.
6. Review the process after the outcome.
""")
    st.warning("Paper results do not guarantee live results. Live execution adds spreads, slippage, latency, financing, and emotional pressure.")
