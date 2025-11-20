# backend/config.py
import os

# Thresholds
CPU_THRESHOLD = 85         # percent
RAM_THRESHOLD = 85         # percent
CHECK_INTERVAL = 5        # seconds between regular checks
CONSECUTIVE_LIMIT = 5      # number of consecutive checks before alert

# Cleanup configuration (default)
SINGLE_RULE_DAYS = 15

# MULTI_RULES kept if you later want per-extension rules (not used in Option1)
MULTI_RULES = {
    # ".tmp": 2,
    # "__default__": 15
}

# When to run daily cleanup (24-hour clock)
CLEANUP_HOUR = 9    # 9 AM local time
CLEANUP_MINUTE = 0

# Paths
HOME = os.path.expanduser("~")
DOWNLOADS_PATH = os.path.join(HOME, "Downloads")
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
REPORT_FILE = os.path.join(REPORTS_DIR, "cleanup_report.txt")
LOG_FILE = os.path.join(BASE_DIR, "system.log")

# History sizes
HISTORY_LEN = 60  # keep last N samples for charts

# Battery
BATTERY_LOW_THRESHOLD = 20  # percent
BATTERY_OVERCHARGE_THRESHOLD = 95  # percent

# UI update interval (ms)
UI_UPDATE_INTERVAL = 1000
