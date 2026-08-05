# ZEMA Forex Academy

## What was added

- Dedicated Streamlit page: `pages/2_Forex_Academy.py`
- Eight beginner modules covering foundations, mechanics, risk, sessions, technicals, news, planning, and psychology
- Quizzes with explanations and an 80% pass score
- Guided trade scenarios with saved feedback
- Progress, weak-topic detection, glossary, and readiness scoring
- Paper Trading gate connected to the three core Academy modules
- New `academy_scenarios` table created by `init_paper_trading.py`

## Install

```powershell
Set-Location "E:\MarketAI"
.\.venv\Scripts\Activate.ps1
python .\init_paper_trading.py
python -m streamlit run .\streamlit_app.py --server.port 8501
```

Open the **Forex Academy** page from the Streamlit sidebar.

## Core lessons required for Paper Trading

1. Forex Foundations
2. Risk Management
3. Fundamental and News Analysis

This feature is for education and simulated paper trading only.
