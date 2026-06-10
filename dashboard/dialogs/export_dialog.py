"""
导出报表弹窗
提供数据导出和报表预览功能
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from services.dashboard_service import DashboardService
from ui.theme import Theme, get_primary_button_style
from utils.exporter import export_to_excel


class ExportReportDialog(QDialog):
    """导出报表弹窗"""
    
    def __init__(self, service: DashboardService, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("导出报表")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self._setup_ui()
        self._preview_data()
    
    def _setup_ui(self):
        """设置UI"""
        self.setStyleSheet(f"""
            QDialog {{
                background: {Theme.get_color('bg_primary')};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # 标题
        title_layout = QHBoxLayout()
        title_layout.setSpacing(12)
        
        title_icon = QLabel("📋")
        title_icon.setStyleSheet(f"""
            QLabel {{
                background: {Theme.get_color('primary_lighter')};
                border-radius: 16px;
                padding: 8px;
                font-size: 20px;
            }}
        """)
        title_layout.addWidget(title_icon)
        
        title_label = QLabel("导出报表")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_primary')};
                font-size: {Theme.get_font_size('xl')}px;
                font-weight: {Theme.FONT_WEIGHTS['bold']};
                background: transparent;
            }}
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # 配置区域
        config_frame = QFrame()
        config_frame.setStyleSheet(f"""
            QFrame {{
                background: {Theme.get_color('bg_card')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: {Theme.get_radius('lg')}px;
                padding: 16px;
            }}
        """)
        
        config_layout = QVBoxLayout(config_frame)
        config_layout.setSpacing(12)
        
        # 报表类型选择
        type_row = QHBoxLayout()
        type_row.setSpacing(12)
        
        type_label = QLabel("报表类型:")
        type_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_primary')};
                font-size: {Theme.get_font_size('md')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                min-width: 80px;
            }}
        """)
        type_row.addWidget(type_label)
        
        self._report_type = QComboBox()
        self._report_type.addItems(["良率报表", "缺陷报表", "工站报表"])
        self._report_type.setStyleSheet(self._get_combo_style())
        self._report_type.currentIndexChanged.connect(self._preview_data)
        type_row.addWidget(self._report_type)
        type_row.addStretch()
        
        config_layout.addLayout(type_row)
        
        # 时间范围选择
        days_row = QHBoxLayout()
        days_row.setSpacing(12)
        
        days_label = QLabel("时间范围:")
        days_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_primary')};
                font-size: {Theme.get_font_size('md')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                min-width: 80px;
            }}
        """)
        days_row.addWidget(days_label)
        
        self._days_combo = QComboBox()
        self._days_combo.addItems(["今天", "近7天", "近30天"])
        self._days_combo.setStyleSheet(self._get_combo_style())
        self._days_combo.currentIndexChanged.connect(self._preview_data)
        days_row.addWidget(self._days_combo)
        days_row.addStretch()
        
        config_layout.addLayout(days_row)
        
        layout.addWidget(config_frame)
        
        # 预览区域
        preview_section = QWidget()
        preview_layout = QVBoxLayout(preview_section)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(8)
        
        preview_title = QLabel("数据预览")
        preview_title.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_primary')};
                font-size: {Theme.get_font_size('lg')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
            }}
        """)
        preview_layout.addWidget(preview_title)
        
        self._preview = QTableWidget()
        self._preview.setEditTriggers(QTableWidget.NoEditTriggers)
        self._preview.setAlternatingRowColors(True)
        self._preview.setSelectionBehavior(QTableWidget.SelectRows)
        self._preview.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._preview.setStyleSheet(f"""
            QTableWidget {{
                background: {Theme.get_color('bg_card')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: {Theme.get_radius('lg')}px;
                gridline-color: {Theme.get_color('border_light')};
                alternate-background-color: {Theme.get_color('bg_primary')};
                selection-background-color: {Theme.get_color('primary_lighter')};
                selection-color: {Theme.get_color('text_primary')};
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {Theme.get_color('border_light')};
            }}
            QHeaderView::section {{
                background: {Theme.get_color('bg_secondary')};
                color: {Theme.get_color('text_secondary')};
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                font-size: {Theme.get_font_size('sm')}px;
                border: none;
                border-bottom: 2px solid {Theme.get_color('border')};
                padding: 10px;
            }}
        """)
        
        preview_layout.addWidget(self._preview, 1)
        layout.addWidget(preview_section, 1)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("取消")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.get_color('bg_secondary')};
                color: {Theme.get_color('text_secondary')};
                padding: 10px 24px;
                border-radius: {Theme.get_radius('md')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                font-size: {Theme.get_font_size('md')}px;
                border: 1px solid {Theme.get_color('border')};
                min-width: 80px;
            }}
            QPushButton:hover {{
                background: {Theme.get_color('border')};
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_export = QPushButton("📥 导出报表")
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.setStyleSheet(get_primary_button_style())
        btn_export.clicked.connect(self._export)
        btn_layout.addWidget(btn_export)
        
        layout.addLayout(btn_layout)
    
    def _get_combo_style(self):
        """获取下拉框样式"""
        return f"""
            QComboBox {{
                padding: 8px 12px;
                border: 1px solid {Theme.get_color('border')};
                border-radius: {Theme.get_radius('md')}px;
                background: {Theme.get_color('bg_card')};
                color: {Theme.get_color('text_primary')};
                font-size: {Theme.get_font_size('md')}px;
                min-width: 150px;
            }}
            QComboBox:focus {{
                border-color: {Theme.get_color('primary')};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background: {Theme.get_color('bg_card')};
                color: {Theme.get_color('text_primary')};
                selection-background-color: {Theme.get_color('primary_lighter')};
                selection-color: {Theme.get_color('primary')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: {Theme.get_radius('md')}px;
                outline: none;
                padding: 4px;
            }}
        """
    
    def _get_days(self):
        """获取选中的天数"""
        return [0, 7, 30][self._days_combo.currentIndex()]
    
    def _preview_data(self):
        """预览数据"""
        try:
            days = self._get_days()
            rtype = self._report_type.currentText()
            
            if rtype == "良率报表":
                data = self.service.yield_trend(days, "day")
                if not data:
                    return
                self._preview.setColumnCount(5)
                self._preview.setHorizontalHeaderLabels(["日期", "检测数", "OK数", "NG数", "良率"])
                self._preview.setRowCount(len(data))
                for i, d in enumerate(data):
                    self._preview.setItem(i, 0, QTableWidgetItem(d["period"]))
                    self._preview.setItem(i, 1, QTableWidgetItem(f"{d['total']:,}"))
                    self._preview.setItem(i, 2, QTableWidgetItem(f"{d['ok']:,}"))
                    self._preview.setItem(i, 3, QTableWidgetItem(f"{d['ng']:,}"))
                    
                    rate_item = QTableWidgetItem(f"{d['yield_rate']:.1f}%")
                    rate_item.setTextAlignment(Qt.AlignCenter)
                    if d['yield_rate'] >= 95:
                        rate_item.setForeground(QColor(Theme.get_color("success")))
                    elif d['yield_rate'] >= 90:
                        rate_item.setForeground(QColor(Theme.get_color("warning")))
                    else:
                        rate_item.setForeground(QColor(Theme.get_color("danger")))
                    self._preview.setItem(i, 4, rate_item)
                    
            elif rtype == "缺陷报表":
                data = self.service.top_defects(days, 20)
                if not data:
                    return
                self._preview.setColumnCount(3)
                self._preview.setHorizontalHeaderLabels(["缺陷名称", "数量", "占比"])
                self._preview.setRowCount(len(data))
                for i, d in enumerate(data):
                    self._preview.setItem(i, 0, QTableWidgetItem(d["name"]))
                    self._preview.setItem(i, 1, QTableWidgetItem(f"{d['count']:,}"))
                    self._preview.setItem(i, 2, QTableWidgetItem(f"{d['pct']:.1f}%"))
                    
            elif rtype == "工站报表":
                data = self.service.station_ng_rates(days)
                if not data:
                    return
                self._preview.setColumnCount(4)
                self._preview.setHorizontalHeaderLabels(["工站名称", "检测数", "NG数", "NG率"])
                self._preview.setRowCount(len(data))
                for i, d in enumerate(data):
                    self._preview.setItem(i, 0, QTableWidgetItem(d["name"]))
                    self._preview.setItem(i, 1, QTableWidgetItem(f"{d['total']:,}"))
                    self._preview.setItem(i, 2, QTableWidgetItem(f"{d['ng']:,}"))
                    
                    rate_item = QTableWidgetItem(f"{d['ng_rate']:.1f}%")
                    rate_item.setTextAlignment(Qt.AlignCenter)
                    if d['ng_rate'] <= 5:
                        rate_item.setForeground(QColor(Theme.get_color("success")))
                    elif d['ng_rate'] <= 10:
                        rate_item.setForeground(QColor(Theme.get_color("warning")))
                    else:
                        rate_item.setForeground(QColor(Theme.get_color("danger")))
                    self._preview.setItem(i, 3, rate_item)
            
        except Exception as e:
            print(f"预览数据失败: {e}")
    
    def _export(self):
        """导出报表"""
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, "导出报表", 
                f"{self._report_type.currentText()}.xlsx",
                "Excel文件 (*.xlsx);;CSV文件 (*.csv);;所有文件 (*)"
            )
            
            if not path:
                return
            
            days = self._get_days()
            rtype = self._report_type.currentText()
            
            headers = []
            rows = []
            
            if rtype == "良率报表":
                data = self.service.yield_trend(days, "day")
                headers = ["日期", "检测数", "OK数", "NG数", "良率"]
                rows = [[d["period"], d["total"], d["ok"], d["ng"], f"{d['yield_rate']:.1f}%"] for d in data]
                
            elif rtype == "缺陷报表":
                data = self.service.top_defects(days, 20)
                headers = ["缺陷名称", "数量", "占比"]
                rows = [[d["name"], d["count"], f"{d['pct']:.1f}%"] for d in data]
                
            elif rtype == "工站报表":
                data = self.service.station_ng_rates(days)
                headers = ["工站名称", "检测数", "NG数", "NG率"]
                rows = [[d["name"], d["total"], d["ng"], f"{d['ng_rate']:.1f}%"] for d in data]
            
            export_to_excel(path, headers, rows)
            QMessageBox.information(
                self, "导出成功", 
                f"报表已成功导出至:\n{path}",
                QMessageBox.Ok
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, "导出失败", 
                f"导出报表时发生错误:\n{str(e)}",
                QMessageBox.Ok
            )
