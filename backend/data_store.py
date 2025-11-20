# backend/data_store.py
import json
import os
import datetime
from . import config, logger

def _ensure_reports_dir():
    """Ensure the reports directory exists."""
    try:
        if not os.path.exists(config.REPORTS_DIR):
            os.makedirs(config.REPORTS_DIR, exist_ok=True)
    except Exception as e:
        logger.log(f"[data_store] Failed to create reports directory: {e}")


def _get_today_filename():
    """
    Returns today's JSON file path:
    reports/daily_samples_YYYY-MM-DD.json
    """
    today = datetime.date.today().strftime("%Y-%m-%d")
    return os.path.join(config.REPORTS_DIR, f"daily_samples_{today}.json")


def append_sample(sample_dict):
    """
    Adds a runtime monitoring sample to today's JSON file.

    sample_dict example:
    {
        "ts": timestamp,
        "cpu": 55.0,
        "ram": 45.0,
        "net_bytes_delta": 12000,
        "top_app": "chrome.exe",
        "battery_event": None
    }
    """
    _ensure_reports_dir()
    fname = _get_today_filename()

    # Load existing data (or create new)
    data = {"samples": []}

    if os.path.exists(fname):
        try:
            with open(fname, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"samples": []}

    # Ensure structure
    if "samples" not in data:
        data["samples"] = []

    # Add new sample
    data["samples"].append(sample_dict)

    # Write back
    try:
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.log(f"[data_store] Failed to write daily sample: {e}")


def load_today():
    """
    Returns:
        {
            "samples": [...]
        }
    If missing or corrupted, returns {"samples": []}
    """
    _ensure_reports_dir()
    fname = _get_today_filename()

    if not os.path.exists(fname):
        return {"samples": []}

    try:
        with open(fname, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.log(f"[data_store] Failed to read today's sample file: {e}")
        return {"samples": []}
