import os
import hashlib
from .. import config, logger
import time

class DuplicateFinder:

    def __init__(self, path=None):
        self.path = path or config.DOWNLOADS_PATH

    def _file_hash(self, filepath, chunk_size=4096):
        try:
            hasher = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return None

    def find_duplicates(self):
        """
        Returns:
            [
                {
                    "filepath": "...",
                    "filename": "...",
                    "size": "10 MB",
                    "modified": "2025-11-19 14:22"
                },
                ...
            ]
        """
        if not os.path.exists(self.path):
            return []

        size_map = {}
        dup_list = []

        # Step 1 — group by size
        for name in os.listdir(self.path):
            fp = os.path.join(self.path, name)
            if not os.path.isfile(fp):
                continue
            size = os.path.getsize(fp)
            size_map.setdefault(size, []).append(fp)

        # Step 2 — hash only those with same size
        final_dups = []
        for size, files in size_map.items():
            if len(files) < 2:
                continue

            hash_map = {}
            for fp in files:
                h = self._file_hash(fp)
                if not h:
                    continue
                hash_map.setdefault(h, []).append(fp)

            for h, group in hash_map.items():
                if len(group) > 1:
                    for fp in group:
                        stat = os.stat(fp)
                        final_dups.append({
                            "filepath": fp,
                            "filename": os.path.basename(fp),
                            "size": f"{stat.st_size / (1024*1024):.2f} MB",
                            "modified": 
                                time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
                        })

        return final_dups

    def delete_files(self, filepaths):
        deleted = []
        for fp in filepaths:
            try:
                os.remove(fp)
                deleted.append(fp)
            except Exception as e:
                logger.log(f"Duplicate delete failed: {fp}, {e}")
        return deleted
