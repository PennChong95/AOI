from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal


class LayoutToolbar(QWidget):
    """布局工具栏：预设按钮 + 保存 / 恢复"""

    preset_applied = pyqtSignal(str)
    save_requested = pyqtSignal()
    load_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet("background: transparent; border: none;")

        btn_style = """
            QPushButton {
                background: #FFFFFF; border: 1px solid #E2E8F0;
                border-radius: 6px; padding: 4px 10px;
                font-size: 11px; font-weight: 600; color: #475569;
            }
            QPushButton:hover { border-color: #3B82F6; color: #3B82F6; }
            QPushButton:pressed { background: #F1F5F9; }
        """

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setSpacing(6)

        label_style = "font-size: 11px; font-weight: 600; color: #64748B; border: none;"

        lbl = self._make_label("布局:", label_style)
        layout.addWidget(lbl)

        presets = [("1×1", "1x1"), ("1×2", "1x2"), ("2×1", "2x1"),
                   ("2×2", "2x2"), ("1×3", "1x3"), ("3×1", "3x1")]
        for text, pval in presets:
            btn = QPushButton(text)
            btn.setStyleSheet(btn_style)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, val=pval: self.preset_applied.emit(val))
            layout.addWidget(btn)

        layout.addStretch()

        save_btn = QPushButton("💾 保存")
        save_btn.setStyleSheet(btn_style)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self.save_requested.emit)
        layout.addWidget(save_btn)

        load_btn = QPushButton("📂 恢复")
        load_btn.setStyleSheet(btn_style)
        load_btn.setCursor(Qt.PointingHandCursor)
        load_btn.clicked.connect(self.load_requested.emit)
        layout.addWidget(load_btn)

    def _make_label(self, text, style):
        from PyQt5.QtWidgets import QLabel
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl
