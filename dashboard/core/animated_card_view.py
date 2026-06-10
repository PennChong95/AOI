from PyQt5.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt5.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QPoint


class AnimatedCardView(QWidget):
    """带动画切换效果的单卡视图"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = None
        self._animating = False
        self.setMinimumSize(200, 120)
        self.setStyleSheet("background: transparent; border: none;")

    def set_card(self, card, animate=True, direction=1):
        """
        设置当前显示的卡片
        direction: 1=new从右进(←), -1=new从左进(→)
        """
        if card is self._current and card is not None:
            return
        if self._animating:
            return

        old = self._current
        self._current = card
        w, h = self.width(), self.height()

        if old is None or not animate:
            if old:
                old.setParent(None)
            if card:
                card.setParent(self)
                card.resize(w, h)
                card.move(0, 0)
                card.show()
            return

        self._animating = True

        # 旧卡：放在当前位置
        old.setParent(self)
        old.resize(w, h)
        old.move(0, 0)

        # 新卡：从侧边滑入
        card.setParent(self)
        card.resize(w, h)
        offset = w if direction == 1 else -w
        card.move(offset, 0)
        card.show()
        card.raise_()

        # 透明度效果（对部分原生控件可能无效，回退到纯滑动）
        try:
            old_effect = QGraphicsOpacityEffect()
            old.setGraphicsEffect(old_effect)
            new_effect = QGraphicsOpacityEffect()
            card.setGraphicsEffect(new_effect)
            use_opacity = True
        except Exception:
            use_opacity = False

        group = QParallelAnimationGroup()

        old_pos = QPropertyAnimation(old, b"pos")
        old_pos.setDuration(300)
        old_pos.setStartValue(QPoint(0, 0))
        old_pos.setEndValue(QPoint(-offset * 3 // 10, 0))
        old_pos.setEasingCurve(QEasingCurve.InOutCubic)
        group.addAnimation(old_pos)

        new_pos = QPropertyAnimation(card, b"pos")
        new_pos.setDuration(300)
        new_pos.setStartValue(QPoint(offset, 0))
        new_pos.setEndValue(QPoint(0, 0))
        new_pos.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(new_pos)

        if use_opacity:
            old_op = QPropertyAnimation(old_effect, b"opacity")
            old_op.setDuration(300)
            old_op.setStartValue(1.0)
            old_op.setEndValue(0.0)
            group.addAnimation(old_op)

            new_op = QPropertyAnimation(new_effect, b"opacity")
            new_op.setDuration(300)
            new_op.setStartValue(0.0)
            new_op.setEndValue(1.0)
            group.addAnimation(new_op)

        def on_finish():
            old.setGraphicsEffect(None)
            card.setGraphicsEffect(None)
            old.hide()
            old.setParent(None)
            self._animating = False

        group.finished.connect(on_finish)
        group.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        if self._current and not self._animating:
            self._current.resize(w, h)
            self._current.move(0, 0)
