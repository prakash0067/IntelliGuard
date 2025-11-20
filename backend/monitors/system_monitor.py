# backend/monitors/system_monitor.py
import psutil
import time
import collections
from .. import config, logger, notifier

class SystemMonitor:
    def __init__(self):
        self.cpu_history = collections.deque(maxlen=config.HISTORY_LEN)
        self.ram_history = collections.deque(maxlen=config.HISTORY_LEN)

        self.cpu_hits = 0
        self.ram_hits = 0

        # Peak tracking
        self.peak_cpu = 0
        self.peak_cpu_time = None
        self.peak_ram = 0
        self.peak_ram_time = None


    def sample(self):
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        ram = mem.percent
        swap = psutil.swap_memory().percent
        ts = time.time()     # <-- Correct timestamp

        # Update history
        self.cpu_history.append((ts, cpu))
        self.ram_history.append((ts, ram))

        # Track peak CPU
        if cpu > self.peak_cpu:
            self.peak_cpu = cpu
            self.peak_cpu_time = ts

        # Track peak RAM
        if ram > self.peak_ram:
            self.peak_ram = ram
            self.peak_ram_time = ts

        # Threshold alerts
        if cpu > config.CPU_THRESHOLD:
            self.cpu_hits += 1
        else:
            self.cpu_hits = 0

        if ram > config.RAM_THRESHOLD:
            self.ram_hits += 1
        else:
            self.ram_hits = 0

        if self.cpu_hits >= config.CONSECUTIVE_LIMIT:
            notifier.Notifier.alert_all(f"CPU > {config.CPU_THRESHOLD}% for {self.cpu_hits} checks.")
            logger.log(f"CPU high: {cpu}% (hits={self.cpu_hits})")

        if self.ram_hits >= config.CONSECUTIVE_LIMIT:
            notifier.Notifier.alert_all(f"RAM > {config.RAM_THRESHOLD}% for {self.ram_hits} checks.")
            logger.log(f"RAM high: {ram}% (hits={self.ram_hits})")

        # Top CPU Processes
        procs_cpu = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
            try:
                procs_cpu.append(p.info)
            except:
                pass
        procs_cpu.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
        top_cpu = procs_cpu[:3]

        # Top RAM Processes
        procs_mem = []
        for p in psutil.process_iter(["pid", "name", "memory_percent"]):
            try:
                procs_mem.append(p.info)
            except:
                pass
        procs_mem.sort(key=lambda x: x.get("memory_percent") or 0, reverse=True)
        top_mem = procs_mem[:3]

        # RETURN VALUE
        return {
            "cpu": cpu,
            "ram": ram,
            "swap": swap,
            "top_cpu": top_cpu,
            "top_mem": top_mem,
            "cpu_hits": self.cpu_hits,
            "ram_hits": self.ram_hits,
            "cpu_history": list(self.cpu_history),
            "ram_history": list(self.ram_history),
            "timestamp": ts,

            # Peak metrics (correct)
            "peak_cpu": self.peak_cpu,
            "peak_cpu_time": self.peak_cpu_time,
            "peak_ram": self.peak_ram,
            "peak_ram_time": self.peak_ram_time,
        }
