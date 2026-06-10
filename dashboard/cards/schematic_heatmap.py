from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QPushButton, QLabel, QComboBox
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from editor.product_layout import Region, ProductLayoutModel
from editor.layout_manager import ProductLayoutManager
from utils.config_manager import ConfigManager


HEAT_THRESHOLDS = [
    (0.0,  QColor("#2ECC71")),   # 正常 — 绿色
    (0.2,  QColor("#A3E635")),   # 轻微异常 — 黄绿色
    (0.4,  QColor("#FACC15")),   # 一般异常 — 黄色
    (0.6,  QColor("#F97316")),   # 严重异常 — 橙色
    (0.99, QColor("#EF4444")),   # 危险区域 — 红色
]


def _heat_color(ratio: float) -> QColor:
    for threshold, color in reversed(HEAT_THRESHOLDS):
        if ratio >= threshold:
            return color
    return QColor("#2ECC71")


class SchematicHeatView(QWidget):
    """模式 1：产品示意图热力图"""

    region_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._regions: list = []
        self._heatmap: dict = {}
        self._canvas_w = 1000
        self._canvas_h = 1000
        self._rect_map: list = []
        self._highlighted_region = None

    def set_data(self, heatmap: dict, product_name: str):
        self._heatmap = heatmap
        if product_name:
            mgr = ProductLayoutManager.instance()
            layout = mgr.load_layout(product_name)
            if layout:
                self._regions = layout.regions
                self._canvas_w = layout.canvas_width
                self._canvas_h = layout.canvas_height
        self.update()

    def mousePressEvent(self, event):
        for region_name, rect in self._rect_map:
            if rect.contains(event.pos()):
                self._highlighted_region = region_name
                self.update()
                QTimer.singleShot(400, self._clear_highlight)
                self.region_clicked.emit(region_name)
                return
        super().mousePressEvent(event)

    def _clear_highlight(self):
        self._highlighted_region = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#F8FAFC"))

        if not self._regions:
            p.setPen(QColor("#94A3B8"))
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(self.rect(), Qt.AlignCenter, "暂无产品示意图数据")
            p.end()
            return

        margin = 6
        sx = (w - 2 * margin) / max(self._canvas_w, 1)
        sy = (h - 2 * margin) / max(self._canvas_h, 1)
        ox, oy = margin, margin

        max_count = max(self._heatmap.values()) if self._heatmap else 1
        total = sum(self._heatmap.values()) if self._heatmap else 1
        self._rect_map.clear()

        for region in sorted(self._regions, key=lambda r: r.z_order):
            if not region.visible:
                continue
            count = self._heatmap.get(region.name, 0)
            ratio = count / max_count if max_count else 0
            pct = count / total * 100 if total else 0
            color = _heat_color(ratio)

            rx = ox + region.x * sx
            ry = oy + region.y * sy
            rw = region.width * sx
            rh = region.height * sy
            rect = QRectF(rx, ry, rw, rh)
            self._rect_map.append((region.name, rect))

            p.setPen(QPen(color.darker(120), 1))
            p.setBrush(QBrush(color))
            if region.border_radius > 0 and rw > region.border_radius * 2 and rh > region.border_radius * 2:
                p.drawRoundedRect(rect, region.border_radius * sx, region.border_radius * sy)
            else:
                p.drawRect(rect)

            p.setPen(QColor("#FFFFFF") if ratio > 0.5 else QColor("#1E293B"))
            f = QFont("Segoe UI", max(8, min(12, int(rh / 5))))
            p.setFont(f)
            label = f"{region.name}\n{count} ({pct:.1f}%)"
            p.drawText(rect, Qt.AlignCenter, label)

        if self._highlighted_region:
            for rname, r in self._rect_map:
                if rname == self._highlighted_region:
                    p.setPen(QPen(QColor("#3B82F6"), 3))
                    p.setBrush(Qt.NoBrush)
                    p.drawRect(r)
                    break

        p.end()


