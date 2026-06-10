import os
import hashlib
import time
from PyQt5.QtGui import QPixmap
from utils.config_manager import ConfigManager


CACHE_TTL = 7 * 24 * 3600


class ThumbnailCache:
    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            local_base = os.environ.get("LOCALAPPDATA", ConfigManager.CONFIG_DIR)
            cache_dir = os.path.join(local_base, "InspectionReview", "cache", "thumbnails")
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _cache_key(self, image_path: str, size: tuple) -> str:
        raw = f"{image_path}_{size[0]}x{size[1]}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def get(self, image_path: str, size: tuple = (120, 120)) -> QPixmap:
        path = os.path.join(self.cache_dir, f"{self._cache_key(image_path, size)}.png")
        if os.path.exists(path):
            if time.time() - os.path.getmtime(path) < CACHE_TTL:
                pix = QPixmap(path)
                if not pix.isNull():
                    return pix
                os.remove(path)
        return None

    def put(self, image_path: str, pixmap: QPixmap, size: tuple = (120, 120)):
        path = os.path.join(self.cache_dir, f"{self._cache_key(image_path, size)}.png")
        try:
            pixmap.save(path, "PNG")
        except Exception:
            pass

    def clean_expired(self):
        for fname in os.listdir(self.cache_dir):
            path = os.path.join(self.cache_dir, fname)
            if os.path.isfile(path) and fname.endswith(".png"):
                if time.time() - os.path.getmtime(path) > CACHE_TTL:
                    os.remove(path)
