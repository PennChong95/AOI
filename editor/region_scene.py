import os
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsItem, QMenu
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QKeyEvent, QFont, QPixmap
from editor.region_items import RegionItemBase


class RegionScene(QGraphicsScene):
    deleteRequested = pyqtSignal()
    pasteRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._draw_grid = True
        self._clipboard_available = False
        self._product_bounds = QRectF(0, 0, 1000, 800)
        self._background_pixmap = None
        self.setSceneRect(-5000, -5000, 10000, 10000)

    def set_product_bounds(self, x: float, y: float, w: float, h: float):
        self._product_bounds = QRectF(x, y, w, h)
        self.update()

    def set_background_image(self, image_path: str):
        if image_path and os.path.exists(image_path):
            pix = QPixmap(image_path)
            if not pix.isNull():
                self._background_pixmap = pix
                self.update()
                return
        self._background_pixmap = None
        self.update()

    def set_draw_grid(self, enabled: bool):
        self._draw_grid = enabled
        self.update()

    def drawBackground(self, painter: QPainter, rect: QRectF):
        b = self._product_bounds
        margin = 40
        draw_rect = b.adjusted(-margin, -margin, margin, margin)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#F8F9FA"))
        painter.drawRect(draw_rect)

        if self._background_pixmap and not self._background_pixmap.isNull():
            scaled = self._background_pixmap.scaled(
                int(b.width()), int(b.height()),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            ox = b.x() + (b.width() - scaled.width()) / 2
            oy = b.y() + (b.height() - scaled.height()) / 2
            painter.drawPixmap(int(ox), int(oy), scaled)
        else:
            painter.setBrush(QColor("#FFFFFF"))
            painter.setPen(QPen(QColor("#DEE2E6"), 1))
            painter.drawRect(b)

        painter.setPen(QPen(QColor("#ADB5BD"), 1, Qt.PenStyle.DashLine))
        painter.drawRect(b)

        painter.setPen(QColor("#6C757D"))
        font = QFont("Segoe UI", 10)
        painter.setFont(font)
        painter.drawText(b.adjusted(6, 4, 0, 0), Qt.AlignLeft | Qt.AlignTop, "产品区域")

        if self._draw_grid:
            painter.setPen(QPen(QColor(200, 200, 200, 40), 1))
            left = int(rect.left()) - int(rect.left()) % 20
            top = int(rect.top()) - int(rect.top()) % 20
            x = left
            while x < rect.right():
                painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
                x += 20
            y = top
            while y < rect.bottom():
                painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
                y += 20

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.deleteRequested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform() if self.views() else None)
        if isinstance(item, RegionItemBase):
            super().contextMenuEvent(event)
            return
        menu = QMenu()
        act_paste = menu.addAction("粘贴")
        act_paste.setEnabled(self._clipboard_available)
        action = menu.exec_(event.screenPos())
        if action == act_paste:
            self.pasteRequested.emit()
        event.accept()

    def get_region_items(self):
        items = [item for item in self.items() if isinstance(item, RegionItemBase)]
        items.sort(key=lambda x: x.zValue())
        return items

    def get_region_item_by_id(self, region_id: str):
        for item in self.items():
            if isinstance(item, RegionItemBase) and item.region_id == region_id:
                return item
        return None
