from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QFont


class DraggableThumbnailCard(QFrame):
    """可拖拽缩略卡：图标 + 名称 + 选中高亮 + 拖拽"""

    clicked = pyqtSignal(str)

    def __init__(self, card_id: str, card_name: str, icon: str = "📄", parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.card_name = card_name
        self._selected = False
        self._drag_start_pos = QPoint()
        self._drag_in_progress = False

        self.setFixedSize(100, 96)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        layout.setSpacing(4)

        self._icon_label = QLabel(icon)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setStyleSheet("font-size: 24px; border: none; background: transparent;")
        layout.addWidget(self._icon_label, 1)

        self._name_label = QLabel(card_name)
        self._name_label.setAlignment(Qt.AlignCenter)
        self._name_label.setWordWrap(True)
        self._name_label.setStyleSheet("font-size: 10px; font-weight: 600; border: none; background: transparent;")
        layout.addWidget(self._name_label)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet("""
                DraggableThumbnailCard {
                    border: 2px solid #3B82F6;
                    border-radius: 10px;
                    background-color: #EFF6FF;
                }
            """)
        else:
            self.setStyleSheet("""
                DraggableThumbnailCard {
                    border: 1px solid #E2E8F0;
                    border-radius: 10px;
                    background-color: #FFFFFF;
                }
                DraggableThumbnailCard:hover {
                    border-color: #93C5FD;
                    background-color: #F8FAFC;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self._drag_in_progress = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if (event.pos() - self._drag_start_pos).manhattanLength() > 10:
                self._drag_in_progress = True
                self._start_drag(event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self._drag_in_progress:
            self.clicked.emit(self.card_id)
        super().mouseReleaseEvent(event)

    def _start_drag(self, pos):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/card-id", self.card_id.encode("utf-8"))
        drag.setMimeData(mime)
        pixmap = self.grab()
        drag.setPixmap(pixmap.scaled(80, 77, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.setHotSpot(pos)
        drag.exec_(Qt.CopyAction)
