# ui/main_window.py
import os
import winreg
from PySide6 import QtCore, QtGui, QtWidgets, QtUiTools
from PySide6.QtCore import QFile, QSize, Qt, QPropertyAnimation
from PySide6.QtGui import QIcon, QTransform

import matplotlib

from backend.cleaners.duplicate_finder import DuplicateFinder
matplotlib.use("QtAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas


# -----------------------------------------------------
# SYSTEM DARK MODE DETECTION
# -----------------------------------------------------
def system_prefers_dark():
    """Detects Windows system dark mode preference."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0  # 0 = dark mode enabled
    except Exception:
        return False


# -----------------------------------------------------
#               MATPLOTLIB CANVAS WRAPPER
# -----------------------------------------------------
class MplCanvas(FigureCanvas):
    def __init__(self, width=4, height=2.4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)


# -----------------------------------------------------
#             ANIMATED DASHBOARD CARD BUTTON
# -----------------------------------------------------
class AnimatedButton(QtWidgets.QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scale = 1.0
        self.anim = QPropertyAnimation(self, b"scale")
        self.anim.setDuration(140)
        self.anim.setEasingCurve(QtCore.QEasingCurve.OutQuad)

    def getScale(self):
        return self._scale

    def setScale(self, value):
        self._scale = value
        transform = QTransform()
        transform.scale(value, value)
        self.setGraphicsEffect(None)
        self.setFixedSize(self.sizeHint() * value)

    scale = QtCore.Property(float, getScale, setScale)

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._scale)
        self.anim.setEndValue(1.07)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._scale)
        self.anim.setEndValue(1.00)
        self.anim.start()
        super().leaveEvent(event)


# -----------------------------------------------------
#                    MAIN WINDOW
# -----------------------------------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, backend, ui_path):
        super().__init__()
        self.backend = backend

        # Load UI
        loader = QtUiTools.QUiLoader()
        ui_file = QFile(ui_path)
        if not ui_file.open(QFile.ReadOnly):
            raise RuntimeError(f"Failed to open UI file: {ui_path}")

        self.ui = loader.load(ui_file)
        ui_file.close()

        if self.ui is None:
            raise RuntimeError("Failed to load UI")

        self.setCentralWidget(self.ui)

        # Paths
        base_dir = os.path.dirname(ui_path)
        self.icons_dir = os.path.join(base_dir, "icons")

        # Theme flag
        self.dark_mode = False

        # Setup UI
        self._setup_navbar()
        self._map_buttons_to_actions()
        self._setup_plots()
        self._setup_cleanup_widgets()
        self._apply_animated_icons()
        self.apply_theme()

        # Start backend update timer
        self._init_backend_timer()
        
        self.dup_finder = DuplicateFinder()
        self._setup_duplicate_ui()

    def _setup_duplicate_ui(self):
        self.tableDuplicates = self.ui.findChild(QtWidgets.QTableWidget, "tableDuplicates")
        self.btnScanDuplicates = self.ui.findChild(QtWidgets.QPushButton, "btnScanDuplicates")
        self.btnDeleteDuplicates = self.ui.findChild(QtWidgets.QPushButton, "btnDeleteDuplicates")

        if self.btnScanDuplicates:
            self.btnScanDuplicates.clicked.connect(self._scan_duplicates)

        if self.btnDeleteDuplicates:
            self.btnDeleteDuplicates.clicked.connect(self._delete_duplicates)

    def _scan_duplicates(self):
        dups = self.dup_finder.find_duplicates()

        print("Duplicates found:", len(dups))
        self.tableDuplicates.setRowCount(len(dups))

        for i, item in enumerate(dups):
            chk = QtWidgets.QTableWidgetItem()
            chk.setCheckState(Qt.Checked)   # Select all by default
            self.tableDuplicates.setItem(i, 0, chk)

            self.tableDuplicates.setItem(i, 1, QtWidgets.QTableWidgetItem(item["filename"]))
            self.tableDuplicates.setItem(i, 2, QtWidgets.QTableWidgetItem(item["size"]))
            self.tableDuplicates.setItem(i, 3, QtWidgets.QTableWidgetItem(item["modified"]))

            # Store filepath
            self.tableDuplicates.item(i, 0).setData(Qt.UserRole, item["filepath"])

    def _delete_duplicates(self):
        rows = self.tableDuplicates.rowCount()
        files_to_delete = []

        for i in range(rows):
            chk = self.tableDuplicates.item(i, 0)
            if chk.checkState() == Qt.Checked:
                fp = chk.data(Qt.UserRole)
                files_to_delete.append(fp)

        if not files_to_delete:
            QtWidgets.QMessageBox.information(self, "Duplicates", "No files selected.")
            return

        confirm = QtWidgets.QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete {len(files_to_delete)} selected files?"
        )

        if confirm != QtWidgets.QMessageBox.Yes:
            return

        deleted = self.dup_finder.delete_files(files_to_delete)

        QtWidgets.QMessageBox.information(
            self,
            "Duplicate Cleanup",
            f"Deleted {len(deleted)} duplicate files."
        )

        self._scan_duplicates()

    # -----------------------------------------------------
    #                  NAVIGATION BAR
    # -----------------------------------------------------
    def _setup_navbar(self):
        self.btnBack = self.ui.findChild(QtWidgets.QPushButton, "btnBack")
        self.btnBack.clicked.connect(self._go_back_dashboard)
        self.btnBack.setVisible(False)

    def _go_back_dashboard(self):
        self._select_page("pageDashboard")
        self.btnBack.setVisible(False)


    # -----------------------------------------------------
    #            BUTTON → ACTIONS CONNECTOR
    # -----------------------------------------------------
    def _map_buttons_to_actions(self):
        self._button_actions = {
            "btnCardCleanup": lambda: self._select_page("pageCleanup"),
            "btnCardMonitor": lambda: self._select_page("pageMonitor"),
            "btnCardBattery": self._open_battery_predictor,
            "btnCardStability": self._open_stability_scores,
            "btnCardStorage": lambda: self._select_page("pageStorage"),
            "btnCardNetwork": lambda: self._select_page("pageNetwork"),
            "btnCardStory": self._open_daily_story,
            "btnCardSettings": self._open_settings_placeholder,
        }

    def _select_page(self, page_name):
        stacked = self.ui.findChild(QtWidgets.QStackedWidget, "stackedWidget")
        if not stacked:
            return

        for i in range(stacked.count()):
            w = stacked.widget(i)
            if w.objectName() == page_name:
                stacked.setCurrentIndex(i)
                self.btnBack.setVisible(page_name != "pageDashboard")
                return


    # -----------------------------------------------------
    #               ANIMATED DASHBOARD CARDS
    # -----------------------------------------------------
    def _apply_animated_icons(self):
        icon_map = {
            "btnCardCleanup": "cleanup.png",
            "btnCardMonitor": "cpu.png",
            "btnCardBattery": "battery.png",
            "btnCardStability": "stability.png",
            "btnCardStorage": "storage.png",
            "btnCardNetwork": "network.png",
            "btnCardStory": "story.png",
            "btnCardSettings": "settings.png",
        }

        for btn_name, icon_filename in icon_map.items():
            old_btn = self.ui.findChild(QtWidgets.QToolButton, btn_name)
            if not old_btn:
                continue

            layout = old_btn.parentWidget().layout()

            # Find row, col in QGridLayout
            row = col = -1
            if isinstance(layout, QtWidgets.QGridLayout):
                for r in range(layout.rowCount()):
                    for c in range(layout.columnCount()):
                        item = layout.itemAtPosition(r, c)
                        if item and item.widget() == old_btn:
                            row, col = r, c
                            break

            # New animated button
            anim_btn = AnimatedButton(self.ui)
            anim_btn.setObjectName(btn_name)
            anim_btn.setText(old_btn.text())
            anim_btn.setToolButtonStyle(old_btn.toolButtonStyle())
            anim_btn.setIconSize(QSize(96, 96))

            path = os.path.join(self.icons_dir, icon_filename)
            if os.path.exists(path):
                anim_btn.setIcon(QIcon(path))

            # Style dynamically applied in theme function

            old_btn.hide()

            if row >= 0 and col >= 0:
                layout.addWidget(anim_btn, row, col)
            else:
                idx = layout.indexOf(old_btn)
                layout.insertWidget(idx, anim_btn)

            if btn_name in self._button_actions:
                anim_btn.clicked.connect(self._button_actions[btn_name])


    # -----------------------------------------------------
    #                   THEME MANAGEMENT
    # -----------------------------------------------------
    def apply_theme(self):
        self.dark_mode = system_prefers_dark()

        if self.dark_mode:
            self.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                    color: #e6e6e6;
                }

                QLabel {
                    color: #e6e6e6;
                }
                QLabel#labelAppName {
                    color: white;
                    font-size: 28px;
                    font-weight: bold;
                }
                QLabel#labelSubtitle {
                    color: #bfbfbf;
                }

                QPushButton {
                    background-color: #333;
                    color: white;
                    border: 1px solid #444;
                    border-radius: 6px;
                    padding: 6px 10px;
                }
                QPushButton:hover {
                    background-color: #444;
                }

                QPushButton#btnBack {
                    background-color: #2f2f2f;
                    color: white;
                    border: 1px solid #444;
                    border-radius: 8px;
                    padding: 6px 12px;
                }
                QPushButton#btnBack:hover {
                    background-color: #3a3a3a;
                }

                QToolButton {
                    background: #2a2a2a;
                    border-radius: 22px;
                    padding: 15px;
                    border: 2px solid #383838;
                    color: white;
                    font-size: 14px;
                    font-weight: 600;
                }
                QToolButton:hover { 
                    background: #333; 
                }

                QComboBox {
                    background: #2b2b2b;
                    border: 1px solid #3a3a3a;
                    padding: 4px;
                    color: white;
                }
                
                QTableWidget::indicator:checked {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #4a90e2;
                    background: #4a90e2;
                }

                QTableWidget::item:checked {
                    color: #4a90e2;
                    font-weight: bold;
                }

                QLabel#labelCurrentDown,
                QLabel#labelCurrentUp {
                    font-size: 16px;
                    color: #4fc3f7;
                }

                QLabel#labelPeakDown,
                QLabel#labelPeakUp {
                    font-size: 14px;
                    color: #aaaaaa;
                }

                QLabel#labelAdapter {
                    font-size: 14px;
                    color: #dddddd;
                }

                QTextEdit {
                    background: #222;
                    border: 1px solid #444;
                    color: #ddd;
                }
            """)

        else:
            self.setStyleSheet("""
                QWidget { background-color: white; color: #222; }
                QLabel { color: #222; }
                QPushButton {
                    background-color: #f1f1f1;
                    color: black;
                    border-radius: 6px;
                    padding: 6px 10px;
                }
                QPushButton:hover { background-color: #e5e5e5; }
            """)


    # -----------------------------------------------------
    #                     CHART SETUP
    # -----------------------------------------------------
    def _setup_plots(self):
        cpu_p = self.ui.findChild(QtWidgets.QWidget, "cpuCanvas")
        ram_p = self.ui.findChild(QtWidgets.QWidget, "ramCanvas")
        disk_p = self.ui.findChild(QtWidgets.QWidget, "diskCanvas")
        net_p = self.ui.findChild(QtWidgets.QWidget, "networkCanvas")

        self.cpu_canvas = MplCanvas()
        self.ram_canvas = MplCanvas()
        self.disk_canvas = MplCanvas()
        self.net_canvas = MplCanvas()

        for widget, canvas in [
            (cpu_p, self.cpu_canvas),
            (ram_p, self.ram_canvas),
            (disk_p, self.disk_canvas),
            (net_p, self.net_canvas),
        ]:
            layout = QtWidgets.QVBoxLayout(widget)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.addWidget(canvas)


    # -----------------------------------------------------
    #              CLEANUP PAGE WIDGETS
    # -----------------------------------------------------
    def _setup_cleanup_widgets(self):
        combo = self.ui.findChild(QtWidgets.QComboBox, "comboCleanupDays")
        if combo:
            combo.clear()
            for d in [1, 3, 5, 7, 10, 15, 20, 30]:
                combo.addItem(str(d))
            combo.setCurrentText(str(self.backend.get_cleanup_days()))

        btn_apply = self.ui.findChild(QtWidgets.QPushButton, "btnApplyCleanup")
        btn_run = self.ui.findChild(QtWidgets.QPushButton, "btnRunCleanup")
        self.cleanup_report = self.ui.findChild(QtWidgets.QTextEdit, "textCleanupReport")

        if btn_apply:
            btn_apply.clicked.connect(self._apply_cleanup_choice)
        if btn_run:
            btn_run.clicked.connect(self._run_cleanup_now) 


    def _apply_cleanup_choice(self):
        combo = self.ui.findChild(QtWidgets.QComboBox, "comboCleanupDays")
        days = combo.currentText()
        ok = self.backend.set_cleanup_days(days)
        if ok:
            self.cleanup_report.append(f"[User] Cleanup interval set to {days} days")
        else:
            self.cleanup_report.append("[Error] Invalid cleanup value")


    def _run_cleanup_now(self):
        res = self.backend.run_cleanup_now()
        deleted = res.get("deleted", [])

        if deleted:
            self.cleanup_report.append(
                f"[Cleanup] Deleted {len(deleted)} files:"
            )
            for f in deleted:
                self.cleanup_report.append(f"• {f}")
        else:
            self.cleanup_report.append("[Cleanup] No files deleted")


    # -----------------------------------------------------
    #            BACKEND → UI UPDATE LOOP
    # -----------------------------------------------------
    def _init_backend_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(self.backend.ui_interval_ms)
        self.timer.timeout.connect(self.update_from_backend)
        self.timer.start()


    def update_from_backend(self):
        data = self.backend.get_latest()
        if not data:
            return
        
        # 1️⃣ ADD THIS BLOCK HERE --------------------------
        import datetime

        cpu_peak = data.get("peak_cpu")
        cpu_peak_time = data.get("peak_cpu_time")

        ram_peak = data.get("peak_ram")
        ram_peak_time = data.get("peak_ram_time")

        cpu_stats_label = self.ui.findChild(QtWidgets.QLabel, "labelCpuStats")
        ram_stats_label = self.ui.findChild(QtWidgets.QLabel, "labelRamStats")

        if cpu_stats_label and cpu_peak is not None and cpu_peak_time:
            cpu_stats_label.setText(
                f"🔥 CPU Peak: {cpu_peak:.1f}% at "
                f"{datetime.datetime.fromtimestamp(cpu_peak_time).strftime('%H:%M:%S')}"
            )

        if ram_stats_label and ram_peak is not None and ram_peak_time:
            ram_stats_label.setText(
                f"💾 RAM Peak: {ram_peak:.1f}% at "
                f"{datetime.datetime.fromtimestamp(ram_peak_time).strftime('%H:%M:%S')}"
            )
        # ----------------------------------------------------

        # Matplotlib colors based on theme
        line = "white" if self.dark_mode else "black"
        ram_line = "#6fdc6f" if self.dark_mode else "#2b8f6b"
        bg = "#1e1e1e" if self.dark_mode else "white"

        # CPU
        try:
            # CPU — updated version
            cpu_hist_raw = data.get("cpu_history", [])
            cpu_hist = [v for (_, v) in cpu_hist_raw]
            cpu_times = [ts for (ts, _) in cpu_hist_raw]

            self.cpu_canvas.ax.clear()

            if cpu_hist:
                # Filled curve
                self.cpu_canvas.ax.fill_between(range(len(cpu_hist)), cpu_hist, color="#6fa8dc" if not self.dark_mode else "#4a90e2", alpha=0.3)

                # Line plot
                self.cpu_canvas.ax.plot(cpu_hist, color="#1c4587" if not self.dark_mode else "white", linewidth=1.5)

                # Average CPU line
                avg_cpu = sum(cpu_hist) / len(cpu_hist)
                self.cpu_canvas.ax.axhline(avg_cpu, color="#ff6f00", linestyle="--", linewidth=1)
                self.cpu_canvas.ax.text(len(cpu_hist)-1, avg_cpu, f"Avg: {avg_cpu:.1f}%", color="#ff6f00")

                # Peak marker
                peak_cpu = data.get("peak_cpu", 0)
                if peak_cpu in cpu_hist:
                    peak_idx = cpu_hist.index(peak_cpu)
                    self.cpu_canvas.ax.scatter(peak_idx, peak_cpu, color="red", s=60, zorder=5)
                    self.cpu_canvas.ax.text(peak_idx, peak_cpu + 3, f"Peak {peak_cpu:.1f}%", color="red")

            self.cpu_canvas.ax.set_title("CPU Usage (%)")
            self.cpu_canvas.ax.set_ylim(0, 100)
            self.cpu_canvas.ax.grid(alpha=0.3)
            self.cpu_canvas.draw_idle()

        except:
            pass

        # RAM
        try:
            ram_hist_raw = data.get("ram_history", [])
            ram_hist = [v for (_, v) in ram_hist_raw]

            self.ram_canvas.ax.clear()

            if ram_hist:
                self.ram_canvas.ax.fill_between(range(len(ram_hist)), ram_hist, color="#93c47d", alpha=0.3)
                self.ram_canvas.ax.plot(ram_hist, color="#38761d" if not self.dark_mode else "#6fdc6f", linewidth=1.5)

                avg_ram = sum(ram_hist) / len(ram_hist)
                self.ram_canvas.ax.axhline(avg_ram, color="#ff6f00", linestyle="--", linewidth=1)
                self.ram_canvas.ax.text(len(ram_hist)-1, avg_ram, f"Avg: {avg_ram:.1f}%", color="#ff6f00")

                peak_ram = data.get("peak_ram", 0)
                if peak_ram in ram_hist:
                    peak_idx = ram_hist.index(peak_ram)
                    self.ram_canvas.ax.scatter(peak_idx, peak_ram, color="red", s=60)
                    self.ram_canvas.ax.text(peak_idx, peak_ram + 3, f"Peak {peak_ram:.1f}%", color="red")

            self.ram_canvas.ax.set_title("RAM Usage (%)")
            self.ram_canvas.ax.set_ylim(0, 100)
            self.ram_canvas.ax.grid(alpha=0.3)
            self.ram_canvas.draw_idle()

        except:
            pass

        # ===================== DISK (UPGRADED) =====================
        try:
            drives = data["disk"].get("drives", [])
            self.disk_canvas.ax.clear()

            if drives:
                labels = [d["device"] for d in drives]
                used_vals = [d["used"] for d in drives]
                free_vals = [d["free"] for d in drives]

                x = range(len(drives))

                # Stacked bar: Used + Free
                self.disk_canvas.ax.bar(x, used_vals, color="#e4572e", label="Used")
                self.disk_canvas.ax.bar(x, free_vals, bottom=used_vals, color="#4caf50", label="Free")

                # Add percentage labels
                for i, d in enumerate(drives):
                    pct = d["percent"]
                    total = d["total"]
                    self.disk_canvas.ax.text(
                        i, used_vals[i] + free_vals[i] * 0.5,
                        f"{pct}%\n({total} GB)",
                        ha="center",
                        color=line,
                        fontsize=10,
                        fontweight="bold"
                    )

                self.disk_canvas.ax.set_xticks(x)
                self.disk_canvas.ax.set_xticklabels(labels, color=line)

                self.disk_canvas.ax.set_title("Storage Usage by Drive", color=line)
                self.disk_canvas.ax.legend(facecolor=bg, labelcolor=line)
                self.disk_canvas.ax.grid(alpha=0.2)

                self.disk_canvas.ax.set_facecolor(bg)
                self.disk_canvas.ax.figure.set_facecolor(bg)

            self.disk_canvas.draw_idle()

        except Exception as e:
            print("Disk error:", e)


        # NETWORK
        try:
            net = data["network"]

            down = net.get("down", 0)
            up = net.get("up", 0)

            down_hist_raw = net.get("history_down", [])
            up_hist_raw = net.get("history_up", [])

            down_hist = [v for (_, v) in down_hist_raw]
            up_hist = [v for (_, v) in up_hist_raw]

            self.net_canvas.ax.clear()

            # Filled curves — modern style
            if down_hist:
                self.net_canvas.ax.fill_between(
                    range(len(down_hist)), down_hist,
                    alpha=0.25,
                    color="#4fc3f7" if not self.dark_mode else "#29b6f6"
                )
                self.net_canvas.ax.plot(
                    down_hist,
                    color="#0277bd" if not self.dark_mode else "white",
                    linewidth=1.7,
                    label="Download KB/s"
                )

            if up_hist:
                self.net_canvas.ax.fill_between(
                    range(len(up_hist)), up_hist,
                    alpha=0.25,
                    color="#81c784" if not self.dark_mode else "#66bb6a"
                )
                self.net_canvas.ax.plot(
                    up_hist,
                    color="#1b5e20" if not self.dark_mode else "#76ff03",
                    linewidth=1.7,
                    label="Upload KB/s"
                )

            # Plot peaks
            peak_down = net.get("peak_download", 0)
            peak_down_t = net.get("peak_download_time")
            peak_up = net.get("peak_upload", 0)
            peak_up_t = net.get("peak_upload_time")

            if peak_down > 0 and peak_down in down_hist:
                idx = down_hist.index(peak_down)
                self.net_canvas.ax.scatter(idx, peak_down, color="red", s=60)
                self.net_canvas.ax.text(idx, peak_down + 3, f"Peak ↓ {peak_down:.1f}", color="red")

            if peak_up > 0 and peak_up in up_hist:
                idx = up_hist.index(peak_up)
                self.net_canvas.ax.scatter(idx, peak_up, color="yellow", s=60)
                self.net_canvas.ax.text(idx, peak_up + 3, f"Peak ↑ {peak_up:.1f}", color="yellow")

            self.net_canvas.ax.set_title("Network Activity (KB/s)")
            self.net_canvas.ax.grid(alpha=0.3)
            self.net_canvas.ax.legend(loc="upper right")

            self.net_canvas.draw_idle()
            
            label_down = self.ui.findChild(QtWidgets.QLabel, "labelCurrentDown")
            label_up = self.ui.findChild(QtWidgets.QLabel, "labelCurrentUp")
            label_peak_down = self.ui.findChild(QtWidgets.QLabel, "labelPeakDown")
            label_peak_up = self.ui.findChild(QtWidgets.QLabel, "labelPeakUp")
            label_adapter = self.ui.findChild(QtWidgets.QLabel, "labelAdapter")

            if label_down:
                label_down.setText(f"↓ {down:.1f} KB/s")

            if label_up:
                label_up.setText(f"↑ {up:.1f} KB/s")

            if label_peak_down and peak_down_t:
                label_peak_down.setText(
                    f"Peak Download: {peak_down:.1f} KB/s at {datetime.datetime.fromtimestamp(peak_down_t).strftime('%H:%M:%S')}"
                )

            if label_peak_up and peak_up_t:
                label_peak_up.setText(
                    f"Peak Upload: {peak_up:.1f} KB/s at {datetime.datetime.fromtimestamp(peak_up_t).strftime('%H:%M:%S')}"
                )

            if label_adapter:
                adapter = net.get("adapters", [])
                if adapter:
                    info = adapter[0]  # first network device
                    label_adapter.setText(
                        f"Adapter: {info['name']} • {info['speed']} Mbps • MTU {info['mtu']}"
                    )


        except Exception as e:
            print("Network UI error:", e)



    # -----------------------------------------------------
    #                POPUP WINDOWS
    # -----------------------------------------------------
    def _open_battery_predictor(self):
        pred = self.backend.get_battery_prediction()

        # Load live battery info if available
        latest = self.backend.get_latest()
        bat_info = latest.get("battery", {}) if latest else {}

        # Load fallback historical entry (from JSON log)
        try:
            from backend.analytics.battery_predictor import BatteryPredictor
            bp = self.backend.batt_predictor
            log_entries = bp._load_log()
            last_log = log_entries[-1] if log_entries else None
        except:
            last_log = None

        # ----------- DIALOG SETUP -----------
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Battery Health & Prediction")
        dlg.setMinimumWidth(450)

        layout = QtWidgets.QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("🔋 Battery Health Summary")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # -----------------------------------------------------
        # 🟢 BUILD BATTERY INFORMATION BLOCK
        # -----------------------------------------------------
        section = QtWidgets.QLabel("<b>Battery Information</b>")
        layout.addWidget(section)

        bullet = "• "

        # Prioritize live info, fallback to log info
        present = bat_info.get("present")
        pct = bat_info.get("percent")
        cycle = bat_info.get("cycle_count")
        design = bat_info.get("design_capacity_mwh")
        full = bat_info.get("full_charge_capacity_mwh")
        volt = bat_info.get("voltage_mv")

        # Fallback from logs only if missing in live data
        if present is None and last_log:
            present = True  # assume device had a battery
        if pct is None and last_log:
            pct = "Unknown"
        if design is None and last_log:
            design = last_log.get("design_mwh")
        if full is None and last_log:
            full = last_log.get("full_mwh")
        if cycle is None and last_log:
            cycle = last_log.get("cycle_count")
        if volt is None and last_log:
            volt = last_log.get("voltage_mv")

        # Wear calculation
        if full and design and design > 0:
            wear = round((1.0 - (full / design)) * 100, 2)
        elif last_log and last_log.get("wear_pct"):
            wear = round(last_log.get("wear_pct"), 2)
        else:
            wear = None

        # Build text
        info_html = ""

        info_html += f"{bullet}<b>Present:</b> {present}<br>"
        info_html += f"{bullet}<b>Charge:</b> {pct}%<br>"

        if design:
            info_html += f"{bullet}<b>Design Capacity:</b> {design} mWh<br>"
        if full:
            info_html += f"{bullet}<b>Full Charge Capacity:</b> {full} mWh<br>"
        if wear is not None:
            info_html += f"{bullet}<b>Wear:</b> {wear}%<br>"
        if cycle is not None:
            info_html += f"{bullet}<b>Cycle Count:</b> {cycle}<br>"
        if volt is not None:
            info_html += f"{bullet}<b>Voltage:</b> {volt} mV<br>"

        # If still nothing meaningful
        if not design and not full and not wear:
            info_html += "<i>Capacity details unavailable on this system.</i>"

        lbl_info = QtWidgets.QLabel(info_html)
        lbl_info.setTextFormat(Qt.RichText)
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        # -----------------------------------------------------
        # 🟡 HEALTH PREDICTION SECTION
        # -----------------------------------------------------
        layout.addWidget(QtWidgets.QLabel("<h3>Health Prediction</h3>"))

        if not pred or pred.get("projected_health_percent") is None:
            msg = QtWidgets.QLabel(
                "<i>Not enough historical data to generate prediction.<br>"
                "(Need at least 3 days of capacity samples.)</i>"
            )
            msg.setWordWrap(True)
            layout.addWidget(msg)
        else:
            pred_html = f"""
            <b>• Weekly Degradation:</b> {pred['weekly_degradation_percent']} %/week<br>
            <b>• Projected Health (6 months):</b> {pred['projected_health_percent']} %<br>
            <b>• Health Score:</b> {pred['health_score']} / 100<br><br>
            <pre style='white-space: pre-wrap; font-size: 13px;'>{pred['notes']}</pre>
            """

            lbl_pred = QtWidgets.QLabel(pred_html)
            lbl_pred.setTextFormat(Qt.RichText)
            lbl_pred.setWordWrap(True)
            layout.addWidget(lbl_pred)

        # -----------------------------------------------------
        # CLOSE BUTTON
        # -----------------------------------------------------
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

        dlg.exec()



    def _open_stability_scores(self):
        import psutil
        import win32gui
        import win32process

        # -------------------------------
        # Helper: collect window titles by PID
        # -------------------------------
        def get_all_window_titles():
            pid_title = {}

            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).strip()
                    if title:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        # Keep only first UNIQUE title per PID
                        if pid not in pid_title:
                            pid_title[pid] = title

            win32gui.EnumWindows(callback, None)
            return pid_title

        pid_to_title = get_all_window_titles()

        # Get scores
        scores = self.backend.get_stability_scores()

        # Dialog setup
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Application Stability")
        dlg.setMinimumSize(850, 450)
        layout = QtWidgets.QVBoxLayout(dlg)

        # Table with 4 columns
        table = QtWidgets.QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["PID", "Process", "App Title", "Score"])
        table.setRowCount(len(scores))

        for i, proc in enumerate(scores):
            pid = proc["pid"]
            proc_name = proc["name"]
            score = proc["score"]

            # Find app title if available
            app_title = pid_to_title.get(pid, "Background / No Window")

            table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(pid)))
            table.setItem(i, 1, QtWidgets.QTableWidgetItem(proc_name))
            table.setItem(i, 2, QtWidgets.QTableWidgetItem(app_title))

            # Show N/A for None
            score_text = str(score) if score is not None else "N/A"
            table.setItem(i, 3, QtWidgets.QTableWidgetItem(score_text))

        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        layout.addWidget(table)

        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

        dlg.exec()



    def _open_daily_story(self):
        story, _ = self.backend.generate_daily_story()

        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Daily Story")
        dlg.setTextFormat(Qt.RichText)  # allow HTML formatting
        dlg.setStyleSheet("QLabel{min-width: 420px;}")  # make story wider
        dlg.setText(story)
        dlg.exec()


    def _open_settings_placeholder(self):
        QtWidgets.QMessageBox.information(self, "Settings", "Settings panel coming soon.")
