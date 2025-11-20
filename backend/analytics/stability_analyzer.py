# backend/analytics/stability_analyzer.py
import math
from .. import logger

class StabilityAnalyzer:
    """
    Assigns a stability score (0–100) to running applications by analyzing:
      - CPU spike frequency (instability)
      - RAM leak (growth slope)
      - Disk IO volume
      - Network IO volume

    A stable app has:
      - Low CPU variance
      - No RAM growth
      - Normal IO and network activity
    """

    def __init__(self):
        pass

    def score_process(self, history):
        """
        history: list of sample dictionaries:
            {
                "ts": timestamp,
                "cpu": float (%),
                "mem": float (MB or %),
                "io_read": int (bytes),
                "io_write": int (bytes),
                "net_sent": int (bytes),
                "net_recv": int (bytes)
            }

        returns:
            {
                "score": int,
                "breakdown": {...},
                "notes": str
            }
        """

        if not history or len(history) < 3:
            return {
                "score": None,
                "breakdown": {},
                "notes": "Insufficient data."
            }

        n = len(history)

        # Extract values
        cpu_vals = [h.get("cpu", 0.0) for h in history]
        mem_vals = [h.get("mem", 0.0) for h in history]
        io_read = [h.get("io_read", 0) for h in history]
        io_write = [h.get("io_write", 0) for h in history]
        net_sent = [h.get("net_sent", 0) for h in history]
        net_recv = [h.get("net_recv", 0) for h in history]

        # --- CPU INSTABILITY ---
        cpu_mean = sum(cpu_vals) / n
        cpu_var = sum((x - cpu_mean) ** 2 for x in cpu_vals) / n
        cpu_std = math.sqrt(cpu_var)
        # Measure instability relative to mean
        cpu_instability = cpu_std / (cpu_mean + 0.1)

        # --- MEMORY LEAK ESTIMATE ---
        mem_slope = (mem_vals[-1] - mem_vals[0]) / max(1, n)

        # --- I/O & Network Volume ---
        io_total_mb = (sum(io_read) + sum(io_write)) / (1024 * 1024)
        net_total_mb = (sum(net_sent) + sum(net_recv)) / (1024 * 1024)

        # --- Penalties ---
        # Normalize the penalties into 0–1 range
        cpu_penalty = min(1.0, cpu_instability / 1.0)
        mem_penalty = min(1.0, max(0.0, mem_slope / 1.0))
        io_penalty = min(1.0, io_total_mb / 50.0)      # high if > 50 MB
        net_penalty = min(1.0, net_total_mb / 20.0)    # high if > 20 MB

        # Weighted penalty
        total_penalty = (
            0.5 * cpu_penalty +
            0.3 * mem_penalty +
            0.1 * io_penalty +
            0.1 * net_penalty
        )

        # Convert to stability score
        score = int(max(0, min(100, round((1 - total_penalty) * 100))))

        breakdown = {
            "cpu_mean": round(cpu_mean, 3),
            "cpu_std": round(cpu_std, 3),
            "cpu_penalty": round(cpu_penalty, 3),
            "mem_slope": round(mem_slope, 4),
            "mem_penalty": round(mem_penalty, 3),
            "io_total_mb": round(io_total_mb, 2),
            "io_penalty": round(io_penalty, 3),
            "net_total_mb": round(net_total_mb, 2),
            "net_penalty": round(net_penalty, 3),
            "combined_penalty": round(total_penalty, 3),
        }

        notes = (
            "Higher penalties indicate instability:\n"
            "- CPU penalty: frequent CPU spikes\n"
            "- Memory penalty: potential memory leak\n"
            "- IO/Network penalty: high data transfer\n"
        )

        return {
            "score": score,
            "breakdown": breakdown,
            "notes": notes
        }
