import json
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent / "thresholds.json"

DEFAULT_THRESHOLDS = {
    "critico": {"temp": 32.0, "hum": 40.0},
    "medio": {"temp": 30.0, "hum": 50.0}
}

def load_thresholds() -> dict:
    if not CONFIG_FILE.exists():
        save_thresholds(DEFAULT_THRESHOLDS)
        return DEFAULT_THRESHOLDS
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_thresholds(thresholds: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(thresholds, f, indent=4)
