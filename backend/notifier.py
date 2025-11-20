# backend/notifier.py
from .logger import log

class Notifier:
    @staticmethod
    def alert_console(msg):
        log(f"ALERT: {msg}")

    @staticmethod
    def alert_sound():
        try:
            import winsound
            winsound.Beep(1000, 250)
        except Exception:
            print("\a")

    @staticmethod
    def alert_all(msg):
        Notifier.alert_console(msg)
        try:
            Notifier.alert_sound()
        except Exception:
            pass
