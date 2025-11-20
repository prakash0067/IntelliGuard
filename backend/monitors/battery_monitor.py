# backend/monitors/battery_monitor.py
import time
import os
import re
import json
import subprocess
from .. import config, logger

try:
    import psutil
except Exception:
    psutil = None


class BatteryMonitor:
    """
    Collects battery information:
      - percent, plugged, secsleft (psutil)
      - attempts to read DesignCapacity / FullChargeCapacity via Windows powercfg battery report
      - returns useful keys for UI + battery predictor
    """

    def __init__(self):
        # path to store last generated battery report (HTML)
        self.reports_dir = config.REPORTS_DIR
        os.makedirs(self.reports_dir, exist_ok=True)
        self._last_report_path = os.path.join(self.reports_dir, "battery_report.html")

    def _run_powercfg_report(self):
        """
        Generate a fresh battery report (HTML) using Windows powercfg and return file path.
        If it fails, return None.
        """
        try:
            out_path = self._last_report_path
            # /output will overwrite existing file
            subprocess.run(["powercfg", "/batteryreport", "/output", out_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=10)
            if os.path.exists(out_path):
                return out_path
        except Exception as e:
            logger.log(f"[BatteryMonitor] powercfg failed: {e}")
        return None

    def _parse_battery_report(self, html_path):
        """
        Parse battery_report.html for Design Capacity and Full Charge Capacity (mWh).
        Returns dict or {} on failure:
            {"design_mwh": int, "full_charge_mwh": int, "cycle_count": int (maybe None)}
        Parsing is heuristic — works with typical Windows battery report HTML layout.
        """
        try:
            txt = ""
            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()

            # Typical table rows contain "DESIGN CAPACITY" or "DESIGN CAPACITY(mWh)" and numbers like "44000 mWh"
            # We'll look for "Design Capacity" and "Full Charge Capacity" nearby and extract numeric values
            # Use case-insensitive search
            txt_low = txt.lower()

            def find_capacity(key):
                idx = txt_low.find(key.lower())
                if idx == -1:
                    return None
                # look forward a few hundred chars
                slice_ = txt[idx: idx + 800]
                # find first number followed by 'mwh' or 'mwh' inside slice
                m = re.search(r"([0-9\,.]{4,})\s*mwh", slice_, flags=re.IGNORECASE)
                if m:
                    raw = m.group(1)
                    raw = raw.replace(",", "").replace(".", "")
                    try:
                        return int(raw)
                    except:
                        try:
                            return int(float(raw))
                        except:
                            return None
                # fallback: find numbers alone
                m2 = re.search(r"([0-9,]{4,})", slice_)
                if m2:
                    raw = m2.group(1).replace(",", "")
                    try:
                        return int(raw)
                    except:
                        return None
                return None

            design = find_capacity("design capacity")
            full = find_capacity("full charge capacity")
            # cycle count sometimes appears as "Cycle Count" or "Battery cycle count"
            cycle = None
            match_cycle = re.search(r"cycle count[^\d]*([0-9,]{1,6})", txt_low)
            if match_cycle:
                try:
                    cycle = int(match_cycle.group(1).replace(",", ""))
                except:
                    cycle = None

            # Voltage - try to find 'Voltage' near battery section
            volt = None
            mvolt = re.search(r"voltage[^\d]*(\d{3,5})\s*m?v", txt_low)
            if mvolt:
                try:
                    volt = int(mvolt.group(1))
                except:
                    volt = None

            result = {
                "design_mwh": design,
                "full_charge_mwh": full,
                "cycle_count": cycle,
                "voltage_mv": volt
            }
            return result
        except Exception as e:
            logger.log(f"[BatteryMonitor] parse error: {e}")
            return {}

    def sample(self):
        """
        Returns a dictionary with battery info.
        Key fields (may be None):
            present (bool)
            percent (0-100)
            secsleft (seconds or None)
            power_plugged (bool)
            design_capacity_mwh (int or None)
            full_charge_capacity_mwh (int or None)
            cycle_count (int or None)
            voltage_mv (int or None)
            timestamp (epoch)
        """
        ts = time.time()
        # Default structure
        bat = {
            "present": False,
            "percent": None,
            "secsleft": None,
            "power_plugged": None,
            "design_capacity_mwh": None,
            "full_charge_capacity_mwh": None,
            "cycle_count": None,
            "voltage_mv": None,
            "timestamp": ts
        }

        # 1) psutil basic info
        try:
            if psutil:
                sb = psutil.sensors_battery()
                if sb:
                    bat["present"] = True
                    try:
                        bat["percent"] = float(sb.percent)
                    except:
                        bat["percent"] = None
                    bat["secsleft"] = sb.secsleft
                    bat["power_plugged"] = bool(sb.power_plugged)
        except Exception as e:
            logger.log(f"[BatteryMonitor] psutil.sensors_battery error: {e}")

        # 2) Try powercfg-based detailed capacities (Windows)
        try:
            report = self._run_powercfg_report()
            if report:
                parsed = self._parse_battery_report(report)
                if parsed:
                    # design / full are expressed in mWh (Windows battery report)
                    if parsed.get("design_mwh"):
                        bat["design_capacity_mwh"] = parsed.get("design_mwh")
                    if parsed.get("full_charge_mwh"):
                        bat["full_charge_capacity_mwh"] = parsed.get("full_charge_mwh")
                    if parsed.get("cycle_count"):
                        bat["cycle_count"] = parsed.get("cycle_count")
                    if parsed.get("voltage_mv"):
                        bat["voltage_mv"] = parsed.get("voltage_mv")
        except Exception as e:
            logger.log(f"[BatteryMonitor] powercfg parse error: {e}")

        # Final timestamp
        bat["timestamp"] = ts
        return bat
