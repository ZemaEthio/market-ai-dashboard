# Historical Backtesting Engine — Decision Replay v1

This release replays **stored historical BUY/SELL decisions** against later
completed candles and writes the results into:

- `backtest_runs`
- `backtest_trades`
- `backtest_metrics`

## Conservative rules

- Entry occurs at the next candle open after the stored decision.
- Spread and slippage are applied at entry and exit.
- When stop and target are both touched in the same hourly candle, stop wins.
- A trade exits after 24 candles if neither stop nor target is reached.
- Position size risks 0.5% of the evolving simulated balance.
- Historical news is not reconstructed in this version.
- The engine does not recreate past decisions using future knowledge.

## Run

```powershell
python .\run_historical_backtest.py --symbol "EURUSD=X" --interval "1h"
python .\run_historical_backtest.py --symbol "GC=F" --interval "1h"
```

Optional date range:

```powershell
python .\run_historical_backtest.py `
  --symbol "EURUSD=X" `
  --interval "1h" `
  --start "2026-01-01T00:00:00+00:00" `
  --end "2026-08-01T00:00:00+00:00"
```

The number of simulated trades is limited by the number of historical decision
records already stored in `decision_analyses`.
