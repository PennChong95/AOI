"""
AOI质量分析看板 - 主窗口
单页面布局，无侧边栏
"""

from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeyEvent
from database.manager import DBManager
from ui.theme import Theme, get_dashboard_style, get_primary_button_style
from services.dashboard_service import DashboardService
from dashboard.pages.home_page import HomePage
from dashboard.dialogs.export_dialog import ExportReportDialog
from dashboard.dialogs.settings_dialog import DashboardSettingsDialog
from utils.config_manager import ConfigManager


class TopBar(QWidget):
    """顶部工具栏"""
    
    refresh_clicked = pyqtSignal()
    export_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            QWidget {{
                background: {Theme.get_color('bg_card')};
                border-bottom: 1px solid {Theme.get_color('border')};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)
        
        # 标题区域
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        self._title = QLabel("AOI质量分析看板")
        self._title.setStyleSheet(f"""
            QLabel {{
                font-size: {Theme.get_font_size('xl')}px;
                font-weight: {Theme.FONT_WEIGHTS['bold']};
                color: {Theme.get_color('text_primary')};
                background: transparent;
            }}
        """)
        title_layout.addWidget(self._title)
        
        self._subtitle = QLabel("Quality Analysis Dashboard")
        self._subtitle.setStyleSheet(f"""
            QLabel {{
                font-size: {Theme.get_font_size('xs')}px;
                color: {Theme.get_color('text_muted')};
                background: transparent;
            }}
        """)
        title_layout.addWidget(self._subtitle)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # 刷新时间
        self._refresh_label = QLabel()
        self._refresh_label.setStyleSheet(f"""
            QLabel {{
                font-size: {Theme.get_font_size('sm')}px;
                color: {Theme.get_color('text_muted')};
                background: transparent;
            }}
        """)
        layout.addWidget(self._refresh_label)
        
        # 设置按钮
        self._btn_settings = QPushButton("⚙ 设置")
        self._btn_settings.setCursor(Qt.PointingHandCursor)
        self._btn_settings.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.get_color('bg_secondary')};
                color: {Theme.get_color('text_secondary')};
                padding: 8px 14px;
                border-radius: {Theme.get_radius('md')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                font-size: {Theme.get_font_size('sm')}px;
                border: 1px solid {Theme.get_color('border')};
            }}
            QPushButton:hover {{
                background: {Theme.get_color('border')};
                border-color: {Theme.get_color('primary_light')};
                color: {Theme.get_color('primary')};
            }}
        """)
        self._btn_settings.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self._btn_settings)
        
        # 导出报表按钮
        self._btn_export = QPushButton("📋 导出报表")
        self._btn_export.setCursor(Qt.PointingHandCursor)
        self._btn_export.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.get_color('bg_secondary')};
                color: {Theme.get_color('text_secondary')};
                padding: 8px 16px;
                border-radius: {Theme.get_radius('md')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                font-size: {Theme.get_font_size('sm')}px;
                border: 1px solid {Theme.get_color('border')};
            }}
            QPushButton:hover {{
                background: {Theme.get_color('border')};
                border-color: {Theme.get_color('primary_light')};
                color: {Theme.get_color('primary')};
            }}
        """)
        self._btn_export.clicked.connect(self.export_clicked.emit)
        layout.addWidget(self._btn_export)
        
        # 刷新按钮
        self._btn_refresh = QPushButton("🔄 刷新")
        self._btn_refresh.setCursor(Qt.PointingHandCursor)
        self._btn_refresh.setStyleSheet(get_primary_button_style())
        self._btn_refresh.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self._btn_refresh)
    
    def update_refresh_time(self):
        """更新刷新时间"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._refresh_label.setText(f"⏰ 更新: {now}")


class DashboardWindow(QDialog):
    """AOI质量分析看板主窗口（单页面布局）"""
    
    def __init__(self, db_manager: DBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self._service = DashboardService(db_manager)
        config = ConfigManager.load()
        self._refresh_interval = self._normalize_refresh_interval(
            int(config.get("dashboard_refresh_interval", 0) or 0)
        )
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._on_auto_refresh)
        
        self.setWindowTitle("AOI质量分析看板")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        self.setWindowFlags(
            self.windowFlags() | 
            Qt.WindowMinimizeButtonHint | 
            Qt.WindowMaximizeButtonHint
        )
        
        self.setStyleSheet(get_dashboard_style())
        self._setup_ui()
        self._connect_signals()
        
        if self._refresh_interval > 0:
            self._auto_timer.start(self._refresh_interval * 1000)
        QTimer.singleShot(100, self.refresh)
    
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        self._top_bar = TopBar()
        root.addWidget(self._top_bar)
        
        self._home_page = HomePage(self._service, self.db_manager)
        root.addWidget(self._home_page, 1)
    
    def _connect_signals(self):
        self._top_bar.refresh_clicked.connect(self.force_refresh)
        self._top_bar.export_clicked.connect(self._show_export_dialog)
        self._top_bar.settings_clicked.connect(self._show_settings_dialog)
    
    def refresh(self):
        self._home_page.refresh()
        self._top_bar.update_refresh_time()

    def force_refresh(self):
        self._service.invalidate_cache()
        self.refresh()

    def _on_auto_refresh(self):
        if not self.isVisible() or self.isMinimized():
            return
        self.refresh()
    
    def _show_export_dialog(self):
        dialog = ExportReportDialog(self._service, self)
        dialog.exec_()
    
    def _show_settings_dialog(self):
        dashboard_view = self._home_page._dashboard_view
        config = ConfigManager.load()
        dialog = DashboardSettingsDialog(self)
        dialog.set_current_preset(dashboard_view.get_current_preset())
        dialog.set_refresh_interval(self._refresh_interval)
        dialog.set_kpi_items(config.get("dashboard_kpi_items", []))
        
        dialog.layout_applied.connect(dashboard_view.apply_layout_preset)
        dialog.save_requested.connect(dashboard_view.save_layout)
        dialog.load_requested.connect(dashboard_view.load_layout)
        dialog.refresh_interval_changed.connect(self._on_refresh_interval_changed)
        
        if dialog.exec_() == QDialog.Accepted:
            new_items = dialog.get_selected_kpi_items()
            config = ConfigManager.load()
            config["dashboard_kpi_items"] = new_items
            config["dashboard_refresh_interval"] = self._refresh_interval
            ConfigManager.save(config)
            self._home_page.set_kpi_items(new_items)
            self.refresh()
    
    def _on_refresh_interval_changed(self, seconds: int):
        seconds = self._normalize_refresh_interval(seconds)
        self._refresh_interval = seconds
        if seconds > 0:
            self._auto_timer.start(seconds * 1000)
        else:
            self._auto_timer.stop()

    @staticmethod
    def _normalize_refresh_interval(seconds: int) -> int:
        if seconds <= 0:
            return 0
        return max(300, seconds)
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_F5:
            self.force_refresh()
            event.accept()
            return
        elif event.key() == Qt.Key_Escape:
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)
