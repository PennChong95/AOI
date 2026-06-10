import cv2
import numpy as np
from database.models import RectangleInt


class ImageUtils:
    """Utility class for image loading, drawing, and conversion."""

    @staticmethod
    def load_image(path: str) -> np.ndarray:
        try:
            with open(path, "rb") as f:
                data = f.read()
            arr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("无法解码图片")
            return img
        except FileNotFoundError:
            raise FileNotFoundError(f"图片文件不存在: {path}")
        except Exception as e:
            raise RuntimeError(f"加载图片失败: {e}")

    @staticmethod
    def draw_bounding_box(
        image: np.ndarray,
        rect: RectangleInt,
        scale: float = 1.0,
        color=(0, 255, 0),
        thickness: int = 2,
    ) -> np.ndarray:
        img = image.copy()
        cx = rect.X + rect.Width / 2
        cy = rect.Y + rect.Height / 2
        new_w = int(rect.Width * scale)
        new_h = int(rect.Height * scale)
        new_x = int(cx - new_w / 2)
        new_y = int(cy - new_h / 2)
        cv2.rectangle(img, (new_x, new_y), (new_x + new_w, new_y + new_h), color, thickness)
        return img

    @staticmethod
    def draw_contour(image: np.ndarray, points: list, color=(0, 255, 255), thickness: int = 1):
        if not points:
            return image
        img = image.copy()
        pts = np.array([[p.X, p.Y] for p in points], dtype=np.int32)
        cv2.polylines(img, [pts], isClosed=True, color=color, thickness=thickness)
        return img

    @staticmethod
    def cv2_to_qpixmap(cv_img: np.ndarray):
        from PyQt5.QtGui import QImage, QPixmap
        h, w, ch = cv_img.shape
        bytes_per_line = ch * w
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg)

    @staticmethod
    def generate_icon(size: int = 256) -> np.ndarray:
        """Flat minimal icon: white bg, rounded blue border, blue Q in center."""
        img = np.ones((size, size, 3), dtype=np.uint8) * 255
        S = size

        BLUE = (247, 108, 79)     # #4F6CF7
        AA = cv2.LINE_AA

        margin = int(S * 0.07)
        r = int(S * 0.16)
        thickness = max(2, int(S * 0.02))

        # Rounded rectangle outline (blue)
        cv2.rectangle(img, (margin + r, margin), (S - margin - r, S - margin), BLUE, thickness)
        cv2.rectangle(img, (margin, margin + r), (S - margin, S - margin - r), BLUE, thickness)
        cv2.circle(img, (margin + r, margin + r), r, BLUE, thickness)
        cv2.circle(img, (S - margin - r, margin + r), r, BLUE, thickness)
        cv2.circle(img, (margin + r, S - margin - r), r, BLUE, thickness)
        cv2.circle(img, (S - margin - r, S - margin - r), r, BLUE, thickness)

        # Center letter Q (blue)
        cx, cy = S // 2, S // 2 + int(S * 0.02)
        qr = int(S * 0.30)
        qt = max(3, int(S * 0.04))
        cv2.circle(img, (cx, cy), qr, BLUE, qt, AA)
        cv2.circle(img, (cx, cy), int(qr * 0.55), (255, 255, 255), -1, AA)
        tx = cx + int(qr * 0.35)
        ty = cy + int(qr * 0.35)
        tl = int(qr * 0.45)
        cv2.line(img, (tx, ty), (tx + tl, ty + tl), BLUE, qt, AA)

        return img

    @staticmethod
    def make_placeholder(w: int, h: int, text: str = "无图片") -> np.ndarray:
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (30, 30, 30)
        cv2.putText(img, text, (w // 4, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
        return img
