# backend/monitors/disk_monitor.py
import psutil
import time
import collections
from .. import config, logger

class DiskMonitor:
    """
    Provides per-drive (C:, D:, E:) storage info
    + total aggregated storage info
    + history of total disk usage
    """

    def __init__(self):
        # Store last N samples for graph (percent used)
        self.history = collections.deque(maxlen=config.HISTORY_LEN)

    def sample(self):
        """
        Returns:
        {
            "drives": [
                {
                    "device": "C:",
                    "mount": "C:\\",
                    "total": 512.0,
                    "used": 300.5,
                    "free": 211.5,
                    "percent": 58.7
                }
            ],
            "total": {
                "total": ...,
                "used": ...,
                "free": ...,
                "percent": ...
            },
            "history": [(ts, percent_total), ...],
            "timestamp": ts
        }
        """

        ts = time.time()
        drives = []

        total_bytes = 0
        used_bytes = 0

        try:
            for part in psutil.disk_partitions(all=False):

                # Skip invalid or CD-ROM drives without a filesystem
                if not part.fstype:
                    continue

                try:
                    usage = psutil.disk_usage(part.mountpoint)

                    total_gb = round(usage.total / (1024**3), 2)
                    used_gb = round(usage.used / (1024**3), 2)
                    free_gb = round(usage.free / (1024**3), 2)

                    drives.append({
                        "device": part.device,
                        "mount": part.mountpoint,
                        "total": total_gb,
                        "used": used_gb,
                        "free": free_gb,
                        "percent": usage.percent
                    })

                    # For total aggregation
                    total_bytes += usage.total
                    used_bytes += usage.used

                except PermissionError:
                    continue
                except Exception as e:
                    logger.log(f"DiskMonitor: error reading {part.mountpoint}: {e}")

        except Exception as e:
            logger.log(f"DiskMonitor: error listing partitions: {e}")

        # ---- Total combined storage (GB) ----
        total_gb = round(total_bytes / (1024**3), 2)
        used_gb = round(used_bytes / (1024**3), 2)
        free_gb = round((total_bytes - used_bytes) / (1024**3), 2)

        percent_total = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0.0

        total_info = {
            "total": total_gb,
            "used": used_gb,
            "free": free_gb,
            "percent": round(percent_total, 2)
        }

        # Store history for graph
        self.history.append((ts, percent_total))

        return {
            "drives": drives,
            "total": total_info,
            "history": list(self.history),
            "timestamp": ts
        }
