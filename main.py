# main.py
import sys
import threading
import time
import datetime
import os
from PySide6 import QtWidgets

# Core backend modules
from backend.monitors.system_monitor import SystemMonitor
from backend.monitors.battery_monitor import BatteryMonitor
from backend.cleaners.downloads_cleaner import DownloadsCleaner

from backend import config, logger
from ui.main_window import MainWindow


# ============================================================
#                    BACKEND CONTROLLER
# ============================================================
class BackendController:
    def __init__(self):
        # Monitors
        self.sysmon = SystemMonitor()
        self.batmon = BatteryMonitor()
        self.cleaner = DownloadsCleaner()

        # Extra monitors
        from backend.monitors.disk_monitor import DiskMonitor
        from backend.monitors.network_monitor import NetworkMonitor
        self.diskmon = DiskMonitor()
        self.netmon = NetworkMonitor()

        # Analytics modules
        from backend.analytics.battery_predictor import BatteryPredictor
        from backend.analytics.stability_analyzer import StabilityAnalyzer
        from backend.analytics.daily_story import DailyStory

        self.batt_predictor = BatteryPredictor()
        self.stability_analyzer = StabilityAnalyzer()
        self.daily_story_gen = DailyStory()

        # Shared state
        self.lock = threading.Lock()
        self.latest = None
        self.running = True
        self.cleanup_days = config.SINGLE_RULE_DAYS
        self.ui_interval_ms = config.UI_UPDATE_INTERVAL

        # Histories
        self.proc_history = {}          # (pid, name) -> list of samples
        self.battery_history = []       # for battery predictor

        # Start background worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()


    # ============================================================
    #                         WORKER LOOP
    # ============================================================
    def _worker_loop(self):

        # Warm up psutil
        try:
            import psutil
            psutil.cpu_percent(interval=0.1)
        except:
            pass

        last_daily_run = None

        while self.running:
            try:
                # --------------------------------------------------
                # 1) Collect Samples
                # --------------------------------------------------
                sys_info = self.sysmon.sample()
                bat_info = self.batmon.sample()
                disk_info = self.diskmon.sample()
                net_info = self.netmon.sample()

                now_ts = time.time()
                ts_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # --------------------------------------------------
                # 2) Stability Analyzer – Process History
                # --------------------------------------------------
                for proc in sys_info.get("top_cpu", []):
                    pid = proc.get("pid")
                    name = proc.get("name") or str(pid)
                    key = (pid, name)

                    entry = {
                        "ts": now_ts,
                        "cpu": proc.get("cpu_percent", 0.0),
                        "mem": proc.get("memory_percent", 0.0),
                        "io_read": 0,
                        "io_write": 0,
                        "net_sent": 0,
                        "net_recv": 0
                    }

                    hist_list = self.proc_history.setdefault(key, [])
                    hist_list.append(entry)

                    # Limit history length
                    if len(hist_list) > config.HISTORY_LEN:
                        hist_list.pop(0)

                # --------------------------------------------------
                # 3) Battery Percentage History (for chart + ML)
                # --------------------------------------------------
                if bat_info.get("present"):
                    pct = bat_info.get("percent") or 0
                    self.battery_history.append((now_ts, pct))

                    if len(self.battery_history) > 600:
                        self.battery_history = self.battery_history[-600:]

                # --------------------------------------------------
                # 4) Daily Battery Health Logging
                # --------------------------------------------------
                try:
                    fcc = bat_info.get("full_charge_capacity_mwh")
                    design = bat_info.get("design_capacity_mwh")
                    cycle = bat_info.get("cycle_count")
                    volt = bat_info.get("voltage_mv")

                    if design and fcc:
                        today_str = datetime.date.today().strftime("%Y-%m-%d")
                        self.batt_predictor.append_daily_entry(
                            today_str,
                            design_mwh=design,
                            full_mwh=fcc,
                            cycle_count=cycle,
                            voltage=volt
                        )

                except Exception as e:
                    logger.log(f"[BackendController] battery log error: {e}")

                # --------------------------------------------------
                # 5) Merge All Data for UI
                # --------------------------------------------------
                merged = {
                    "cpu": sys_info["cpu"],
                    "ram": sys_info["ram"],
                    "swap": sys_info["swap"],

                    "top_cpu": sys_info["top_cpu"],
                    "top_mem": sys_info["top_mem"],

                    "cpu_hits": sys_info["cpu_hits"],
                    "ram_hits": sys_info["ram_hits"],

                    "cpu_history": sys_info["cpu_history"],
                    "ram_history": sys_info["ram_history"],

                    "peak_cpu": sys_info.get("peak_cpu"),
                    "peak_cpu_time": sys_info.get("peak_cpu_time"),
                    "peak_ram": sys_info.get("peak_ram"),
                    "peak_ram_time": sys_info.get("peak_ram_time"),

                    "battery": bat_info,
                    "disk": disk_info,
                    "network": net_info,

                    "timestamp": now_ts,
                    "timestamp_str": ts_str
                }

                # Thread-safe latest data update
                with self.lock:
                    self.latest = merged

                # --------------------------------------------------
                # 6) Save Sample for Daily Story
                # --------------------------------------------------
                try:
                    from backend.data_store import append_sample
                    sample = {
                        "ts": now_ts,
                        "cpu": sys_info["cpu"],
                        "ram": sys_info["ram"],
                        "net_bytes_delta": (
                            net_info.get("bytes_recv_total", 0)
                            + net_info.get("bytes_sent_total", 0)
                        ),
                        "top_app": sys_info["top_cpu"][0].get("name") if sys_info["top_cpu"] else None,
                        "battery_event": None
                    }
                    append_sample(sample)
                except Exception as e:
                    logger.log(f"[BackendController] Failed to save daily sample: {e}")

                # --------------------------------------------------
                # 7) Scheduled Daily Cleanup
                # --------------------------------------------------
                now = datetime.datetime.now()
                if now.hour == config.CLEANUP_HOUR and now.minute == config.CLEANUP_MINUTE:
                    today = now.date()
                    if last_daily_run != today:
                        logger.log("Scheduled cleanup triggered.")
                        self.cleaner.run_cleanup(self.cleanup_days)
                        last_daily_run = today
                        time.sleep(61)

            except Exception as e:
                logger.log(f"[BackendController] Worker loop error: {e}")

            # Sleep interval (5 sec or whatever you set)
            time.sleep(config.CHECK_INTERVAL)


    # ============================================================
    #                         PUBLIC METHODS
    # ============================================================
    def get_latest(self):
        with self.lock:
            return self.latest


    # ---------- Cleanup ----------
    def set_cleanup_days(self, days):
        try:
            d = int(days)
            if d < 0:
                return False
            self.cleanup_days = d
            logger.log(f"Cleanup interval updated to {d} days.")
            return True
        except:
            return False

    def get_cleanup_days(self):
        return int(self.cleanup_days)

    def run_cleanup_now(self):
        return self.cleaner.run_cleanup(self.cleanup_days)


    # ---------- Battery Prediction ----------
    def get_battery_prediction(self, months=6):
        try:
            return self.batt_predictor.predict(months_ahead=months)
        except Exception as e:
            logger.log(f"Battery predictor error: {e}")
            return {}


    # ---------- Stability Analyzer ----------
    def get_stability_scores(self):
        scores = []
        try:
            for (pid, name), hist in self.proc_history.items():
                if not hist:
                    continue
                result = self.stability_analyzer.score_process(hist)
                scores.append({
                    "pid": pid,
                    "name": name,
                    "score": result.get("score"),
                    "breakdown": result.get("breakdown"),
                })

            scores.sort(key=lambda x: (x["score"] is None, x["score"]), reverse=True)

        except Exception as e:
            logger.log(f"Stability analyzer error: {e}")

        return scores


    # ---------- Daily Story ----------
    def generate_daily_story(self):
        try:
            from backend.data_store import load_today

            file_data = load_today()
            samples = file_data.get("samples", [])

            # Aggregate for daily story
            aggregated = {
                "cpu": [],
                "ram": [],
                "network_bytes": [],
                "battery_events": [],
                "app_usage": {}
            }

            for s in samples:
                aggregated["cpu"].append(s.get("cpu", 0))
                aggregated["ram"].append(s.get("ram", 0))
                aggregated["network_bytes"].append(s.get("net_bytes_delta", 0))

                app = s.get("top_app")
                if app:
                    aggregated["app_usage"][app] = aggregated["app_usage"].get(app, 0) + 1

                if s.get("battery_event"):
                    aggregated["battery_events"].append(s["battery_event"])

            return self.daily_story_gen.generate(aggregated)

        except Exception as e:
            logger.log(f"Daily story error: {e}")
            return "Failed to generate story.", {}


    # ---------- Stop Worker Thread ----------
    def stop(self):
        self.running = False
        try:
            self.worker_thread.join(timeout=2)
        except:
            pass


# ============================================================
#                       MAIN APPLICATION
# ============================================================
def main():
    # Ensure 'reports' folder exists
    reports_path = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(reports_path, exist_ok=True)

    app = QtWidgets.QApplication(sys.argv)

    backend = BackendController()
    ui_file = os.path.join(os.path.dirname(__file__), "ui", "main_window.ui")

    window = MainWindow(backend, ui_file)
    window.show()

    try:
        rv = app.exec()
    finally:
        backend.stop()

    sys.exit(rv)


if __name__ == "__main__":
    main()
