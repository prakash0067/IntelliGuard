# backend/analytics/daily_story.py
import datetime

class DailyStory:
    def generate(self, aggregated):
        cpu_list = aggregated.get("cpu", [])
        ram_list = aggregated.get("ram", [])
        net_list = aggregated.get("network_bytes", [])
        app_usage = aggregated.get("app_usage", {})

        # CPU stats
        if cpu_list:
            cpu_avg = sum(cpu_list) / len(cpu_list)
            cpu_peak = max(cpu_list)
            cpu_peak_time = aggregated.get("cpu_peak_time", "-")
        else:
            cpu_avg = cpu_peak = 0
            cpu_peak_time = "-"

        # RAM stats
        if ram_list:
            ram_avg = sum(ram_list) / len(ram_list)
            ram_peak = max(ram_list)
            ram_peak_time = aggregated.get("ram_peak_time", "-")
        else:
            ram_avg = ram_peak = 0
            ram_peak_time = "-"

        # Network stats
        net_total = sum(net_list) / 1024 / 1024  # convert to MB
        busiest_net = max(net_list) if net_list else 0

        # App usage sorted
        sorted_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)
        top_apps = sorted_apps[:5]

        # System health estimation
        health_score = 100
        if cpu_avg > 70 or ram_avg > 70:
            health_score -= 20
        if cpu_peak > 90 or ram_peak > 90:
            health_score -= 20
        if net_total > 2000:  # > 2GB used
            health_score -= 10

        # Recommendation
        if health_score > 80:
            rec = "Your system is running very smoothly today. 🚀"
        elif health_score > 60:
            rec = "Overall performance was decent, but a cleanup may help. 🧹"
        else:
            rec = "High load detected. Consider closing background apps. ⚠️"

        # Build HTML formatted story
        story = f"""
        <h2>📝 Daily System Story</h2>

        <h3>🔥 CPU Summary</h3>
        <p>• <b>Average:</b> {cpu_avg:.1f}%<br>
        • <b>Peak:</b> {cpu_peak:.1f}%<br></p>

        <h3>💾 RAM Summary</h3>
        <p>• <b>Average:</b> {ram_avg:.1f}%<br>
        • <b>Peak:</b> {ram_peak:.1f}%<br></p>

        <h3>🌐 Network</h3>
        <p>• <b>Total Data Used:</b> {net_total:.2f} MB<br>
        • <b>Busiest Moment:</b> {busiest_net/1024:.1f} KB/s</p>

        <h3>📱 Top Applications Used</h3>
        <ul>
        {''.join([f"<li>{app} — {count} active checks</li>" for app, count in top_apps])}
        </ul>

        <h3>❤️ System Health Score: {health_score}/100</h3>
        <p>{rec}</p>
        """

        summary = {
            "cpu_avg": cpu_avg,
            "cpu_peak": cpu_peak,
            "ram_avg": ram_avg,
            "ram_peak": ram_peak,
            "net_total_mb": net_total,
            "top_apps": top_apps,
            "health_score": health_score
        }

        return story, summary
