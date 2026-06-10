from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QFrame, QPushButton, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from dashboard.core.dashboard_card import DashboardCard


class HeroThumbnailLayout(QWidget):
    """
    单 Hero + 缩略按钮栏 布局管理器
    - 顶部：外部注入的 KPI+Header
    - 中部：单卡 Hero 区
    - 底部：QScrollArea 水平缩略图标+名称按钮栏
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_cards = {}         # card_id -> DashboardCard
        self._current_hero_id = None
        self._thumb_buttons = {}     # card_id -> QPushButton

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部区域（外部注入）
        self._top_container = QWidget()
        self._top_container.setStyleSheet("background: transparent; border: none;")
        self._top_layout = QVBoxLayout(self._top_container)
        self._top_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._top_container)

        # Hero 区 — 单卡
        self._hero_widget = QFrame()
        self._hero_widget.setStyleSheet("background: transparent; border: none;")
        self._hero_layout = QVBoxLayout(self._hero_widget)
        self._hero_layout.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(self._hero_widget, 1)

        # 缩略按钮栏
        self._thumb_container = QWidget()
        self._thumb_container.setFixedHeight(64)
        self._thumb_container.setStyleSheet("background: transparent; border: none;")

        thumb_outer = QVBoxLayout(self._thumb_container)
        thumb_outer.setContentsMargins(0, 0, 0, 6)

        self._thumb_scroll = QScrollArea()
        self._thumb_scroll.setWidgetResizable(True)
        self._thumb_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._thumb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._thumb_scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:horizontal {
                height: 4px; background: #F1F5F9; border-radius: 2px;
            }
            QScrollBar::handle:horizontal {
                background: #CBD5E1; border-radius: 2px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
            }
        """)

        self._thumb_inner = QWidget()
        self._thumb_inner.setStyleSheet("background: transparent; border: none;")
        self._thumb_layout = QHBoxLayout(self._thumb_inner)
        self._thumb_layout.setContentsMargins(12, 4, 12, 4)
        self._thumb_layout.setSpacing(8)
        self._thumb_layout.addStretch()

        self._thumb_scroll.setWidget(self._thumb_inner)
        thumb_outer.addWidget(self._thumb_scroll)
        layout.addWidget(self._thumb_container)

    # ─── 公共接口 ─────────────────────────────────

    def set_top_widget(self, widget: QWidget):
        self._top_layout.addWidget(widget)

    def add_card(self, card: DashboardCard):
        """添加卡片。第一张自动进入 Hero，其余进入缩略栏。"""
        self._all_cards[card.card_id] = card
        if self._current_hero_id is None:
            self._set_to_hero(card.card_id)
        else:
            self._set_to_thumb(card.card_id)

    def set_hero_card(self, card: DashboardCard):
        """强制设置某张卡为当前 Hero（其他卡自动放入缩略栏）"""
        self._all_cards[card.card_id] = card
        if self._current_hero_id == card.card_id:
            return
        if self._current_hero_id:
            self._set_to_thumb(self._current_hero_id)
        self._set_to_hero(card.card_id)

    def add_thumbnail_card(self, card: DashboardCard):
        """直接添加到缩略栏"""
        self._all_cards[card.card_id] = card
        self._set_to_thumb(card.card_id)

    def get_cards(self) -> dict:
        return self._all_cards.copy()

    def get_card(self, card_id: str) -> DashboardCard:
        return self._all_cards.get(card_id)

    def get_current_hero_id(self) -> str:
        return self._current_hero_id

    def refresh_all(self, data: dict = None):
        for card in self._all_cards.values():
            card.refresh_data(data)

    # ─── 内部管理 ────────────────────────────────

    def _set_to_hero(self, card_id: str):
        """将卡片设置为当前 Hero（从缩略栏移除其按钮）"""
        card = self._all_cards.get(card_id)
        if card is None:
            return

        self._clear_layout(self._hero_layout)
        self._hero_layout.addWidget(card)
        card.show()

        self._current_hero_id = card_id
        self._remove_thumb_button(card_id)

    def _set_to_thumb(self, card_id: str):
        """从 Hero 区移除并为其创建缩略按钮"""
        card = self._all_cards.get(card_id)
        if card is None:
            return

        card.setParent(None)
        self._create_thumb_button(card_id)

    def _create_thumb_button(self, card_id: str):
        """为卡片创建一个缩略按钮"""
        card = self._all_cards.get(card_id)
        if card is None:
            return

        icon = getattr(card, '_icon', '📄')
        btn = QPushButton(f"  {icon}  {card.card_name}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(150, 44)
        is_current = (card_id == self._current_hero_id)
        btn.setCheckable(True)
        btn.setChecked(is_current)

        btn.setStyleSheet(f"""
            QPushButton {{
                background: {"#EFF6FF" if is_current else "#FFFFFF"};
                border: 1px solid {"#3B82F6" if is_current else "#E2E8F0"};
                border-radius: 8px;
                font-size: 12px;
                font-weight: {700 if is_current else 500};
                color: {"#1E3A5F" if is_current else "#475569"};
                padding: 0 8px;
            }}
            QPushButton:hover {{
                background: #F1F5F9;
                border-color: #3B82F6;
            }}
            QPushButton:checked {{
                background: #EFF6FF;
                border-color: #3B82F6;
                font-weight: 700;
                color: #1E3A5F;
            }}
        """)
        btn.clicked.connect(lambda: self._on_thumb_clicked(card_id))

        self._thumb_buttons[card_id] = btn
        idx = self._thumb_layout.count() - 1
        self._thumb_layout.insertWidget(idx, btn)

    def _remove_thumb_button(self, card_id: str):
        btn = self._thumb_buttons.pop(card_id, None)
        if btn:
            self._thumb_layout.removeWidget(btn)
            btn.deleteLater()

    def _on_thumb_clicked(self, card_id: str):
        """点击缩略按钮 → 交换到 Hero"""
        if card_id == self._current_hero_id:
            return

        old_id = self._current_hero_id
        if old_id:
            # 旧 Hero → 缩略按钮
            old_card = self._all_cards.get(old_id)
            if old_card:
                old_card.setParent(None)

        # 新卡片 → Hero
        card = self._all_cards.get(card_id)
        if card is None:
            return

        self._clear_layout(self._hero_layout)
        self._hero_layout.addWidget(card)
        card.show()
        self._current_hero_id = card_id

        self._remove_thumb_button(card_id)
        if old_id:
            self._create_thumb_button(old_id)

        # 刷新按钮选中态
        self._update_thumb_states()

    def _update_thumb_states(self):
        for cid, btn in self._thumb_buttons.items():
            is_current = (cid == self._current_hero_id)
            btn.blockSignals(True)
            btn.setChecked(is_current)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {"#EFF6FF" if is_current else "#FFFFFF"};
                    border: 1px solid {"#3B82F6" if is_current else "#E2E8F0"};
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: {700 if is_current else 500};
                    color: {"#1E3A5F" if is_current else "#475569"};
                    padding: 0 8px;
                }}
                QPushButton:hover {{
                    background: #F1F5F9;
                    border-color: #3B82F6;
                }}
                QPushButton:checked {{
                    background: #EFF6FF;
                    border-color: #3B82F6;
                    font-weight: 700;
                    color: #1E3A5F;
                }}
            """)
            btn.blockSignals(False)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
