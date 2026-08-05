from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

DB = Path(os.getenv("MARKET_AI_DATABASE", "data/market_ai.db"))
PASS_SCORE = 80.0

st.set_page_config(page_title="Forex Academy | ZEMA", page_icon="📚", layout="wide")
st.title("📚 ZEMA Forex Academy")
st.caption(
    "Learn the mechanics, risk, technicals, and news drivers of forex before using Paper Trading. "
    "Educational and simulated use only."
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def table_exists(name: str) -> bool:
    with connect() as connection:
        return (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
            ).fetchone()
            is not None
        )


def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    with connect() as connection:
        return pd.read_sql_query(sql, connection, params=params)


def execute(sql: str, params: tuple = ()) -> None:
    with connect() as connection:
        connection.execute(sql, params)
        connection.commit()


if not all(table_exists(name) for name in ("paper_accounts", "education_progress", "academy_scenarios")):
    st.error("Run `python init_paper_trading.py` to install the Forex Academy schema.")
    st.stop()

LESSONS = {
    "fx_basics": {
        "title": "1. Forex foundations",
        "topic": "Foundations",
        "summary": "Understand currency pairs, quotes, pips, spreads, and what it means to buy or sell a pair.",
        "content": [
            "A forex pair compares the value of a base currency with a quote currency. In EUR/USD, EUR is the base and USD is the quote.",
            "Buying EUR/USD means expecting the euro to strengthen relative to the U.S. dollar. Selling means expecting the euro to weaken.",
            "The bid is the price at which the market buys from you; the ask is the price at which it sells to you. The difference is the spread.",
            "For most major pairs, one pip is 0.0001. JPY pairs commonly use 0.01 as one pip.",
        ],
        "questions": [
            ("In EUR/USD, which is the base currency?", ["USD", "EUR", "Both"], 1, "The first currency is the base currency."),
            ("Buying EUR/USD expresses which view?", ["EUR strengthens versus USD", "USD strengthens versus EUR", "No directional view"], 0, "A long position benefits when EUR/USD rises."),
            ("What is the spread?", ["The difference between bid and ask", "Your stop distance", "The daily price range"], 0, "The spread is an immediate transaction cost."),
        ],
    },
    "pips_lots": {
        "title": "2. Pips, lots, leverage, and margin",
        "topic": "Mechanics",
        "summary": "Learn how trade size and leverage amplify both gains and losses.",
        "content": [
            "A standard lot is 100,000 units of the base currency; a mini lot is 10,000 and a micro lot is 1,000.",
            "Leverage lets you control a larger position with less capital, but it does not reduce the underlying market risk.",
            "Margin is collateral set aside to support a leveraged position. A margin call can occur when equity becomes insufficient.",
            "Position size should come from account risk and stop distance—not from the maximum leverage offered by a broker.",
        ],
        "questions": [
            ("A micro lot equals approximately how many base-currency units?", ["100", "1,000", "100,000"], 1, "A micro lot is 1,000 units."),
            ("What does leverage primarily do?", ["Guarantee profit", "Magnify exposure", "Remove spreads"], 1, "Leverage magnifies both gains and losses."),
            ("The safest basis for position size is:", ["Maximum broker leverage", "Desired profit", "Risk amount and stop distance"], 2, "Risk amount divided by stop distance determines position size."),
        ],
    },
    "risk_management": {
        "title": "3. Risk management",
        "topic": "Risk",
        "summary": "Define risk before reward and protect the account from a string of losses.",
        "content": [
            "Risk a small, fixed fraction of equity per trade. Beginners often use 0.25% to 1% in simulation while learning.",
            "A stop loss belongs at the price that invalidates the trade thesis—not at an arbitrary monetary amount.",
            "Reward-to-risk compares the planned reward with the amount at risk. A 2R target seeks twice the initial risk.",
            "Daily loss limits, maximum open exposure, and correlation limits help prevent one idea from becoming several hidden copies of the same risk.",
        ],
        "questions": [
            ("What should happen first?", ["Choose desired profit", "Define invalidation and risk", "Increase leverage"], 1, "Risk and invalidation come before position size and target."),
            ("If account equity is $10,000 and risk is 0.5%, what is the maximum planned loss?", ["$5", "$50", "$500"], 1, "0.5% of $10,000 is $50."),
            ("Moving a stop farther away only to avoid a loss is:", ["Good discipline", "Risk-plan violation", "Required in trends"], 1, "Changing invalidation after entry can turn a planned loss into an uncontrolled one."),
        ],
    },
    "market_sessions": {
        "title": "4. Market sessions and liquidity",
        "topic": "Market structure",
        "summary": "Understand when liquidity, volatility, and spreads typically change.",
        "content": [
            "Forex trades nearly 24 hours a day during the business week through overlapping regional sessions.",
            "London and New York overlap often brings higher liquidity and activity in major pairs.",
            "Thin-liquidity periods can produce wider spreads and sudden price moves.",
            "Session behavior is a tendency, not a guarantee; scheduled news can dominate normal session patterns.",
        ],
        "questions": [
            ("Which overlap is often active for major pairs?", ["London–New York", "Weekend–holiday", "No sessions overlap"], 0, "The London–New York overlap is typically liquid."),
            ("Thin liquidity may cause:", ["Guaranteed stability", "Wider spreads", "No slippage"], 1, "Lower liquidity can widen spreads and increase slippage."),
            ("Session tendencies should be treated as:", ["Guarantees", "Context", "Trading signals by themselves"], 1, "They provide context, not certainty."),
        ],
    },
    "technical_analysis": {
        "title": "5. Technical analysis basics",
        "topic": "Technicals",
        "summary": "Read trend, structure, support, resistance, momentum, and volatility without treating indicators as guarantees.",
        "content": [
            "An uptrend generally forms higher highs and higher lows; a downtrend forms lower highs and lower lows.",
            "Support and resistance are zones where buying or selling previously became important—not exact permanent lines.",
            "Moving averages summarize past prices. RSI measures momentum; neither predicts the future with certainty.",
            "A breakout is stronger when supported by participation, follow-through, and a clear invalidation level.",
        ],
        "questions": [
            ("Higher highs and higher lows usually describe:", ["An uptrend", "A downtrend", "A fixed spread"], 0, "That sequence is a common uptrend structure."),
            ("Support and resistance are best treated as:", ["Exact permanent prices", "Zones", "Guaranteed reversals"], 1, "Markets often react across an area rather than one exact tick."),
            ("An indicator should be used as:", ["One piece of evidence", "A guarantee", "A replacement for risk management"], 0, "Indicators add context but cannot guarantee outcomes."),
        ],
    },
    "news_fundamentals": {
        "title": "6. Fundamental and news analysis",
        "topic": "News",
        "summary": "Connect central banks, inflation, employment, growth, yields, and geopolitical risk to currencies.",
        "content": [
            "Interest-rate expectations are a major currency driver because capital tends to seek higher risk-adjusted returns.",
            "Inflation, employment, and growth data influence expectations for future central-bank policy.",
            "A headline matters only when it is relevant to the instrument, credible, fresh, and large enough to change expectations.",
            "During high-impact releases, spreads and slippage can increase. Waiting is a valid decision.",
        ],
        "questions": [
            ("Which event is usually high impact for EUR/USD?", ["Fed or ECB rate decision", "An unrelated sports result", "A months-old blog post"], 0, "Fed and ECB policy can directly alter rate expectations."),
            ("Why can strong U.S. jobs data support USD?", ["It may raise rate expectations", "It removes all risk", "It fixes the exchange rate"], 0, "Stronger data can reduce expected easing or increase expected tightening."),
            ("Near a major release, a disciplined trader may:", ["Increase leverage automatically", "Wait or reduce risk", "Ignore spreads"], 1, "Avoiding unstable conditions is valid risk management."),
        ],
    },
    "trade_planning": {
        "title": "7. Building a trade plan",
        "topic": "Process",
        "summary": "Convert an idea into a testable plan with entry, invalidation, target, and a reason not to trade.",
        "content": [
            "A complete plan states the market view, evidence, entry condition, invalidation, target, risk, and event risk.",
            "A setup is not a trade until entry conditions are met. Missing a trade is cheaper than forcing one.",
            "The plan should define what evidence would make you cancel the idea before entry.",
            "Journal the original plan so the outcome can be reviewed without hindsight bias.",
        ],
        "questions": [
            ("Which belongs in every trade plan?", ["Exact invalidation", "Guaranteed profit", "Unlimited risk"], 0, "Invalidation defines when the thesis is wrong."),
            ("A setup that has not met entry conditions is:", ["Automatically open", "Still only a setup", "Risk-free"], 1, "Wait for the planned condition."),
            ("Why save the original thesis?", ["To reduce hindsight bias", "To hide mistakes", "To change the entry later"], 0, "The original record makes review honest."),
        ],
    },
    "psychology_journal": {
        "title": "8. Psychology and journaling",
        "topic": "Discipline",
        "summary": "Recognize FOMO, revenge trading, overconfidence, and the value of process-based review.",
        "content": [
            "A good trade can lose and a poor trade can win. Judge the process first, then the outcome.",
            "FOMO often appears after a rapid move; revenge trading often follows a loss. Both can break the risk plan.",
            "A useful journal records the setup, evidence, emotions, rule compliance, outcome, and lesson.",
            "Consistent small losses are survivable; inconsistent oversized losses are not.",
        ],
        "questions": [
            ("A losing trade that followed the plan can be:", ["A good process", "Always a mistake", "Proof the market is unfair"], 0, "Execution quality and outcome are different."),
            ("Revenge trading usually means:", ["Trying to recover a loss impulsively", "Following a daily loss limit", "Reducing size"], 0, "It is emotion-driven risk escalation."),
            ("A journal should emphasize:", ["Process and evidence", "Only profit", "Only prediction accuracy"], 0, "Process review reveals repeatable strengths and weaknesses."),
        ],
    },
}

