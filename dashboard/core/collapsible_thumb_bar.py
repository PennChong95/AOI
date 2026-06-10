from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from dashboard.core.thumbnail_bar import ThumbnailBar


class CollapsibleThumbBar(QWidget):
    """可折叠缩略卡栏，带动画展开/收起"""

    card_clicked = pyqtSignal(str)

    THUMB_HEIGHT = 120
    ANIM_DURATION = 300
    BTN_HEIGHT = 30

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._animating = False
        self._anim = None
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 缩略卡栏容器（动画控制其 maximumHeight）
        self._thumb_wrapper = QWidget()
        self._thumb_wrapper.setStyleSheet("background: transparent; border: none;")
        self._thumb_wrapper.setMinimumHeight(0)
        self._thumb_wrapper.setMaximumHeight(0)

        wrapper_layout = QVBoxLayout(self._thumb_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)

        self._thumb_bar = ThumbnailBar()
        self._thumb_bar.card_clicked.connect(self._on_card_clicked)
        wrapper_layout.addWidget(self._thumb_bar)

        layout.addWidget(self._thumb_wrapper)

        # 展开/收起按钮（居中）
        btn_container = QHBoxLayout()
        btn_container.setContentsMargins(0, 0, 0, 0)

        self._toggle_btn = QPushButton("▲ 展开")
        self._toggle_btn.setFixedSize(120, self.BTN_HEIGHT)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: #FFFFFF; border: 1px solid #E2E8F0;
                border-radius: 14px; font-size: 11px; font-weight: 600;
                color: #475569;
            }
            QPushButton:hover {
                background: #F1F5F9; border-color: #3B82F6;
                color: #3B82F6;
            }
            QPushButton:disabled {
                color: #CBD5E1; background: #F8FAFC;
            }
        """)
        self._toggle_btn.clicked.connect(self.toggle)

        btn_container.addStretch()
        btn_container.addWidget(self._toggle_btn)
        btn_container.addStretch()
        layout.addLayout(btn_container)

        # 默认本控件不占用布局空间（由父窗口手动 setGeometry）
        self.setVisible(False)

    # ─── 公开方法 ─────────────────────────────────

    def toggle(self):
        if self._animating:
            return
        self._animating = True
        self._toggle_btn.setEnabled(False)

        if self._expanded:
            self._animate_collapse()
        else:
            self._animate_expand()

    def set_expanded(self, expanded: bool, animate: bool = False):
        if expanded == self._expanded:
            return
        if animate:
            self.toggle()
        else:
            self._expanded = expanded
            if expanded:
                self._thumb_wrapper.setMaximumHeight(self.THUMB_HEIGHT)
                self._thumb_wrapper.setVisible(True)
            else:
                self._thumb_wrapper.setMaximumHeight(0)
            self._toggle_btn.setText("▼ 收起" if expanded else "▲ 展开")

    def is_expanded(self) -> bool:
        return self._expanded

    def is_animating(self) -> bool:
        return self._animating

    def update_floating_geometry(self, parent_width: int, parent_height: int, margin: int = 0):
        """根据父窗口尺寸计算浮动位置"""
        if self._animating and self._anim is not None:
            return  # 动画期间不干预
        thumb_h = self.THUMB_HEIGHT if self._expanded else 0
        total_h = thumb_h + self.BTN_HEIGHT
        x = margin
        w = parent_width - 2 * margin
        y = parent_height - total_h - 4
        self.setGeometry(QRect(x, y, w, total_h))

    def get_thumb_global_rect(self) -> QRect:
        """返回缩略卡栏的全局坐标矩形（供事件过滤器用）"""
        return QRect(
            self.mapToGlobal(self._thumb_wrapper.pos()),
            self._thumb_wrapper.size()
        )

    def get_toggle_global_rect(self) -> QRect:
        """返回切换按钮的全局坐标矩形"""
        return QRect(
            self.mapToGlobal(self._toggle_btn.pos()),
            self._toggle_btn.size()
        )

    # ─── 代理方法 ──────────────────────────────────

    def add_card(self, card_id: str, card_name: str, icon: str = "📄"):
        return self._thumb_bar.add_card(card_id, card_name, icon)

    def remove_card(self, card_id: str):
        self._thumb_bar.remove_card(card_id)

    def set_selected(self, card_id: str):
        self._thumb_bar.set_selected(card_id)

    def get_thumb(self, card_id: str):
        return self._thumb_bar.get_thumb(card_id)

    def get_inner_bar(self) -> ThumbnailBar:
        return self._thumb_bar

    # ─── 事件 ──────────────────────────────────────

    def _on_card_clicked(self, card_id: str):
        self.card_clicked.emit(card_id)

    # ─── 动画 ──────────────────────────────────────

    def _animate_expand(self):
        self.show()
        self.raise_()
        self._thumb_wrapper.setMaximumHeight(self.THUMB_HEIGHT)
        self._thumb_wrapper.setVisible(True)

        parent = self.parentWidget()
        if not parent:
            self._on_expand_finished()
            return

        pw, ph = parent.width(), parent.height()
        start_h = self.BTN_HEIGHT
        end_h = self.THUMB_HEIGHT + self.BTN_HEIGHT
        start_rect = QRect(0, ph - start_h - 4, pw, start_h)
        end_rect = QRect(0, ph - end_h - 4, pw, end_h)
        self.setGeometry(start_rect)

        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(self.ANIM_DURATION)
        self._anim.setStartValue(start_rect)
        self._anim.setEndValue(end_rect)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_expand_finished)
        self._anim.start()

    def _on_expand_finished(self):
        self._expanded = True
        self._animating = False
        self._toggle_btn.setEnabled(True)
        self._toggle_btn.setText("▼ 收起")

    def _animate_collapse(self):
        parent = self.parentWidget()
        if not parent:
            self._on_collapse_finished()
            return

        pw, ph = parent.width(), parent.height()
        start_h = self.THUMB_HEIGHT + self.BTN_HEIGHT
        end_h = self.BTN_HEIGHT
        start_rect = QRect(0, ph - start_h - 4, pw, start_h)
        end_rect = QRect(0, ph - end_h - 4, pw, end_h)
        self.setGeometry(start_rect)

        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(self.ANIM_DURATION)
        self._anim.setStartValue(start_rect)
        self._anim.setEndValue(end_rect)
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.finished.connect(self._on_collapse_finished)
        self._anim.start()

    def _on_collapse_finished(self):
        self._expanded = False
        self._animating = False
        self._toggle_btn.setEnabled(True)
        self._toggle_btn.setText("▲ 展开")
        self._thumb_wrapper.setMaximumHeight(0)
