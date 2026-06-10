from PyQt5.QtWidgets import QScrollArea, QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from dashboard.core.thumbnail_card import DraggableThumbnailCard


class HorizontalScrollArea(QScrollArea):
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta != 0:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta)
            event.accept()
        else:
            super().wheelEvent(event)


class ThumbnailBar(QWidget):
    """水平可滚动缩略卡栏"""

    card_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards = {}  # card_id -> DraggableThumbnailCard
        self.setFixedHeight(120)
        self.setStyleSheet("background: transparent; border: none;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 4, 12, 4)

        self._scroll = HorizontalScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:horizontal {
                height: 4px; background: #F1F5F9; border-radius: 2px;
            }
            QScrollBar::handle:horizontal {
                background: #CBD5E1; border-radius: 2px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        """)

        self._inner = QWidget()
        self._inner.setStyleSheet("background: transparent; border: none;")
        self._layout = QHBoxLayout(self._inner)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)
        self._layout.addStretch()

        self._scroll.setWidget(self._inner)
        outer.addWidget(self._scroll)

    def add_card(self, card_id: str, card_name: str, icon: str = "📄") -> DraggableThumbnailCard:
        thumb = DraggableThumbnailCard(card_id, card_name, icon)
        thumb.clicked.connect(self._on_thumb_clicked)
        self._cards[card_id] = thumb
        idx = self._layout.count() - 1
        self._layout.insertWidget(idx, thumb)
        return thumb

    def remove_card(self, card_id: str):
        thumb = self._cards.pop(card_id, None)
        if thumb:
            self._layout.removeWidget(thumb)
            thumb.deleteLater()

    def set_selected(self, card_id: str):
        for cid, thumb in self._cards.items():
            thumb.set_selected(cid == card_id)

    def get_thumb(self, card_id: str):
        return self._cards.get(card_id)

    def _on_thumb_clicked(self, card_id: str):
        self.card_clicked.emit(card_id)
