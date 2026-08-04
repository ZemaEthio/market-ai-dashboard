from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

exec(
    compile(
        (PROJECT_ROOT / "app" / "ui" / "dashboard.py").read_text(encoding="utf-8"),
        str(PROJECT_ROOT / "app" / "ui" / "dashboard.py"),
        "exec",
    )
)