CORE_KEYS = {"fx_basics", "risk_management", "news_fundamentals"}

accounts = query("SELECT * FROM paper_accounts ORDER BY id")
if accounts.empty:
    st.info("Create a paper account in the Paper Trading page first.")
    st.stop()

with st.sidebar:
    choices = {
        int(row.id): f"{row['name']} · ${float(row['current_balance']):,.2f}"
        for _, row in accounts.iterrows()
    }
    account_id = st.selectbox("Learner account", list(choices), format_func=lambda item: choices[item])
    topic_filter = st.selectbox(
        "Topic",
        ["All"] + sorted({lesson["topic"] for lesson in LESSONS.values()}),
    )

progress = query(
    "SELECT * FROM education_progress WHERE account_id=?", (account_id,)
)
progress_by_key = {
    row.lesson_key: row for _, row in progress.iterrows()
} if not progress.empty else {}
passed = {
    key for key, row in progress_by_key.items() if int(row.passed) == 1
}

academy_passed = len(set(LESSONS).intersection(passed))
completion = academy_passed / len(LESSONS) * 100
core_ready = CORE_KEYS.issubset(passed)
average_score = (
    pd.to_numeric(progress[progress.lesson_key.isin(LESSONS)]["score"], errors="coerce").mean()
    if not progress.empty
    else 0.0
)
average_score = 0.0 if pd.isna(average_score) else float(average_score)
readiness = min(100.0, completion * 0.65 + average_score * 0.35)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Academy completion", f"{completion:.0f}%")
m2.metric("Lessons passed", f"{academy_passed}/{len(LESSONS)}")
m3.metric("Average quiz score", f"{average_score:.0f}%")
m4.metric("Trade readiness", f"{readiness:.0f}%")

