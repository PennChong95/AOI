from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QWidget, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal


class DashboardSettingsDialog(QDialog):
    """看板设置弹窗：布局预设 + 自动刷新"""

    layout_applied = pyqtSignal(str)
    save_requested = pyqtSignal()
    load_requested = pyqtSignal()
    refresh_interval_changed = pyqtSignal(int)  # 秒，0=关闭

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("看板设置")
        self.setFixedSize(420, 520)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # ─── 布局预设 ────────────────────────────
        layout_group = QGroupBox("布局预设")
        layout_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px; font-weight: 600; color: #1E293B;
                border: 1px solid #E2E8F0; border-radius: 8px;
                margin-top: 12px; padding: 16px 12px 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 12px;
                padding: 0 6px;
            }
        """)
        lg_layout = QVBoxLayout(layout_group)
        lg_layout.setSpacing(10)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        preset_row.addWidget(self._make_label("布局模式:"))
        self._preset_combo = QComboBox()
        self._preset_combo.addItems(["1×1", "1×2", "2×1", "2×2", "1×3", "3×1"])
        self._preset_combo.setCurrentText("1×2")
        self._preset_combo.setStyleSheet(self._combo_style())
        preset_row.addWidget(self._preset_combo)
        preset_row.addStretch()
        lg_layout.addLayout(preset_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_apply = QPushButton("应用")
        self._btn_apply.setStyleSheet(self._primary_btn_style())
        self._btn_apply.clicked.connect(self._on_apply_layout)
        btn_row.addWidget(self._btn_apply)

        self._btn_save = QPushButton("💾 保存")
        self._btn_save.setStyleSheet(self._secondary_btn_style())
        self._btn_save.clicked.connect(self.save_requested.emit)
        btn_row.addWidget(self._btn_save)

        self._btn_load = QPushButton("📂 恢复")
        self._btn_load.setStyleSheet(self._secondary_btn_style())
        self._btn_load.clicked.connect(self.load_requested.emit)
        btn_row.addWidget(self._btn_load)

        btn_row.addStretch()
        lg_layout.addLayout(btn_row)
        layout.addWidget(layout_group)

        # ─── 自动刷新 ────────────────────────────
        refresh_group = QGroupBox("自动刷新")
        refresh_group.setStyleSheet(layout_group.styleSheet())
        rf_layout = QHBoxLayout(refresh_group)
        rf_layout.setSpacing(8)

        rf_layout.addWidget(self._make_label("刷新间隔:"))
        self._refresh_combo = QComboBox()
        self._refresh_combo.addItems(["关闭", "30秒", "60秒", "120秒", "300秒"])
        self._refresh_combo.setCurrentIndex(0)
        self._refresh_combo.setStyleSheet(self._combo_style())
        self._refresh_combo.currentIndexChanged.connect(self._on_refresh_changed)
        rf_layout.addWidget(self._refresh_combo)
        rf_layout.addStretch()
        layout.addWidget(refresh_group)

        # ─── KPI 显示项 ───────────────────────────
        kpi_group = QGroupBox("KPI 显示项")
        kpi_group.setStyleSheet(layout_group.styleSheet())
        kpi_layout = QVBoxLayout(kpi_group)
        kpi_layout.setSpacing(4)

        self._kpi_checkboxes = {}
        kpi_options = [
            ("total", "总投入", True),
            ("ok", "OK数", True),
            ("ng", "NG数", True),
            ("yield_rate", "良率", True),
            ("review_ok", "复判OK", False),
            ("review_ng", "复判NG", False),
            ("post_review_yield_rate", "复判后良率", False),
        ]
        for i in range(0, len(kpi_options), 2):
            row = QHBoxLayout()
            row.setSpacing(12)
            for j in range(2):
                if i + j < len(kpi_options):
                    key, name, fixed = kpi_options[i + j]
                    cb = QCheckBox(name)
                    if fixed:
                        cb.setChecked(True)
                        cb.setEnabled(False)
                    else:
                        cb.setChecked(True)
                    cb.setStyleSheet("""
                        QCheckBox { font-size: 12px; color: #1E293B; padding: 2px 0; }
                        QCheckBox::indicator { width: 16px; height: 16px; }
                    """)
                    self._kpi_checkboxes[key] = cb
                    row.addWidget(cb)
                else:
                    row.addStretch()
            kpi_layout.addLayout(row)

        layout.addWidget(kpi_group)

        # ─── 底部按钮 ────────────────────────────
        layout.addStretch()
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self._btn_close = QPushButton("关闭")
        self._btn_close.setStyleSheet("""
            QPushButton {
                padding: 8px 24px; border-radius: 6px;
                font-size: 12px; font-weight: 600;
                border: 1px solid #E2E8F0; color: #475569;
                background: #FFFFFF;
            }
            QPushButton:hover { border-color: #3B82F6; color: #3B82F6; }
        """)
        self._btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(self._btn_close)
        layout.addLayout(bottom_row)

    # ─── 公共接口 ─────────────────────────────────

    def set_current_preset(self, preset: str):
        """设置当前布局预设显示"""
        mapping = {"1x1": "1×1", "1x2": "1×2", "2x1": "2×1",
                   "2x2": "2×2", "1x3": "1×3", "3x1": "3×1"}
        text = mapping.get(preset, "1×2")
        idx = self._preset_combo.findText(text)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)

    def get_selected_kpi_items(self) -> list:
        fixed = ["total", "ok", "ng", "yield_rate"]
        optional = [key for key, cb in self._kpi_checkboxes.items()
                    if cb.isChecked() and key not in fixed]
        return fixed + optional

    def set_kpi_items(self, items: list):
        for key, cb in self._kpi_checkboxes.items():
            if cb.isEnabled():
                cb.setChecked(key in items)

    def get_refresh_interval(self) -> int:
        """获取当前刷新间隔（秒）"""
        mapping = {"关闭": 0, "30秒": 30, "60秒": 60, "120秒": 120, "300秒": 300}
        return mapping.get(self._refresh_combo.currentText(), 0)

    def set_refresh_interval(self, seconds: int):
        """设置刷新间隔显示"""
        rev = {0: "关闭", 30: "30秒", 60: "60秒", 120: "120秒", 300: "300秒"}
        text = rev.get(seconds, "关闭")
        idx = self._refresh_combo.findText(text)
        if idx >= 0:
            self._refresh_combo.setCurrentIndex(idx)

    # ─── 内部 ─────────────────────────────────────

    def _on_apply_layout(self):
        mapping = {"1×1": "1x1", "1×2": "1x2", "2×1": "2x1",
                   "2×2": "2x2", "1×3": "1x3", "3×1": "3x1"}
        preset = mapping.get(self._preset_combo.currentText(), "1x2")
        self.layout_applied.emit(preset)

    def _on_refresh_changed(self, idx):
        interval = self.get_refresh_interval()
        self.refresh_interval_changed.emit(interval)

    def _make_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 12px; color: #475569; border: none;")
        return lbl

    def _combo_style(self):
        return """
            QComboBox {
                padding: 6px 10px; border: 1px solid #E2E8F0;
                border-radius: 6px; font-size: 12px; min-width: 100px;
                background: #FFFFFF;
            }
            QComboBox:focus { border-color: #3B82F6; }
            QComboBox::drop-down { border: none; width: 20px; }
        """

    def _primary_btn_style(self):
        return """
            QPushButton {
                padding: 6px 16px; border-radius: 6px;
                font-size: 12px; font-weight: 600;
                background: #3B82F6; color: #FFFFFF; border: none;
            }
            QPushButton:hover { background: #2563EB; }
        """

    def _secondary_btn_style(self):
        return """
            QPushButton {
                padding: 6px 14px; border-radius: 6px;
                font-size: 11px; font-weight: 600;
                border: 1px solid #E2E8F0; color: #475569;
                background: #FFFFFF;
            }
            QPushButton:hover { border-color: #3B82F6; color: #3B82F6; }
        """
