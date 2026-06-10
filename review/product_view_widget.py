import os
from PyQt5.QtWidgets import QWidget, QSizePolicy, QToolTip
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap, QImage
from editor.product_layout import Region, ShapeType, ProductLayoutModel
from editor.collision import hit_test_rectangle, hit_test_circle


class ProductViewWidget(QWidget):
    region_clicked = pyqtSignal(str)
    region_hovered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(200, 200)
        self.setMouseTracking(True)

        self._regions: list[Region] = []
        self._canvas_width = 1000
        self._canvas_height = 1000
        self._product_name: str = ""
        self._highlight_region_id: str = ""
        self._selected_region_id: str = ""
        self._hover_region_id: str = ""
        self._ng_region_ids: set = set()
        self._pixmap: QPixmap = None
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_animation)
        self._anim_intensity = 0.0
        self._anim_direction = 1
        self._anim_running = False

    def set_layout(self, layout: ProductLayoutModel):
        self._product_name = layout.product_name
        self._regions = layout.regions
        self._canvas_width = layout.canvas_width
        self._canvas_height = layout.canvas_height
        if layout.background_image and os.path.exists(layout.background_image):
            self._set_pixmap(layout.background_image)
        else:
            self._pixmap = None
        self.update()

    def set_regions(self, regions: list[Region], canvas_width=1000, canvas_height=1000, product_name=""):
        self._product_name = product_name
        self._regions = regions
        self._canvas_width = canvas_width
        self._canvas_height = canvas_height
        self.update()

    def set_background_image(self, image_path: str):
        self._set_pixmap(image_path)
        self.update()

    def _set_pixmap(self, image_path: str):
        if image_path and os.path.exists(image_path):
            pix = QPixmap(image_path)
            if not pix.isNull():
                self._pixmap = pix
                return
        self._pixmap = None

    def set_highlight_region(self, region_id: str):
        self._highlight_region_id = region_id or ""
        self.update()

    def set_selected_region(self, region_id: str):
        self._selected_region_id = region_id or ""
        self.update()

    def clear_selected_region(self):
        self._selected_region_id = ""
        self.update()

    def set_ng_regions(self, region_ids: set):
        self._ng_region_ids = region_ids
        self._stop_animation()
        self.update()

    def _start_animation(self):
        pass

    def _stop_animation(self):
        self._anim_running = False
        self._anim_intensity = 0.0
        self._anim_timer.stop()

    def _tick_animation(self):
        self._anim_intensity += 0.05 * self._anim_direction
        if self._anim_intensity >= 1.0:
            self._anim_direction = -1
        elif self._anim_intensity <= 0.0:
            self._anim_direction = 1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#F8FAFC"))

        margin = 8
        draw_w = w - 2 * margin
        draw_h = h - 2 * margin

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(draw_w, draw_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            ox = margin + (draw_w - scaled.width()) // 2
            oy = margin + (draw_h - scaled.height()) // 2
            p.drawPixmap(ox, oy, scaled)
            img_w = scaled.width()
            img_h = scaled.height()
        else:
            p.setPen(QPen(QColor("#CBD5E1"), 1))
            p.setBrush(QColor("#F1F5F9"))
            p.drawRoundedRect(margin, margin, draw_w, draw_h, 8, 8)
            p.setPen(QColor("#94A3B8"))
            p.setFont(QFont("Segoe UI", 12))
            label = self._product_name if self._product_name else "无产品示意图"
            p.drawText(QRectF(margin, margin, draw_w, draw_h), Qt.AlignCenter, label)
            img_w = draw_w
            img_h = draw_h
            ox = margin
            oy = margin

        scale_x = img_w / self._canvas_width
        scale_y = img_h / self._canvas_height

        for region in sorted(self._regions, key=lambda r: r.z_order):
            if not region.visible:
                continue
            self._draw_region(p, region, ox, oy, scale_x, scale_y)

        p.end()

    def _draw_region(self, p: QPainter, region: Region, ox: float, oy: float, sx: float, sy: float):
        rx = ox + region.x * sx
        ry = oy + region.y * sy
        rw = region.width * sx
        rh = region.height * sy

        if rw <= 0 or rh <= 0:
            return

        color = QColor(region.color)
        is_highlight = (region.id == self._highlight_region_id)
        is_selected = (region.id == self._selected_region_id)
        is_hover = (region.id == self._hover_region_id)
        is_ng = (region.id in self._ng_region_ids)

        rect = QRectF(rx, ry, rw, rh)

        # Layer 0: White fill to obscure lower overlapping regions
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 220))
        self._draw_shape(p, rect, region, sx, sy)

        # Layer 1: Base region
        p.setPen(QPen(color, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        self._draw_shape(p, rect, region, sx, sy)

        # Layer 2: NG overlay (semi-transparent red)
        if is_ng:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(255, 0, 0, 80), Qt.BrushStyle.SolidPattern))
            self._draw_shape(p, rect, region, sx, sy)

        # Layer 3: Hatch overlay for current selected region (white diagonal lines)
        if is_selected:
            hatch = QBrush(Qt.BDiagPattern)
            hatch.setColor(QColor(255, 255, 255, 120))
            p.setBrush(hatch)
            p.setPen(Qt.NoPen)
            self._draw_shape(p, rect, region, sx, sy)

        # Layer 4: Highlight border (defect click)
        if is_highlight:
            p.setPen(QPen(color.lighter(130), 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            self._draw_shape(p, rect, region, sx, sy)

        # Layer 5: Hover border
        if is_hover:
            p.setPen(QPen(QColor("#4F6CF7"), 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            self._draw_shape(p, rect, region, sx, sy)

        if region.name:
            p.setPen(QColor("#1E293B"))
            p.setFont(QFont("Segoe UI", 9, QFont.Bold))
            p.drawText(rect, Qt.AlignCenter, region.name)

    def _draw_shape(self, p, rect, region, sx=1.0, sy=1.0):
        if region.shape_type in (ShapeType.RECTANGLE,):
            p.drawRect(rect)
        elif region.shape_type in (ShapeType.CIRCLE,):
            p.drawEllipse(rect)

    def _hit_test_region(self, pos: QPointF) -> str:
        margin = 8
        draw_w = self.width() - 2 * margin
        draw_h = self.height() - 2 * margin

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(draw_w, draw_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            ox = margin + (draw_w - scaled.width()) // 2
            oy = margin + (draw_h - scaled.height()) // 2
            img_w = scaled.width()
            img_h = scaled.height()
        else:
            ox = margin
            oy = margin
            img_w = draw_w
            img_h = draw_h

        sx = img_w / self._canvas_width
        sy = img_h / self._canvas_height

        for region in reversed(self._regions):
            if not region.visible:
                continue
            rx = ox + region.x * sx
            ry = oy + region.y * sy
            rw = region.width * sx
            rh = region.height * sy
            rect = QRectF(rx, ry, rw, rh)

            hit = False
            if region.shape_type == ShapeType.RECTANGLE:
                hit = hit_test_rectangle(pos, rect)
            elif region.shape_type == ShapeType.CIRCLE:
                hit = hit_test_circle(pos, rect.center(), rect.width() / 2.0)

            if hit:
                return region.id
        return ""

    def mouseReleaseEvent(self, event):
        rid = self._hit_test_region(event.pos())
        if rid:
            self.region_clicked.emit(rid)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        rid = self._hit_test_region(event.pos())
        if rid != self._hover_region_id:
            self._hover_region_id = rid
            self.update()
            if rid:
                for r in self._regions:
                    if r.id == rid:
                        QToolTip.showText(self.mapToGlobal(event.pos()), f"区域: {r.name}\n类型: {r.shape_type.value}")
                        break
                self.region_hovered.emit(rid)
            else:
                QToolTip.hideText()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_region_id = ""
        self.update()
        QToolTip.hideText()
        super().leaveEvent(event)
