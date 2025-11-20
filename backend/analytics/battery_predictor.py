# backend/analytics/battery_predictor.py
import os
import time
import datetime
import json
from .. import config, logger

# Optional numpy for best-fit
try:
    import numpy as np
except Exception:
    np = None


class BatteryPredictor:
    """
    Uses true capacity values (FullChargeCapacity & DesignCapacity) logged over days
    to compute wear percentage, trend, and projections.
    """

    def __init__(self, health_log_fname=None, min_points=3):
        self.min_points = min_points
        self.health_log_fname = health_log_fname or os.path.join(config.REPORTS_DIR, "battery_health_log.json")
        # ensure reports dir exists
        try:
            os.makedirs(config.REPORTS_DIR, exist_ok=True)
        except:
            pass

    def _load_log(self):
        if not os.path.exists(self.health_log_fname):
            return []
        try:
            with open(self.health_log_fname, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.log(f"[BatteryPredictor] failed to read log: {e}")
        return []

    def _save_log(self, logs):
        try:
            with open(self.health_log_fname, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            logger.log(f"[BatteryPredictor] failed to write log: {e}")

    def append_daily_entry(self, date_str, design_mwh, full_mwh, cycle_count=None, voltage=None):
        """
        Append or update today's entry in the health log.
        date_str: "YYYY-MM-DD"
        design_mwh, full_mwh: integers (mWh) or None
        """
        logs = self._load_log()
        # find existing entry for date
        existing = None
        for e in logs:
            if e.get("date") == date_str:
                existing = e
                break

        wear = None
        if design_mwh and full_mwh and design_mwh > 0:
            wear = round((1.0 - (full_mwh / design_mwh)) * 100.0, 3)

        entry = {
            "date": date_str,
            "design_mwh": design_mwh,
            "full_mwh": full_mwh,
            "wear_pct": wear,
            "cycle_count": cycle_count,
            "voltage_mv": voltage
        }

        if existing:
            # update fields if newer values present
            existing.update(entry)
        else:
            logs.append(entry)

        # sort by date ascending
        try:
            logs.sort(key=lambda x: x.get("date"))
        except:
            pass

        self._save_log(logs)
        return entry

    def predict(self, months_ahead=6):
        """
        Read log and produce trend + projection.
        Returns dict:
          weekly_degradation_percent,
          projected_health_percent (percentage of original design),
          health_score (0-100),
          trend_slope_wear_per_day,
          notes,
          entries (log)
        """
        logs = self._load_log()
        # Only keep entries that have wear_pct
        entries = [e for e in logs if e.get("wear_pct") is not None and e.get("design_mwh")]
        if len(entries) < self.min_points:
            return {
                "weekly_degradation_percent": None,
                "projected_health_percent": None,
                "health_score": None,
                "trend_slope_wear_per_day": None,
                "notes": f"Need at least {self.min_points} daily capacity samples (found {len(entries)}).",
                "entries": logs
            }

        # Create arrays: x = days since first sample, y = wear_pct
        first_date = datetime.datetime.strptime(entries[0]["date"], "%Y-%m-%d")
        x = []
        y = []
        for e in entries:
            try:
                d = datetime.datetime.strptime(e["date"], "%Y-%m-%d")
                x_days = (d - first_date).days
                x.append(x_days)
                y.append(float(e["wear_pct"]))
            except Exception:
                continue

        if len(x) < self.min_points:
            return {
                "weekly_degradation_percent": None,
                "projected_health_percent": None,
                "health_score": None,
                "trend_slope_wear_per_day": None,
                "notes": "Insufficient usable log entries after parsing.",
                "entries": logs
            }

        # Fit slope (wear percent per day)
        slope_per_day = None
        intercept = None
        try:
            if np is not None:
                p = np.polyfit(x, y, 1)
                slope_per_day = float(p[0])
                intercept = float(p[1])
            else:
                # simple linear fit (least squares)
                n = len(x)
                sx = sum(x)
                sy = sum(y)
                sxy = sum(i*j for i,j in zip(x,y))
                sxx = sum(i*i for i in x)
                denom = (n * sxx - sx*sx)
                if denom != 0:
                    slope_per_day = (n * sxy - sx * sy) / denom
                    intercept = (sy - slope_per_day * sx) / n
        except Exception as e:
            logger.log(f"[BatteryPredictor] regression failed: {e}")

        if slope_per_day is None:
            return {
                "weekly_degradation_percent": None,
                "projected_health_percent": None,
                "health_score": None,
                "trend_slope_wear_per_day": None,
                "notes": "Failed to compute degradation slope.",
                "entries": logs
            }

        # Weekly degradation percent (wear increase per week)
        weekly_degradation = slope_per_day * 7.0

        # Project health after months_ahead
        months = months_ahead
        days = months * 30.4375  # average month days
        projected_wear = (slope_per_day * ( (datetime.datetime.now() - first_date).days + days )) + intercept
        # Projected full_capacity fraction = 1 - wear/100
        # But we need design capacity: use latest known design in log
        latest = entries[-1]
        design = latest.get("design_mwh")
        latest_full = latest.get("full_mwh")
        if design and projected_wear is not None:
            projected_full_mwh = design * (1.0 - (projected_wear/100.0))
            projected_health_pct = max(0.0, min(100.0, (projected_full_mwh / design) * 100.0))
        else:
            projected_full_mwh = None
            projected_health_pct = None

        # health score interpret: higher = better; simple: 100 - projected_wear (clamped)
        health_score = None
        if projected_health_pct is not None:
            health_score = int(round(projected_health_pct))

        notes = (
            f"Computed slope: {slope_per_day:.6f} % wear per day.\n"
            f"Weekly wear increase (approx): {weekly_degradation:.4f}%.\n"
            "Wear % = 100 * (1 - FullChargeCapacity / DesignCapacity)."
        )

        return {
            "weekly_degradation_percent": round(weekly_degradation, 6),
            "projected_health_percent": round(projected_health_pct, 2) if projected_health_pct is not None else None,
            "health_score": health_score,
            "trend_slope_wear_per_day": round(slope_per_day, 8),
            "notes": notes,
            "entries": logs
        }