if core_ready:
    st.success("Core readiness unlocked: Forex foundations, Risk Management, and News Analysis are passed.")
else:
    missing = [LESSONS[key]["title"] for key in CORE_KEYS if key not in passed]
    st.warning("Complete the core lessons before Paper Trading is unlocked: " + "; ".join(missing))

learn_tab, practice_tab, progress_tab, glossary_tab = st.tabs(
    ["Lessons", "Guided Practice", "Progress & Weak Topics", "Glossary"]
)

with learn_tab:
    for key, lesson in LESSONS.items():
        if topic_filter != "All" and lesson["topic"] != topic_filter:
            continue
        existing = progress_by_key.get(key)
        status = "✅" if key in passed else "📘"
        score_label = f" · {float(existing.score):.0f}%" if existing is not None else ""
        with st.expander(f"{status} {lesson['title']}{score_label}", expanded=key not in passed):
            st.write(lesson["summary"])
            for point in lesson["content"]:
                st.markdown(f"- {point}")

            with st.form(f"academy_quiz_{key}"):
                answers = []
                for index, (question, choices_list, _, _) in enumerate(lesson["questions"]):
                    answers.append(
                        st.radio(
                            question,
                            choices_list,
                            key=f"academy_{key}_{index}",
                        )
                    )
                submitted = st.form_submit_button("Submit quiz")

            if submitted:
                correct_count = 0
                review = []
                for index, (_, choices_list, correct_index, explanation) in enumerate(lesson["questions"]):
                    is_correct = answers[index] == choices_list[correct_index]
                    correct_count += int(is_correct)
                    review.append(
                        {
                            "answer": answers[index],
                            "correct": choices_list[correct_index],
                            "is_correct": is_correct,
                            "explanation": explanation,
                        }
                    )
                score = correct_count / len(lesson["questions"]) * 100
                execute(
                    """
                    INSERT INTO education_progress(
                        account_id, lesson_key, lesson_title, score, passed,
                        answers_json, completed_at_utc
                    ) VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(account_id, lesson_key) DO UPDATE SET
                        lesson_title=excluded.lesson_title,
                        score=excluded.score,
                        passed=excluded.passed,
                        answers_json=excluded.answers_json,
                        completed_at_utc=excluded.completed_at_utc
                    """,
                    (
                        account_id,
                        key,
                        lesson["title"],
                        score,
                        int(score >= PASS_SCORE),
                        json.dumps(review),
                        now(),
                    ),
                )
                st.success(
                    f"Score: {score:.0f}% — "
                    + ("passed" if score >= PASS_SCORE else "review the explanations and retry")
                )
                for index, item in enumerate(review, start=1):
                    icon = "✅" if item["is_correct"] else "❌"
                    st.write(f"{icon} Question {index}: {item['explanation']}")
                st.rerun()

