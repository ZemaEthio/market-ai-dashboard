$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if (-not (Test-Path ".env")) { Copy-Item .env.example .env }
python collect_data.py --symbols "GC=F" "EURUSD=X" --period 6mo --interval 1h
python inspect_database.py
