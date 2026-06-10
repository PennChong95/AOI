from typing import Dict, Optional
from PyQt5.QtWidgets import QWidget, QSplitter, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from dashboard.core.slot_manager import SlotManager
from dashboard.core.slot_widget import SlotWidget


class DashboardWorkspace(QWidget):
    """中央工作区：嵌套 QSplitter 管理所有槽位"""

    slot_activated = pyqtSignal(int)
    slot_maximize_requested = pyqtSignal(int)
    card_dropped = pyqtSignal(int, str)

    def __init__(self, slot_manager: SlotManager, parent=None):
        super().__init__(parent)
        self.slot_manager = slot_manager
        self._slot_widgets: Dict[int, SlotWidget] = {}
        self._maximized_slot_id: Optional[int] = None

        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._root_splitter = QSplitter(Qt.Horizontal)
        self._root_splitter.setHandleWidth(4)
        self._root_splitter.setChildrenCollapsible(False)
        self._root_splitter.setStyleSheet("""
            QSplitter::handle {
                background: #E2E8F0; margin: 6px 0;
                border-radius: 2px;
            }
            QSplitter::handle:hover { background: #3B82F6; }
            QSplitter::handle:horizontal { width: 4px; }
            QSplitter::handle:vertical { height: 4px; }
        """)
        layout.addWidget(self._root_splitter, 1)

        self.slot_manager.slot_added.connect(self._on_slot_added)
        self.slot_manager.slot_removed.connect(self._on_slot_removed)
        self.slot_manager.slot_activated.connect(self._on_slot_activated)

    def _on_slot_added(self, slot_id: int):
        slot_widget = SlotWidget(slot_id)
        slot_widget.slot_clicked.connect(lambda sid: self.slot_manager.activate_slot(sid))
        slot_widget.slot_double_clicked.connect(self.slot_maximize_requested.emit)
        slot_widget.card_dropped.connect(self.card_dropped.emit)
        self._slot_widgets[slot_id] = slot_widget
        self._root_splitter.addWidget(slot_widget)
        sizes = [100] * self._root_splitter.count()
        self._root_splitter.setSizes(sizes)

    def _on_slot_removed(self, slot_id: int):
        widget = self._slot_widgets.pop(slot_id, None)
        if widget:
            if widget.current_card:
                widget.current_card.setParent(None)
            widget.deleteLater()

    def _on_slot_activated(self, slot_id: int):
        for sid, widget in self._slot_widgets.items():
            widget.set_activated(sid == slot_id)
        self.slot_activated.emit(slot_id)

    def set_slot_card(self, slot_id: int, card):
        if slot_id in self._slot_widgets:
            self._slot_widgets[slot_id].set_card(card)

    def toggle_slot_maximized(self, slot_id: int):
        if self._maximized_slot_id == slot_id:
            for widget in self._slot_widgets.values():
                widget.show()
            self._maximized_slot_id = None
        else:
            for sid, widget in self._slot_widgets.items():
                widget.setVisible(sid == slot_id)
            self._maximized_slot_id = slot_id

    def apply_layout_preset(self, preset: str):
        """应用预设布局（仅重置槽位，卡片恢复由 DashboardView 处理）"""
        while self.slot_manager.slots:
            self.slot_manager.remove_slot(self.slot_manager.slots[0].slot_id)

        if preset == "1x1":
            self._root_splitter.setOrientation(Qt.Horizontal)
            self.slot_manager.add_slot()
        elif preset == "1x2":
            self._root_splitter.setOrientation(Qt.Horizontal)
            self.slot_manager.add_slot()
            self.slot_manager.add_slot()
        elif preset == "2x1":
            self._root_splitter.setOrientation(Qt.Vertical)
            self.slot_manager.add_slot()
            self.slot_manager.add_slot()
        elif preset == "2x2":
            self._root_splitter.setOrientation(Qt.Vertical)
            top = QSplitter(Qt.Horizontal)
            top.setHandleWidth(4)
            bottom = QSplitter(Qt.Horizontal)
            bottom.setHandleWidth(4)
            self._root_splitter.addWidget(top)
            self._root_splitter.addWidget(bottom)
            for i in range(4):
                sid = self.slot_manager.add_slot()
                w = self._slot_widgets[sid]
                w.setParent(None)
                if i < 2:
                    top.addWidget(w)
                else:
                    bottom.addWidget(w)
            for s in [top, bottom]:
                s.setSizes([100, 100])
                s.setChildrenCollapsible(False)
                s.setStyleSheet(self._root_splitter.styleSheet())
            self._root_splitter.setSizes([100, 100])
        elif preset == "1x3":
            self._root_splitter.setOrientation(Qt.Horizontal)
            for _ in range(3):
                self.slot_manager.add_slot()
        elif preset == "3x1":
            self._root_splitter.setOrientation(Qt.Vertical)
            for _ in range(3):
                self.slot_manager.add_slot()

        if self.slot_manager.slots:
            self.slot_manager.activate_slot(self.slot_manager.slots[0].slot_id)
