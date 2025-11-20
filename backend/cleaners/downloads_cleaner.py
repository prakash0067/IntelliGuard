# backend/cleaners/downloads_cleaner.py
import os
import time
import datetime
from .. import config, logger

class DownloadsCleaner:
    def __init__(self, path=None):
        self.path = path or config.DOWNLOADS_PATH

    def _age_days(self, fp):
        try:
            mtime = os.path.getmtime(fp)
            return (time.time() - mtime) / (60*60*24)
        except Exception:
            return None

    def run_cleanup(self, cleanup_days):
        """
        cleanup_days: integer number of days; delete files older than this many days
        """
        logger.log(f"Starting downloads cleanup with rule: delete files older than {cleanup_days} days.")
        if not os.path.exists(self.path):
            logger.log(f"Downloads path not found: {self.path}")
            return {"deleted": [], "skipped": [], "error": "path_not_found"}

        deleted = []
        skipped = []
        for name in os.listdir(self.path):
            fp = os.path.join(self.path, name)
            if os.path.isfile(fp):
                try:
                    age = self._age_days(fp)
                    if age is None:
                        skipped.append(name)
                        continue
                    if age > cleanup_days:
                        try:
                            os.remove(fp)
                            deleted.append(name)
                        except Exception as e:
                            logger.log(f"Failed to delete {fp}: {e}")
                            skipped.append(name)
                    else:
                        skipped.append(name)
                except Exception as e:
                    logger.log(f"Error processing {fp}: {e}")
                    skipped.append(name)
            else:
                skipped.append(name)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_lines = [f"=== Cleanup run at {now} (days={cleanup_days}) ==="]
        if deleted:
            report_lines.append(f"Deleted {len(deleted)} files:")
            for d in deleted:
                report_lines.append(f" - {d}")
        else:
            report_lines.append("No files deleted.")
        logger.append_report("\n".join(report_lines))
        logger.log("Downloads cleanup finished.")
        return {"deleted": deleted, "skipped": skipped}
