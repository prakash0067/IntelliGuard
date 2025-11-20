# backend/logger.py
import datetime
import os
from . import config

def _ensure_reports_dir():
    d = config.REPORTS_DIR
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def log(msg):
    _ensure_reports_dir()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(config.LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def append_report(text):
    _ensure_reports_dir()
    with open(config.REPORT_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")
