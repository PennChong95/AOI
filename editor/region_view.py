from PyQt5.QtWidgets import QGraphicsView
from PyQt5.QtCore import Qt, QRectF, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QWheelEvent, QMouseEvent


class RegionGraphicsView(QGraphicsView):
    drawRequested = pyqtSignal(object)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMouseTracking(True)
        self._draw_mode = False
        self._zoom = 1.0

    def setup_focus(self):
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    def set_draw_mode(self, enabled: bool):
        self._draw_mode = enabled
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.scene().deleteRequested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if self._draw_mode and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.drawRequested.emit(scene_pos)
            event.accept()
            return
        super().mousePressEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        factor = 1.15
        if event.angleDelta().y() > 0:
            self._zoom *= factor
            self.scale(factor, factor)
        else:
            self._zoom /= factor
            self.scale(1 / factor, 1 / factor)

    def zoom_fit(self):
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_actual(self):
        self.resetTransform()
        self._zoom = 1.0

    @property
    def zoom(self):
        return self._zoom
