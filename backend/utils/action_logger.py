from datetime import datetime, UTC
from pathlib import Path
import json
import os


APP_DATA = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
if APP_DATA:
    LOG_DIR = Path(APP_DATA) / "NeuralAgent" / "logs"
else:
    LOG_DIR = Path(__file__).resolve().parents[1] / "logs"

ACTION_LOG_FILE = LOG_DIR / "actions.log"


def log_action(action: str, payload: dict | None = None, status: str = "ok") -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "status": status,
        "payload": payload or {},
    }
    with ACTION_LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
