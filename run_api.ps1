Set-Location $PSScriptRoot
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . ".\.venv\Scripts\Activate.ps1"
}
$env:MARKET_AI_DATABASE = ".\data\market_ai.db"
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
