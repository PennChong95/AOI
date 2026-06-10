from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget
from PyQt5.QtCore import Qt, QEvent, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent


class SlotWidget(QFrame):
    """单个槽位UI组件：容器 + 激活态 + 拖放目标"""

    slot_clicked = pyqtSignal(int)
    slot_double_clicked = pyqtSignal(int)
    card_dropped = pyqtSignal(int, str)

    def __init__(self, slot_id: int, parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self._activated = False
        self._drag_hover = False
        self.current_card = None
        self.setAcceptDrops(True)
        self._update_style()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self.setMinimumSize(200, 120)

        self._placeholder = QLabel("暂无卡片\n从下方展开缩略栏，拖拽卡片至此槽位")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setWordWrap(True)
        self._placeholder.setStyleSheet("""
            QLabel {
                color: #94A3B8;
                font-size: 13px;
                background: transparent;
                border: none;
                padding: 20px;
            }
        """)
        self._placeholder.setAcceptDrops(True)
        self._placeholder.installEventFilter(self)
        self._layout.addWidget(self._placeholder)

    def set_card(self, card):
        self._placeholder.setVisible(card is None)
        if self.current_card:
            self._uninstall_drop_proxy(self.current_card)
            self.current_card.setParent(None)
        self.current_card = card
        if card:
            self._layout.addWidget(card)
            self._install_drop_proxy(card)
            card.show()

    def _install_drop_proxy(self, root: QWidget):
        root.setAcceptDrops(True)
        root.installEventFilter(self)
        for child in root.findChildren(QWidget):
            child.setAcceptDrops(True)
            child.installEventFilter(self)

    def _uninstall_drop_proxy(self, root: QWidget):
        try:
            root.removeEventFilter(self)
        except Exception:
            pass
        for child in root.findChildren(QWidget):
            try:
                child.removeEventFilter(self)
            except Exception:
                pass

    def set_activated(self, activated: bool):
        self._activated = activated
        self._update_style()

    def _update_style(self):
        if self._drag_hover:
            self.setStyleSheet("""
                SlotWidget {
                    border: 2px solid #3B82F6;
                    border-radius: 8px;
                    background-color: #EFF6FF;
                }
            """)
        elif self._activated:
            self.setStyleSheet("""
                SlotWidget {
                    border: 2px solid #3B82F6;
                    border-radius: 8px;
                    background-color: #FFFFFF;
                }
            """)
        else:
            self.setStyleSheet("""
                SlotWidget {
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                    background-color: #FFFFFF;
                }
                SlotWidget:hover {
                    border-color: #93C5FD;
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.slot_clicked.emit(self.slot_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.slot_double_clicked.emit(self.slot_id)
        super().mouseDoubleClickEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasFormat("application/card-id"):
            self._accept_drag(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/card-id"):
            self._accept_drag(event)

    def dragLeaveEvent(self, event):
        self._drag_hover = False
        self._update_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        self._handle_drop(event)

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.DragEnter, QEvent.DragMove):
            if event.mimeData().hasFormat("application/card-id"):
                self._accept_drag(event)
                return True
        if event.type() == QEvent.DragLeave:
            self._drag_hover = False
            self._update_style()
            return False
        if event.type() == QEvent.Drop:
            if event.mimeData().hasFormat("application/card-id"):
                self._handle_drop(event)
                return True
        return super().eventFilter(obj, event)

    def _accept_drag(self, event):
        self._drag_hover = True
        self._update_style()
        event.acceptProposedAction()

    def _handle_drop(self, event):
        self._drag_hover = False
        self._update_style()
        card_id = bytes(event.mimeData().data("application/card-id")).decode()
        self.card_dropped.emit(self.slot_id, card_id)
        event.acceptProposedAction()