with practice_tab:
    st.subheader("Guided trade scenario")
    scenarios = [
        {
            "key": "eurusd_cpi",
            "title": "EUR/USD before U.S. CPI",
            "prompt": "EUR/USD is near resistance. U.S. CPI is due in 20 minutes. The spread has widened and the engine says WAIT.",
            "choices": ["Buy immediately", "Sell with maximum leverage", "Wait for the release and reassess"],
            "correct": 2,
            "explanation": "Event risk, wider spreads, and a WAIT decision favor patience rather than forced exposure.",
        },
        {
            "key": "gbpusd_risk",
            "title": "GBP/USD position sizing",
            "prompt": "Your account is $10,000. You risk 0.5%, and your stop represents $0.50 per unit of position risk.",
            "choices": ["Risk $50 and size from the stop", "Risk $500 because confidence is high", "Remove the stop"],
            "correct": 0,
            "explanation": "The risk budget is $50. Position size must be calculated from that budget and the stop distance.",
        },
        {
            "key": "breakout_fomo",
            "title": "Breakout and FOMO",
            "prompt": "Price has already moved sharply beyond your planned entry. Your original reward-to-risk is no longer available.",
            "choices": ["Chase the move", "Skip it and wait for a new setup", "Double size to compensate"],
            "correct": 1,
            "explanation": "A missed entry is not a loss. Chasing usually worsens reward-to-risk and invalidates the original plan.",
        },
    ]
    selected_title = st.selectbox("Scenario", [item["title"] for item in scenarios])
    scenario = next(item for item in scenarios if item["title"] == selected_title)
    st.info(scenario["prompt"])
    with st.form("guided_scenario"):
        answer = st.radio("What is the best response?", scenario["choices"])
        reasoning = st.text_area("Explain your reasoning in one or two sentences")
        submitted = st.form_submit_button("Check scenario")
    if submitted:
        correct = answer == scenario["choices"][scenario["correct"]]
        execute(
            """
            INSERT INTO academy_scenarios(
                account_id, scenario_key, selected_answer, reasoning,
                score, feedback, attempted_at_utc
            ) VALUES(?,?,?,?,?,?,?)
            """,
            (
                account_id,
                scenario["key"],
                answer,
                reasoning.strip(),
                100.0 if correct else 0.0,
                scenario["explanation"],
                now(),
            ),
        )
        if correct:
            st.success("Correct. " + scenario["explanation"])
        else:
            st.error("Not quite. " + scenario["explanation"])

