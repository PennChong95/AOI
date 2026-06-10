from PyQt5.QtWidgets import QGraphicsObject, QGraphicsItem, QStyleOptionGraphicsItem, QGraphicsSceneMouseEvent, QMenu
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QCursor, QFont
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from editor.product_layout import ShapeType


HANDLE_SIZE = 8
HANDLE_PEN = QPen(Qt.GlobalColor.black, 1)
HANDLE_BRUSH = QBrush(Qt.GlobalColor.white)

TL, TR, BL, BR, TC, BC, LC, RC = range(8)
MIN_SIZE = 10


class RegionItemBase(QGraphicsObject):
    region_geometry_changed = pyqtSignal()
    region_selected = pyqtSignal(str)
    contextMenuAction = pyqtSignal(str, str)
    region_clicked = pyqtSignal(str)

    Type = QGraphicsItem.UserType + 1

    def __init__(self, region_id: str, parent=None):
        super().__init__(parent)
        self.region_id = region_id
        self.m_width = 100
        self.m_height = 100
        self.m_color = QColor("#00A0FF")
        self.m_is_hovered = False
        self.m_shape_type = ShapeType.RECTANGLE
        self.m_name = ""
        self.m_polygon_points = []
        self._highlight_intensity = 0.0
        self._is_ng_highlight = False
        self._clipboard_available = False

        self._resizing = False
        self._resize_handle = -1
        self._hidden = False
        self._drag_start_pos = QPointF()
        self._drag_start_rect = QRectF()
        self._drag_start_scene_pos = QPointF()
        self._drag_start_item_pos = QPointF()
        self._bounds_rect = QRectF()

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def type(self) -> int:
        return self.Type

    def boundingRect(self) -> QRectF:
        margin = HANDLE_SIZE + 6
        return QRectF(-margin, -margin, self.m_width + 2 * margin, self.m_height + 2 * margin)

    def _item_rect(self) -> QRectF:
        return QRectF(0, 0, self.m_width, self.m_height)

    def _handle_positions(self):
        r = self._item_rect()
        return [
            r.topLeft(), r.topRight(), r.bottomLeft(), r.bottomRight(),
            QPointF(r.center().x(), r.top()),
            QPointF(r.center().x(), r.bottom()),
            QPointF(r.left(), r.center().y()),
            QPointF(r.right(), r.center().y()),
        ]

    def _handle_at(self, pos: QPointF) -> int:
        hs = HANDLE_SIZE * 1.5
        for i, hp in enumerate(self._handle_positions()):
            if abs(pos.x() - hp.x()) <= hs and abs(pos.y() - hp.y()) <= hs:
                return i
        return -1

    def _handle_cursor(self, handle: int) -> Qt.CursorShape:
        cursors = {
            TL: Qt.CursorShape.SizeFDiagCursor, BR: Qt.CursorShape.SizeFDiagCursor,
            TR: Qt.CursorShape.SizeBDiagCursor, BL: Qt.CursorShape.SizeBDiagCursor,
            TC: Qt.CursorShape.SizeVerCursor, BC: Qt.CursorShape.SizeVerCursor,
            LC: Qt.CursorShape.SizeHorCursor, RC: Qt.CursorShape.SizeHorCursor,
        }
        return cursors.get(handle, Qt.CursorShape.ArrowCursor)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        if self._hidden:
            painter.setPen(QPen(QColor("#CBD5E1"), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(200, 200, 200, 30)))
            self.paint_shape(painter)
            painter.save()
            painter.setPen(QColor("#94A3B8"))
            font = QFont("Segoe UI", 10, QFont.Bold)
            painter.setFont(font)
            r = self._item_rect()
            if r.width() > 20 and r.height() > 16:
                painter.drawText(r, Qt.AlignCenter, self.m_name)
            painter.restore()
            return
        if self._is_ng_highlight:
            self._paint_ng(painter)
            self.paint_shape(painter)
        else:
            # White fill to obscure lower overlapping regions
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 220))
            self.paint_shape(painter)

            if self.m_is_hovered:
                glow_pen = QPen(QColor("#4F6CF7"), 4)
                painter.setPen(glow_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                self.paint_shape(painter)

            if self.isSelected():
                painter.setPen(QPen(self.m_color.lighter(130), 3))
                painter.setBrush(QBrush(self.m_color, Qt.BrushStyle.Dense4Pattern))
            elif self.m_is_hovered:
                painter.setPen(QPen(self.m_color.lighter(140), 3))
                painter.setBrush(QBrush(self.m_color, Qt.BrushStyle.Dense3Pattern))
            else:
                painter.setPen(QPen(self.m_color, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)

            self.paint_shape(painter)

        self._draw_name(painter)
        if self.isSelected() and not self._resizing:
            self.draw_resize_handles(painter)

    def _draw_name(self, painter: QPainter):
        if not self.m_name:
            return
        painter.save()
        painter.setPen(QColor("#1E293B"))
        font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font)
        r = self._item_rect()
        if r.width() > 20 and r.height() > 16:
            painter.drawText(r, Qt.AlignCenter, self.m_name)
        painter.restore()

    def _paint_ng(self, painter: QPainter):
        intensity = self._highlight_intensity
        ng_color = QColor(255, 50, 50).lighter(100 + int(intensity * 50))
        fill_color = QColor(255, 50, 50, int(30 + intensity * 50))
        painter.setPen(QPen(ng_color, 3 + intensity * 2))
        painter.setBrush(QBrush(fill_color))

    def paint_shape(self, painter: QPainter):
        raise NotImplementedError

    def draw_resize_handles(self, painter: QPainter):
        handles = self._handle_positions()
        painter.setPen(HANDLE_PEN)
        painter.setBrush(HANDLE_BRUSH)
        for h in handles:
            painter.drawRect(QRectF(h.x() - HANDLE_SIZE / 2, h.y() - HANDLE_SIZE / 2, HANDLE_SIZE, HANDLE_SIZE))

    def hoverMoveEvent(self, event):
        handle = self._handle_at(event.pos())
        if handle >= 0:
            self.setCursor(self._handle_cursor(handle))
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverMoveEvent(event)

    def hoverEnterEvent(self, event):
        self.m_is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.m_is_hovered = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        handle = self._handle_at(event.pos())
        if handle >= 0 and self.isSelected():
            self._resizing = True
            self._resize_handle = handle
            self._drag_start_pos = event.pos()
            self._drag_start_scene_pos = event.scenePos()
            self._drag_start_rect = QRectF(0, 0, self.m_width, self.m_height)
            self._drag_start_item_pos = self.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self._resizing and self._resize_handle >= 0:
            delta = event.scenePos() - self._drag_start_scene_pos
            self._apply_resize(delta)
            self.region_geometry_changed.emit()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self._resizing:
            self._resizing = False
            self._resize_handle = -1
            self.region_geometry_changed.emit()
            event.accept()
            return
        self.region_clicked.emit(self.region_id)
        super().mouseReleaseEvent(event)

    def _apply_resize(self, delta: QPointF):
        r = QRectF(self._drag_start_rect)
        dx, dy = delta.x(), delta.y()
        h = self._resize_handle

        if h == TL:
            r.setLeft(r.left() + dx); r.setTop(r.top() + dy)
        elif h == TR:
            r.setRight(r.right() + dx); r.setTop(r.top() + dy)
        elif h == BL:
            r.setLeft(r.left() + dx); r.setBottom(r.bottom() + dy)
        elif h == BR:
            r.setRight(r.right() + dx); r.setBottom(r.bottom() + dy)
        elif h == TC:
            r.setTop(r.top() + dy)
        elif h == BC:
            r.setBottom(r.bottom() + dy)
        elif h == LC:
            r.setLeft(r.left() + dx)
        elif h == RC:
            r.setRight(r.right() + dx)

        if r.width() < MIN_SIZE:
            r.setWidth(MIN_SIZE)
        if r.height() < MIN_SIZE:
            r.setHeight(MIN_SIZE)

        self.prepareGeometryChange()
        new_w = max(MIN_SIZE, r.width())
        new_h = max(MIN_SIZE, r.height())
        new_pos = self._drag_start_item_pos + QPointF(r.left(), r.top())

        if not self._bounds_rect.isNull() and not self._bounds_rect.isEmpty():
            min_x = self._bounds_rect.left()
            min_y = self._bounds_rect.top()
            max_x = self._bounds_rect.right() - new_w
            max_y = self._bounds_rect.bottom() - new_h
            new_pos.setX(max(min_x, min(max_x, new_pos.x())))
            new_pos.setY(max(min_y, min(max_y, new_pos.y())))
            new_w = min(new_w, self._bounds_rect.right() - new_pos.x())
            new_h = min(new_h, self._bounds_rect.bottom() - new_pos.y())
            new_w = max(MIN_SIZE, new_w)
            new_h = max(MIN_SIZE, new_h)

        old_pos = self._drag_start_item_pos
        old_w = self._drag_start_rect.width()
        old_h = self._drag_start_rect.height()
        if h in (TL, BL, LC):
            new_w = min(new_w, old_pos.x() + old_w - new_pos.x())
        if h in (TL, TR, TC):
            new_h = min(new_h, old_pos.y() + old_h - new_pos.y())
        new_w = max(MIN_SIZE, new_w)
        new_h = max(MIN_SIZE, new_h)

        self.m_width = new_w
        self.m_height = new_h
        self.setPos(new_pos)
        self.update()

    def set_bounds(self, bounds: QRectF):
        self._bounds_rect = bounds

    def _clamp_pos(self, pos: QPointF) -> QPointF:
        if self._bounds_rect.isNull() or self._bounds_rect.isEmpty():
            return pos
        min_x = self._bounds_rect.left()
        min_y = self._bounds_rect.top()
        max_x = self._bounds_rect.right() - self.m_width
        max_y = self._bounds_rect.bottom() - self.m_height
        return QPointF(max(min_x, min(max_x, pos.x())), max(min_y, min(max_y, pos.y())))

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            clamped = self._clamp_pos(value)
            self.region_geometry_changed.emit()
            return clamped
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        self.region_selected.emit(self.region_id)
        super().mouseDoubleClickEvent(event)

    def set_ng_highlight(self, enabled: bool, intensity: float = 0.0):
        self._is_ng_highlight = enabled
        self._highlight_intensity = intensity
        self.update()

    def set_highlight_intensity(self, value: float):
        self._highlight_intensity = value
        self.update()

    def contextMenuEvent(self, event):
        menu = QMenu()
        act_copy = menu.addAction("复制")
        act_paste = menu.addAction("粘贴")
        act_paste.setEnabled(self._clipboard_available)
        menu.addSeparator()
        act_rename = menu.addAction("重命名")
        act_delete = menu.addAction("删除")
        menu.addSeparator()
        act_bring_forward = menu.addAction("上移一层")
        act_send_backward = menu.addAction("下移一层")
        menu.addSeparator()
        act_bring_to_front = menu.addAction("置于顶层")
        act_send_to_back = menu.addAction("置于底层")

        action = menu.exec_(event.screenPos())
        if action == act_copy:
            self.contextMenuAction.emit(self.region_id, "copy")
        elif action == act_paste:
            self.contextMenuAction.emit(self.region_id, "paste")
        elif action == act_rename:
            self.contextMenuAction.emit(self.region_id, "rename")
        elif action == act_delete:
            self.contextMenuAction.emit(self.region_id, "delete")
        elif action == act_bring_forward:
            self.contextMenuAction.emit(self.region_id, "bring_forward")
        elif action == act_send_backward:
            self.contextMenuAction.emit(self.region_id, "send_backward")
        elif action == act_bring_to_front:
            self.contextMenuAction.emit(self.region_id, "bring_to_front")
        elif action == act_send_to_back:
            self.contextMenuAction.emit(self.region_id, "send_to_back")
        event.accept()

    def hit_test(self, point: QPointF) -> bool:
        from editor.collision import hit_test_rectangle, hit_test_circle
        rect = QRectF(self.pos().x(), self.pos().y(), self.m_width, self.m_height)
        if self.m_shape_type == ShapeType.RECTANGLE:
            return hit_test_rectangle(point, rect)
        elif self.m_shape_type == ShapeType.CIRCLE:
            return hit_test_circle(point, rect.center(), min(rect.width(), rect.height()) / 2.0)
        return False


class RectRegionItem(RegionItemBase):
    def __init__(self, region_id: str, parent=None):
        super().__init__(region_id, parent)
        self.m_shape_type = ShapeType.RECTANGLE

    def paint_shape(self, painter: QPainter):
        painter.drawRect(QRectF(0, 0, self.m_width, self.m_height))


class CircleRegionItem(RegionItemBase):
    def __init__(self, region_id: str, parent=None):
        super().__init__(region_id, parent)
        self.m_shape_type = ShapeType.CIRCLE

    def paint_shape(self, painter: QPainter):
        painter.drawEllipse(QRectF(0, 0, self.m_width, self.m_height))
