# ZEMA Market Overview Graphs Upgrade

Replaces the dashboard market chart with a two-panel interactive Plotly view.

## Added

- Candlestick/line chart selector
- Optional EMA 20/50/200 overlays
- Optional Bollinger Bands
- Toggleable support/resistance levels
- Entry, stop, target, and current-price lines
- RSI, volume, or return lower panel
- One-day, one-week, one-month, and full-history selectors
- Visible-window change, range, RSI, and EMA-structure metrics
- Expandable chart-reading guide for beginners

## Install

Copy `app/ui/dashboard.py` into the matching project path, replacing the existing file.

Run:

```powershell
python -m py_compile .\app\ui\dashboard.py
python -m streamlit run .\streamlit_app.py --server.port 8501
```