class TreemapHeatView(QWidget):
    """模式 2：色块比例图"""

    region_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list = []
        self._rect_map: list = []
        self._highlighted_name = None

    def set_data(self, heatmap: dict, product_name: str = ""):
        self._items = sorted(heatmap.items(), key=lambda x: -x[1])
        self.update()

    def mousePressEvent(self, event):
        for region_name, rect in self._rect_map:
            if rect.contains(event.pos()):
                self._highlighted_name = region_name
                self.update()
                QTimer.singleShot(400, self._clear_highlight)
                self.region_clicked.emit(region_name)
                return
        super().mousePressEvent(event)

    def _clear_highlight(self):
        self._highlighted_name = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#F8FAFC"))

        if not self._items:
            p.setPen(QColor("#94A3B8"))
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(self.rect(), Qt.AlignCenter, "暂无热力图数据")
            p.end()
            return

        total = sum(c for _, c in self._items)
        max_count = max(c for _, c in self._items)
        margin = 6
        gap = 4
        self._rect_map.clear()

        row_y = margin
        idx = 0

        while idx < len(self._items):
            remaining = sum(c for _, c in self._items[idx:])
            fraction = remaining / total if total else 1
            row_h = (h - 2 * margin - gap * (len(self._items) - idx - 1)) * fraction
            row_h = max(36, min(row_h, h - row_y - margin))

            row_x = margin
            row_count = 0
            for i in range(idx, len(self._items)):
                name, count = self._items[i]
                w_ratio = count / remaining if remaining else 0
                block_w = max(30, (w - 2 * margin - gap * (len(self._items) - idx - 1)) * w_ratio)

                if row_x + block_w > w - margin and row_count > 0:
                    break

                ratio_color = count / max_count if max_count else 0
                color = _heat_color(ratio_color)

                rect = QRectF(row_x, row_y, block_w, row_h)
                self._rect_map.append((name, rect))
                p.setPen(QPen(color.darker(130), 1))
                p.setBrush(QBrush(color))
                p.drawRoundedRect(rect, 4, 4)

                text_color = QColor("#FFFFFF") if ratio_color > 0.5 else QColor("#1E293B")
                p.setPen(text_color)
                fw = max(8, min(12, int(block_w / 8)))
                p.setFont(QFont("Segoe UI", fw))
                pct_str = f"{count / total * 100:.1f}%" if total else ""
                label = f"{name}\n{count} ({pct_str})"
                p.drawText(rect, Qt.AlignCenter, label)

                row_x += block_w + gap
                idx += 1
                row_count += 1

            row_y += row_h + gap
            if idx >= len(self._items) or row_y > h - 20:
                break

        if self._highlighted_name:
            for rname, r in self._rect_map:
                if rname == self._highlighted_name:
                    p.setPen(QPen(QColor("#3B82F6"), 3))
                    p.setBrush(Qt.NoBrush)
                    p.drawRoundedRect(r, 4, 4)
                    break

        p.end()


class SchematicHeatmapCard(QWidget):
    """热力图卡片：双模式切换"""

    drilldown_triggered = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._stack = QStackedWidget()
        self._schematic = SchematicHeatView()
        self._treemap = TreemapHeatView()
        self._stack.addWidget(self._schematic)
        self._stack.addWidget(self._treemap)

        self._schematic.region_clicked.connect(self._on_region_clicked)
        self._treemap.region_clicked.connect(self._on_region_clicked)

        self._toggle_btn = QPushButton("区域视图")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setFixedHeight(24)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                padding: 2px 10px; border: 1px solid #E2E8F0;
                border-radius: 4px; font-size: 10px; background: #F8FAFC;
                color: #475569;
            }
            QPushButton:hover { border-color: #3B82F6; color: #3B82F6; }
            QPushButton:checked { background: #EFF6FF; border-color: #3B82F6; color: #2563EB; }
        """)
        self._toggle_btn.toggled.connect(self._on_toggle)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self._toggle_btn)
        header.addStretch()

        layout.addLayout(header)
        layout.addWidget(self._stack, 1)

    def set_data(self, heatmap: dict):
        config = ConfigManager.load()
        product_name = config.get("last_product_name", "")
        self._schematic.set_data(heatmap, product_name)
        self._treemap.set_data(heatmap)

    def _on_toggle(self, checked: bool):
        self._stack.setCurrentIndex(1 if checked else 0)
        self._toggle_btn.setText("占比视图" if checked else "区域视图")

    def _on_region_clicked(self, region_name: str):
        self.drilldown_triggered.emit("Area", region_name)
