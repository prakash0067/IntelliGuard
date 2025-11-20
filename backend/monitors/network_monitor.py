# backend/monitors/network_monitor.py
import psutil
import time
import collections
from .. import config, logger

class NetworkMonitor:

    def __init__(self):
        self.last_total_recv = None
        self.last_total_sent = None
        self.history_down = collections.deque(maxlen=config.HISTORY_LEN)
        self.history_up = collections.deque(maxlen=config.HISTORY_LEN)

        # Peak values
        self.peak_download = 0
        self.peak_download_time = None
        self.peak_upload = 0
        self.peak_upload_time = None

    def sample(self):
        now = time.time()
        net = psutil.net_io_counters()

        if self.last_total_recv is None:
            self.last_total_recv = net.bytes_recv
            self.last_total_sent = net.bytes_sent
            return {
                "down": 0, "up": 0,
                "history_down": list(self.history_down),
                "history_up": list(self.history_up),
                "peak_download": self.peak_download,
                "peak_download_time": self.peak_download_time,
                "peak_upload": self.peak_upload,
                "peak_upload_time": self.peak_upload_time,
                "adapters": self._adapter_info(),
                "timestamp": now
            }

        # Calculate deltas
        down_kb = (net.bytes_recv - self.last_total_recv) / 1024
        up_kb = (net.bytes_sent - self.last_total_sent) / 1024

        # Update stored previous values
        self.last_total_recv = net.bytes_recv
        self.last_total_sent = net.bytes_sent

        # Append to history
        self.history_down.append((now, down_kb))
        self.history_up.append((now, up_kb))

        # Track peaks
        if down_kb > self.peak_download:
            self.peak_download = down_kb
            self.peak_download_time = now

        if up_kb > self.peak_upload:
            self.peak_upload = up_kb
            self.peak_upload_time = now

        return {
            "down": round(down_kb, 2),
            "up": round(up_kb, 2),
            "history_down": list(self.history_down),
            "history_up": list(self.history_up),
            "peak_download": round(self.peak_download, 2),
            "peak_download_time": self.peak_download_time,
            "peak_upload": round(self.peak_upload, 2),
            "peak_upload_time": self.peak_upload_time,
            "adapters": self._adapter_info(),
            "timestamp": now
        }

    def _adapter_info(self):
        """Return detailed info for each network interface."""
        adapters = []
        for name, addrs in psutil.net_if_addrs().items():
            stats = psutil.net_if_stats().get(name)
            if stats:
                adapters.append({
                    "name": name,
                    "speed": stats.speed,
                    "isup": stats.isup,
                    "duplex": stats.duplex,
                    "mtu": stats.mtu
                })
        return adapters
