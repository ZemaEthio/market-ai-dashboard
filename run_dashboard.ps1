Set-Location $PSScriptRoot
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . ".\.venv\Scripts\Activate.ps1"
}
$env:MARKET_AI_DATABASE = ".\data\market_ai.db"
python -m streamlit run app\ui\dashboard.py
