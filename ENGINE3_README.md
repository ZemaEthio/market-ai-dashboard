# Engine 3 — Decision and Explanation Engine

Engine 3 reads the latest Engine 1 and Engine 2 rows for each symbol, combines them conservatively, and stores an auditable decision.

It never executes trades. A `wait` result is intentional whenever evidence is weak, stale, conflicting, or incomplete.

## Run

```powershell
python run_decision_engine.py --symbols "GC=F" "EURUSD=X" --interval 1h
python inspect_decision_analysis.py
```

## Output

- Combined bias and confidence
- Engine alignment
- Preferred action
- Bullish, bearish, and neutral scenarios
- No-trade reasons
- Risk level and data quality
- References to the exact Engine 1 and Engine 2 records used
