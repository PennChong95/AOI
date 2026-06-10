import json, os
from typing import Dict, Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QApplication, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QRect, QEvent, QObject, QTimer
from PyQt5.QtGui import QColor, QKeyEvent
from dashboard.core.slot_manager import SlotManager, DashboardSlot
from dashboard.core.workspace import DashboardWorkspace
from dashboard.core.collapsible_thumb_bar import CollapsibleThumbBar
from dashboard.core.dashboard_card import DashboardCard

LAYOUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "config", "dashboard_layout.json")


class _RestoreFilter(QObject):
    """最大化时专用的事件过滤器：双击还原卡片"""

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self._view = view

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonDblClick:
            self._view._restore_card()
            return True
        return False


class DashboardView(QWidget):
    """卡片工作区主视图：工作区 + 缩略卡栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: Dict[str, DashboardCard] = {}
        self._current_preset = "1x2"
        self._maximized = False
        self._max_card_id = None
        self._max_slot_id = None

        self.slot_manager = SlotManager()
        self.workspace = DashboardWorkspace(self.slot_manager)
        self.thumbnail_bar = CollapsibleThumbBar(self)
        self._restore_filter = _RestoreFilter(self)

        # 悬浮阴影
        thumb_shadow = QGraphicsDropShadowEffect()
        thumb_shadow.setBlurRadius(15)
        thumb_shadow.setXOffset(0)
        thumb_shadow.setYOffset(-3)
        thumb_shadow.setColor(QColor(0, 0, 0, 35))
        self.thumbnail_bar.setGraphicsEffect(thumb_shadow)

        self._max_container = QFrame()
        self._max_container.setStyleSheet("background: #F8FAFC; border: none;")
        self._max_container.setVisible(False)
        _max_layout = QVBoxLayout(self._max_container)
        _max_layout.setContentsMargins(16, 8, 16, 8)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 42)
        layout.setSpacing(6)
        layout.addWidget(self.workspace, 1)
        layout.addWidget(self._max_container, 1)

        # 缩略卡栏不加入布局，在 resizeEvent 中绝对定位悬浮

        self.thumbnail_bar.card_clicked.connect(self._on_thumbnail_clicked)
        self.workspace.card_dropped.connect(self._on_card_dropped)
        self.workspace.slot_maximize_requested.connect(self._on_slot_maximize)
        self.slot_manager.slot_activated.connect(self._on_slot_activated)

        # 全局事件过滤器（点击外部收起悬浮缩略栏）
        QApplication.instance().installEventFilter(self)

    # ─── 事件 / 悬浮定位 ──────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        if self._maximized:
            self.thumbnail_bar.hide()
            self.thumbnail_bar.setEnabled(False)
        else:
            self.thumbnail_bar.show()
            self.thumbnail_bar.setEnabled(True)
            self.thumbnail_bar.update_floating_geometry(w, h, 0)
            self.thumbnail_bar.raise_()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape and self.thumbnail_bar.is_expanded():
            self.thumbnail_bar.toggle()
            event.accept()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
                and self.thumbnail_bar.is_expanded()
                and not self.thumbnail_bar.is_animating()):
            global_pos = event.globalPos()
            if (not self.thumbnail_bar.get_thumb_global_rect().contains(global_pos)
                    and not self.thumbnail_bar.get_toggle_global_rect().contains(global_pos)):
                self.thumbnail_bar.toggle()
        return False

    # ─── 卡片管理 ─────────────────────────────────

    def add_card(self, card: DashboardCard):
        """注册卡片（自动添加到缩略栏 + 填充空闲槽位）"""
        self._cards[card.card_id] = card
        icon = getattr(card, '_icon', '📄')
        self.thumbnail_bar.add_card(card.card_id, card.card_name, icon)
        slot = self.slot_manager.get_empty_slot()
        if slot:
            self._fill_slot(slot.slot_id, card.card_id)

    def get_card(self, card_id: str) -> Optional[DashboardCard]:
        return self._cards.get(card_id)

    def get_all_cards(self) -> dict:
        return self._cards.copy()

    # ─── 填充逻辑 ────────────────────────────────

    def _fill_slot(self, slot_id: int, card_id: str):
        """将卡片填充到指定槽位"""
        if card_id not in self._cards:
            return
        old_slot = self.slot_manager.get_slot_by_card(card_id)
        if old_slot and old_slot.slot_id == slot_id:
            return  # 已在目标槽位，不重复填充
        if old_slot:
            self.workspace.set_slot_card(old_slot.slot_id, None)
            self.slot_manager.set_slot_card(old_slot.slot_id, None)
        card = self._cards[card_id]
        self.workspace.set_slot_card(slot_id, card)
        self.slot_manager.set_slot_card(slot_id, card_id)

    def _on_thumbnail_clicked(self, card_id: str):
        """点击缩略卡 → 填充到当前激活槽位 / 空闲槽位 / 替换第一个"""
        slot = self.slot_manager.get_activated_slot()
        if slot:
            self._fill_slot(slot.slot_id, card_id)
            return
        empty = self.slot_manager.get_empty_slot()
        if empty:
            self._fill_slot(empty.slot_id, card_id)
            self.slot_manager.activate_slot(empty.slot_id)
            return
        if self.slot_manager.slots:
            first = self.slot_manager.slots[0].slot_id
            self._fill_slot(first, card_id)
            self.slot_manager.activate_slot(first)

    def _on_card_dropped(self, slot_id: int, card_id: str):
        """拖拽卡片到槽位"""
        self._fill_slot(slot_id, card_id)
        self.slot_manager.activate_slot(slot_id)

    def _on_slot_activated(self, slot_id: int):
        """槽位被激活 → 高亮对应缩略卡"""
        slot = self.slot_manager.get_activated_slot()
        cid = slot.card_id if slot else None
        self.thumbnail_bar.set_selected(cid or "")

    def _on_slot_maximize(self, slot_id: int):
        """双击槽位 → 统一走卡片最大化/还原"""
        if self._maximized:
            self._restore_card()
            return
        for s in self.slot_manager.slots:
            if s.slot_id == slot_id and s.card_id:
                self._show_card_maximized(s.card_id)
                break

    # ─── 卡片最大化/还原 ──────────────────────────

    def _show_card_maximized(self, card_id: str):
        """从槽位取出卡片，放入全屏容器"""
        if self._maximized:
            return
        card = self._cards.get(card_id)
        if not card:
            return
        self._max_card_id = card_id
        slot = self.slot_manager.get_slot_by_card(card_id)
        self._max_slot_id = slot.slot_id if slot else None
        if slot:
            self.workspace.set_slot_card(slot.slot_id, None)
            self.slot_manager.set_slot_card(slot.slot_id, None)
        card.setParent(self._max_container)
        self._max_container.layout().addWidget(card)
        card.show()
        self.workspace.setVisible(False)
        self.thumbnail_bar.setVisible(False)
        self._max_container.setVisible(True)
        self._maximized = True
        QTimer.singleShot(0, lambda: QApplication.instance().installEventFilter(self._restore_filter))

    def _restore_card(self):
        """从全屏容器取出卡片，放回原槽位"""
        if not self._maximized:
            return
        self._maximized = False
        item = self._max_container.layout().takeAt(0)
        if not item:
            return
        card = item.widget()
        if not card:
            return
        if self._max_slot_id is not None:
            self.workspace.set_slot_card(self._max_slot_id, card)
            self.slot_manager.set_slot_card(self._max_slot_id, card.card_id)
        self.workspace.setVisible(True)
        self.thumbnail_bar.setVisible(True)
        self._max_container.setVisible(False)
        QApplication.instance().removeEventFilter(self._restore_filter)

    # ─── 公共方法 ────────────────────────────────

    def apply_layout_preset(self, preset: str):
        """切换布局预设 → 保存卡片顺序，重置布局，恢复卡片（公开接口）"""
        self._current_preset = preset
        card_order = []
        for slot in self.slot_manager.slots:
            if slot.card_id and slot.card_id in self._cards:
                card_order.append(slot.card_id)

        self.workspace.apply_layout_preset(preset)

        for slot in self.slot_manager.slots:
            if card_order:
                cid = card_order.pop(0)
                self._fill_slot(slot.slot_id, cid)

        self.thumbnail_bar.set_selected("")

    def get_current_preset(self) -> str:
        return self._current_preset

    def save_layout(self):
        """保存布局到文件"""
        config = self.slot_manager.save_layout()
        config["preset"] = self._current_preset
        os.makedirs(os.path.dirname(LAYOUT_FILE), exist_ok=True)
        with open(LAYOUT_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def load_layout(self):
        """从文件恢复布局"""
        if not os.path.exists(LAYOUT_FILE):
            return
        with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        preset = config.get("preset", "1x2")
        self.apply_layout_preset(preset)
        slot_cards = {}
        for sc in config.get("slots", []):
            if sc.get("card_id"):
                slot_cards[sc["slot_id"]] = sc["card_id"]
        for slot in self.slot_manager.slots:
            cid = slot_cards.pop(slot.slot_id, None)
            if cid:
                self._fill_slot(slot.slot_id, cid)
            elif slot_cards:
                cid = list(slot_cards.values())[0]
                del slot_cards[list(slot_cards.keys())[0]]
                self._fill_slot(slot.slot_id, cid)
        aid = config.get("activated_slot_id")
        if aid is not None:
            self.slot_manager.activate_slot(aid)
        self._on_slot_activated(aid)