with progress_tab:
    st.subheader("Progress")
    rows = []
    for key, lesson in LESSONS.items():
        item = progress_by_key.get(key)
        rows.append(
            {
                "Lesson": lesson["title"],
                "Topic": lesson["topic"],
                "Score": float(item.score) if item is not None else 0.0,
                "Status": "Passed" if key in passed else "Not passed",
                "Last completed": item.completed_at_utc if item is not None else "—",
            }
        )
    progress_table = pd.DataFrame(rows)
    st.dataframe(progress_table, use_container_width=True, hide_index=True)

    weak = progress_table[progress_table["Score"] < PASS_SCORE]
    if weak.empty:
        st.success("No weak topics detected. Continue with guided practice and journaling.")
    else:
        st.subheader("Weak topics to review")
        for topic, group in weak.groupby("Topic"):
            st.markdown(f"**{topic}** — " + ", ".join(group["Lesson"].tolist()))

    attempts = query(
        "SELECT * FROM academy_scenarios WHERE account_id=? ORDER BY attempted_at_utc DESC LIMIT 20",
        (account_id,),
    )
    st.subheader("Recent scenario attempts")
    if attempts.empty:
        st.info("Complete a Guided Practice scenario to build your practice history.")
    else:
        st.dataframe(attempts, use_container_width=True, hide_index=True)

with glossary_tab:
    glossary = {
        "Base currency": "The first currency in a pair.",
        "Quote currency": "The second currency in a pair; it states the price of one unit of the base currency.",
        "Pip": "A standard small unit of price movement, commonly 0.0001 for major non-JPY pairs.",
        "Spread": "The difference between the bid and ask prices.",
        "Lot": "A standardized position-size unit: standard 100,000, mini 10,000, micro 1,000.",
        "Leverage": "Borrowed exposure that magnifies both gains and losses.",
        "Margin": "Collateral reserved to support a leveraged position.",
        "Stop loss": "A predefined exit intended to limit loss when the thesis is invalidated.",
        "Take profit": "A predefined price for realizing planned profit.",
        "Reward-to-risk": "Planned potential reward divided by planned loss.",
        "Slippage": "The difference between the expected execution price and the actual execution price.",
        "Drawdown": "A decline from an account-equity peak to a later low.",
    }
    search = st.text_input("Search glossary")
    for term, definition in glossary.items():
        if not search or search.lower() in term.lower() or search.lower() in definition.lower():
            st.markdown(f"**{term}:** {definition}")
