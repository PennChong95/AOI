"""
首页看板
整合所有功能：KPI、良率趋势、缺陷分布、最近记录
"""

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QWidget,
    QSizePolicy, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit, QScrollArea, QStackedWidget
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QColor
from ui.widgets.chart_widget import LineChart, PieChart, BarChart, ParetoChart
from ui.widgets.kpi_card import create_kpi_card, create_kpi_summary_panel, KPIStripPanel
from ui.theme import Theme
from utils.config_manager import ConfigManager
from services.dashboard_service import DashboardService, TIME_RANGE_GRANULARITY
from dashboard.core.dashboard_card import DashboardCard
from dashboard.core.dashboard_view import DashboardView
from dashboard.cards.schematic_heatmap import SchematicHeatmapCard
from dashboard.cards.image_viewer_card import ImageViewerCard
from dashboard.core.drilldown_bus import BUS, DrillDownEvent


# KPI配置
KPI_LABELS = ["total", "ok", "ng", "yield_rate", "review_ok", "review_ng"]


class HeaderBar(QWidget):
    """头部通栏 - 班次/工单/时间范围"""
    
    time_range_changed = pyqtSignal(int)
    custom_date_changed = pyqtSignal(str, str)
    shift_changed = pyqtSignal(str)
    work_order_changed = pyqtSignal(str)
    
    def __init__(self, service: DashboardService, parent=None):
        super().__init__(parent)
        self.service = service
        self._current_days = 0
        self._is_custom = False
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
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
        
        # 班次选择
        shift_label = QLabel("班次:")
        shift_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_secondary')};
                font-size: {Theme.get_font_size('sm')}px;
                font-weight: {Theme.FONT_WEIGHTS['medium']};
            }}
        """)
        layout.addWidget(shift_label)
        
        self._shift_combo = QComboBox()
        self._shift_combo.addItems(["全部班次", "白班", "夜班"])
        self._shift_combo.setStyleSheet(self._get_combo_style())
        self._shift_combo.currentTextChanged.connect(
            lambda text: self.shift_changed.emit(text if text != "全部班次" else "")
        )
        layout.addWidget(self._shift_combo)
        
        # 工单选择
        order_label = QLabel("工单:")
        order_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_secondary')};
                font-size: {Theme.get_font_size('sm')}px;
                font-weight: {Theme.FONT_WEIGHTS['medium']};
            }}
        """)
        layout.addWidget(order_label)
        
        self._order_combo = QComboBox()
        self._order_combo.setStyleSheet(self._get_combo_style())
        self._order_combo.setMinimumWidth(150)
        self._order_combo.currentTextChanged.connect(
            lambda text: self.work_order_changed.emit(text if text != "全部工单" else "")
        )
        layout.addWidget(self._order_combo)
        
        layout.addStretch()
        
        # 时间范围按钮
        self._time_buttons = {}
        time_options = [
            {"text": "今天", "days": 0},
            {"text": "近7天", "days": 7},
            {"text": "近30天", "days": 30},
            {"text": "自定义", "days": "custom"},
        ]
        
        for config in time_options:
            btn = QPushButton(config["text"])
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._get_time_button_style())
            btn.clicked.connect(lambda checked, d=config["days"]: self._on_time_clicked(d))
            layout.addWidget(btn)
            self._time_buttons[config["days"]] = btn
        
        # 默认选中今天
        self._time_buttons[0].setChecked(True)
        
        # 自定义日期范围
        self._date_start = QDateEdit()
        self._date_start.setCalendarPopup(True)
        self._date_start.setDate(QDate.currentDate().addDays(-7))
        self._date_start.setDisplayFormat("yyyy-MM-dd")
        self._date_start.setStyleSheet(self._get_date_style())
        self._date_start.setVisible(False)
        self._date_start.dateChanged.connect(self._on_custom_date_changed)
        layout.addWidget(self._date_start)
        
        self._date_separator = QLabel("~")
        self._date_separator.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_muted')};
                font-size: {Theme.get_font_size('sm')}px;
            }}
        """)
        self._date_separator.setVisible(False)
        layout.addWidget(self._date_separator)
        
        self._date_end = QDateEdit()
        self._date_end.setCalendarPopup(True)
        self._date_end.setDate(QDate.currentDate())
        self._date_end.setDisplayFormat("yyyy-MM-dd")
        self._date_end.setStyleSheet(self._get_date_style())
        self._date_end.setVisible(False)
        self._date_end.dateChanged.connect(self._on_custom_date_changed)
        layout.addWidget(self._date_end)
    
    def _get_combo_style(self):
        """获取下拉框样式"""
        return f"""
            QComboBox {{
                padding: 6px 12px;
                border: 1px solid {Theme.get_color('border')};
                border-radius: {Theme.get_radius('md')}px;
                background: {Theme.get_color('bg_card')};
                color: {Theme.get_color('text_primary')};
                font-size: {Theme.get_font_size('sm')}px;
                min-width: 100px;
            }}
            QComboBox:focus {{
                border-color: {Theme.get_color('primary')};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
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
    
    def _get_time_button_style(self):
        """获取时间按钮样式"""
        return f"""
            QPushButton {{
                background: {Theme.get_color('bg_card')};
                color: {Theme.get_color('text_secondary')};
                padding: 6px 14px;
                border-radius: {Theme.get_radius('md')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                font-size: {Theme.get_font_size('sm')}px;
                border: 1px solid {Theme.get_color('border')};
                min-width: 60px;
            }}
            QPushButton:hover {{
                background: {Theme.get_color('bg_active')};
                border-color: {Theme.get_color('primary_light')};
                color: {Theme.get_color('primary')};
            }}
            QPushButton:checked {{
                background: {Theme.get_color('primary')};
                color: {Theme.get_color('text_inverse')};
                border-color: {Theme.get_color('primary_dark')};
            }}
        """
    
    def _get_date_style(self):
        """获取日期选择器样式"""
        return f"""
            QDateEdit {{
                padding: 6px 10px;
                border: 1px solid {Theme.get_color('border')};
                border-radius: {Theme.get_radius('md')}px;
                background: {Theme.get_color('bg_card')};
                color: {Theme.get_color('text_primary')};
                font-size: {Theme.get_font_size('sm')}px;
                min-width: 100px;
            }}
            QDateEdit:focus {{
                border-color: {Theme.get_color('primary')};
            }}
        """
    
    def _on_time_clicked(self, days):
        """时间按钮点击事件"""
        if days == "custom":
            # 点击自定义按钮
            self._is_custom = True
            self._current_days = -1
            
            # 取消其他按钮选中
            for d, btn in self._time_buttons.items():
                if d != "custom":
                    btn.setChecked(False)
            self._time_buttons["custom"].setChecked(True)
            
            # 显示日期选择器
            self._set_date_visible(True)
            
            # 触发自定义日期变化
            self._emit_custom_date()
        else:
            # 点击预设时间按钮
            self._is_custom = False
            self._current_days = days
            
            # 取消自定义按钮选中
            if "custom" in self._time_buttons:
                self._time_buttons["custom"].setChecked(False)
            
            # 设置预设按钮选中状态
            for d, btn in self._time_buttons.items():
                if d != "custom":
                    btn.setChecked(d == days)
            
            # 隐藏日期选择器
            self._set_date_visible(False)
            
            # 触发预设时间变化
            self.time_range_changed.emit(days)
    
    def _set_date_visible(self, visible: bool):
        """设置日期选择器可见性"""
        self._date_start.setVisible(visible)
        self._date_separator.setVisible(visible)
        self._date_end.setVisible(visible)
    
    def _on_custom_date_changed(self):
        """自定义日期变化"""
        if self._is_custom:
            self._emit_custom_date()
    
    def _emit_custom_date(self):
        """触发自定义日期信号"""
        start = self._date_start.date().toString("yyyy-MM-dd")
        end = self._date_end.date().toString("yyyy-MM-dd")
        self.custom_date_changed.emit(start, end)
    
    def get_days(self) -> int:
        """获取当前选中的天数"""
        return self._current_days
    
    def get_date_range(self) -> tuple:
        """获取当前日期范围"""
        if self._is_custom:
            start = self._date_start.date().toString("yyyy-MM-dd")
            end = self._date_end.date().toString("yyyy-MM-dd")
            return (start, end)
        return (None, None)
    
    def update_work_orders(self, orders: list):
        """更新工单列表"""
        current = self._order_combo.currentText()
        self._order_combo.clear()
        self._order_combo.addItem("全部工单")
        self._order_combo.addItems(orders)
        
        # 恢复之前的选择
        index = self._order_combo.findText(current)
        if index >= 0:
            self._order_combo.setCurrentIndex(index)


class GranularitySelector(QWidget):
    """粒度选择器（30分钟/1小时/全天）"""
    
    granularity_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_value = "day"
        self._buttons = {}
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
    
    def set_options(self, options: list):
        """设置粒度选项"""
        # 清空现有按钮
        for btn in self._buttons.values():
            btn.deleteLater()
        self._buttons.clear()
        
        # 创建新按钮
        for config in options:
            btn = QPushButton(config["text"])
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._get_button_style())
            btn.clicked.connect(lambda checked, v=config["value"]: self._on_clicked(v))
            self._layout.addWidget(btn)
            self._buttons[config["value"]] = btn
        
        # 默认选中第一个
        if self._buttons:
            first_key = options[0]["value"]
            self._buttons[first_key].setChecked(True)
            self._current_value = first_key
    
    def _get_button_style(self):
        """获取按钮样式"""
        return f"""
            QPushButton {{
                background: {Theme.get_color('bg_card')};
                color: {Theme.get_color('text_secondary')};
                padding: 4px 10px;
                border-radius: {Theme.get_radius('sm')}px;
                font-weight: {Theme.FONT_WEIGHTS['medium']};
                font-size: {Theme.get_font_size('xs')}px;
                border: 1px solid {Theme.get_color('border')};
                min-width: 50px;
            }}
            QPushButton:hover {{
                background: {Theme.get_color('bg_active')};
                border-color: {Theme.get_color('primary_light')};
                color: {Theme.get_color('primary')};
            }}
            QPushButton:checked {{
                background: {Theme.get_color('primary')};
                color: {Theme.get_color('text_inverse')};
                border-color: {Theme.get_color('primary_dark')};
            }}
        """
    
    def _on_clicked(self, value: str):
        """按钮点击事件"""
        self._current_value = value
        for v, btn in self._buttons.items():
            btn.setChecked(v == value)
        self.granularity_changed.emit(value)
    
    def get_value(self) -> str:
        """获取当前选中的粒度"""
        return self._current_value



class RecentRecordsTable(QWidget):
    """最近检测记录表格"""
    
    filter_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_filter = "ng"
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 筛选按钮 + 表格（标题由 DashboardCard 提供）
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        filter_row.addStretch()

        self._filter_buttons = {}
        filters = [
            {"text": "NG", "value": "ng"},
            {"text": "OK", "value": "ok"},
            {"text": "全部", "value": "all"},
        ]

        for config in filters:
            btn = QPushButton(config["text"])
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._get_filter_button_style())
            btn.clicked.connect(lambda checked, v=config["value"]: self._on_filter_clicked(v))
            filter_row.addWidget(btn)
            self._filter_buttons[config["value"]] = btn

        self._filter_buttons["ng"].setChecked(True)

        layout.addLayout(filter_row)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["时间", "产品", "缺陷类型", "工站", "状态"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setStyleSheet(f"""
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
            QTableWidget::item:hover {{
                background: {Theme.get_color('bg_active')};
            }}
            QHeaderView::section {{
                background: {Theme.get_color('bg_secondary')};
                color: {Theme.get_color('text_secondary')};
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                font-size: {Theme.get_font_size('sm')}px;
                border: none;
                border-bottom: 2px solid {Theme.get_color('border')};
                border-right: 1px solid {Theme.get_color('border_light')};
                padding: 10px;
            }}
        """)
        layout.addWidget(self._table, 1)
    
    def _get_filter_button_style(self):
        """获取筛选按钮样式"""
        return f"""
            QPushButton {{
                background: {Theme.get_color('bg_card')};
                color: {Theme.get_color('text_secondary')};
                padding: 4px 12px;
                border-radius: {Theme.get_radius('sm')}px;
                font-weight: {Theme.FONT_WEIGHTS['medium']};
                font-size: {Theme.get_font_size('xs')}px;
                border: 1px solid {Theme.get_color('border')};
                min-width: 40px;
            }}
            QPushButton:hover {{
                background: {Theme.get_color('bg_active')};
                border-color: {Theme.get_color('primary_light')};
                color: {Theme.get_color('primary')};
            }}
            QPushButton:checked {{
                background: {Theme.get_color('primary')};
                color: {Theme.get_color('text_inverse')};
                border-color: {Theme.get_color('primary_dark')};
            }}
        """
    
    def _on_filter_clicked(self, value: str):
        """筛选按钮点击事件"""
        self._current_filter = value
        for v, btn in self._filter_buttons.items():
            btn.setChecked(v == value)
        self.filter_changed.emit(value)
    
    def get_filter(self) -> str:
        """获取当前筛选"""
        return self._current_filter
    
    def update_data(self, records: list):
        """更新表格数据"""
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(records))
        
        for i, record in enumerate(records):
            # 时间
            time_item = QTableWidgetItem(str(record.get("time", "")))
            self._table.setItem(i, 0, time_item)
            
            # 产品
            self._table.setItem(i, 1, QTableWidgetItem(record.get("sn", "")))
            
            # 缺陷类型
            defect = record.get("defect", "-")
            self._table.setItem(i, 2, QTableWidgetItem(defect))
            
            # 工站
            self._table.setItem(i, 3, QTableWidgetItem(record.get("station", "")))
            
            # 状态
            result = record.get("result", "")
            status_item = QTableWidgetItem(f"● {result}")
            if result == "NG":
                status_item.setForeground(QColor(Theme.get_color("danger")))
            else:
                status_item.setForeground(QColor(Theme.get_color("success")))
            self._table.setItem(i, 4, status_item)
        
        self._table.setSortingEnabled(True)


class HomePage(QWidget):
    """首页看板（卡片工作区架构）"""

    def __init__(self, service: DashboardService, db_manager=None, parent=None):
        super().__init__(parent)
        self.service = service
        self._db_manager = db_manager
        self._days = 0
        self._start_date = None
        self._end_date = None
        self._shift = ""
        self._work_order = ""
        self._cards = {}
        self._build_ui()
        self._connect_signals()
        self._refresh_all()

    def _build_ui(self):
        self._header = HeaderBar(self.service)
        self._kpi_panel = self._create_kpi_section()

        top_area = QWidget()
        top_area.setStyleSheet("background: transparent; border: none;")
        top_layout = QVBoxLayout(top_area)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        top_layout.addWidget(self._header)

        kpi_margin = 16
        kpi_wrapper = QWidget()
        kpi_wrapper.setStyleSheet("background: transparent; border: none;")
        kpi_wrapper_layout = QVBoxLayout(kpi_wrapper)
        kpi_wrapper_layout.setContentsMargins(kpi_margin, 0, kpi_margin, 0)
        kpi_wrapper_layout.addWidget(self._kpi_panel)
        top_layout.addWidget(kpi_wrapper)

        self._trend_chart = LineChart()
        self._trend_card = self._make_card("trend", "良率趋势", "📈", self._trend_chart)

        self._defect_stack = QStackedWidget()
        self._defect_donut = PieChart()
        self._defect_bar = BarChart()
        self._defect_stack.addWidget(self._defect_donut)  # index 0
        self._defect_stack.addWidget(self._defect_bar)     # index 1
        self._defect_stack.setCurrentIndex(0)
        self._defect_chart = self._defect_donut
        self._defect_card = self._make_card("defect", "缺陷分布TOP10", "🔍", self._defect_stack)
        self._defect_toggle_btn = QPushButton("📊 柱状图")
        self._defect_toggle_btn.setCheckable(True)
        self._defect_toggle_btn.setCursor(Qt.PointingHandCursor)
        self._defect_toggle_btn.setStyleSheet("""
            QPushButton {
                padding: 2px 8px; border: 1px solid #E2E8F0;
                border-radius: 4px; font-size: 10px; background: #F8FAFC;
                min-height: 20px; color: #475569; font-weight: 500;
            }
            QPushButton:hover { border-color: #3B82F6; color: #3B82F6; }
            QPushButton:checked {
                background: #EFF6FF; border-color: #3B82F6; color: #2563EB;
            }
        """)
        self._defect_toggle_btn.toggled.connect(self._on_defect_toggle)
        self._defect_card.add_header_widget(self._defect_toggle_btn)
        self._pareto_chart = ParetoChart()
        self._pareto_card = self._make_card("pareto", "缺陷Pareto分析", "📊", self._pareto_chart)

        self._records_table = RecentRecordsTable()
        self._records_card = DashboardCard("records", "最近检测记录", "📋")
        self._records_card.get_content_layout().addWidget(self._records_table)
        for btn in self._records_table._filter_buttons.values():
            self._records_card.add_header_widget(btn)
        self._records_table.layout().takeAt(0)

        self._heatmap_widget = SchematicHeatmapCard()
        self._heatmap_card = DashboardCard("heatmap", "区域热力图", "🔥")
        self._heatmap_card.get_content_layout().addWidget(self._heatmap_widget)
        self._heatmap_card.add_header_widget(self._heatmap_widget._toggle_btn)
        self._heatmap_widget.layout().takeAt(0)

        self._image_viewer_card = ImageViewerCard(self._db_manager) if self._db_manager else None
        if self._image_viewer_card:
            self._image_viewer_card.set_time_range(self._days)

        self._dashboard_view = DashboardView()
        self._dashboard_view.add_card(self._trend_card)
        self._dashboard_view.add_card(self._defect_card)
        self._dashboard_view.add_card(self._pareto_card)
        self._dashboard_view.add_card(self._records_card)
        self._dashboard_view.add_card(self._heatmap_card)
        if self._image_viewer_card:
            self._dashboard_view.add_card(self._image_viewer_card)

        self._cards = {
            "trend": self._trend_card,
            "defect": self._defect_card,
            "pareto": self._pareto_card,
            "records": self._records_card,
            "heatmap": self._heatmap_card,
        }
        if self._image_viewer_card:
            self._cards["image_viewer"] = self._image_viewer_card

        self._dashboard_view.load_layout()
        if len(self._dashboard_view.slot_manager.slots) == 0:
            self._dashboard_view.apply_layout_preset("1x2")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(top_area)
        main_layout.addWidget(self._dashboard_view, 1)

    def _make_card(self, card_id: str, card_name: str, icon: str, chart_widget) -> DashboardCard:
        card = DashboardCard(card_id, card_name, icon)
        card.get_content_layout().addWidget(chart_widget)
        combo = QComboBox()
        combo.setMinimumWidth(80)
        combo.setStyleSheet("""
            QComboBox {
                padding: 2px 6px; border: 1px solid #E2E8F0;
                border-radius: 4px; font-size: 10px; background: #F8FAFC;
                min-height: 20px;
            }
            QComboBox:focus { border-color: #3B82F6; }
            QComboBox::drop-down { border: none; width: 16px; }
        """)
        combo.currentTextChanged.connect(
            lambda text, cid=card_id: self._on_card_granularity_changed(cid)
        )
        card._granularity_combo = combo
        card.add_header_widget(combo)
        return card

    def _on_card_granularity_changed(self, card_id: str):
        self._refresh_card(card_id)

    def _on_defect_toggle(self, checked: bool):
        """缺陷图切换：环形图 ↔ 柱状图"""
        self._defect_stack.setCurrentIndex(1 if checked else 0)
        self._defect_toggle_btn.setText("🍩 环形图" if checked else "📊 柱状图")
        self._defect_chart = self._defect_bar if checked else self._defect_donut

    def _create_kpi_section(self) -> QWidget:
        config = ConfigManager.load()
        enabled_kpis = config.get("dashboard_kpi_items", KPI_LABELS)
        self._kpi_panel = KPIStripPanel(enabled_kpis)
        return self._kpi_panel

    def set_kpi_items(self, keys: list):
        if hasattr(self, '_kpi_panel'):
            self._kpi_panel.set_enabled_keys(keys)

    def _connect_signals(self):
        self._header.time_range_changed.connect(self._on_time_range_changed)
        self._header.custom_date_changed.connect(self._on_custom_date_changed)
        self._records_table.filter_changed.connect(self._on_records_filter_changed)

        self._defect_donut.drilldown_triggered.connect(self._on_defect_drilldown)
        self._defect_bar.drilldown_triggered.connect(self._on_defect_drilldown)
        self._heatmap_widget.drilldown_triggered.connect(self._on_heatmap_drilldown)

    def _on_time_range_changed(self, days: int):
        self._days = days
        self._start_date = None
        self._end_date = None
        if self._image_viewer_card:
            self._image_viewer_card.set_time_range(days)
        self._refresh_all()

    def _on_custom_date_changed(self, start_date: str, end_date: str):
        self._start_date = start_date
        self._end_date = end_date
        self._days = -1
        if self._image_viewer_card:
            self._image_viewer_card.set_time_range(-1, start_date, end_date)
        self._refresh_all()

    def _refresh_all(self):
        if self._days >= 0:
            options = self.service.get_granularity_options(self._days)
        else:
            options = TIME_RANGE_GRANULARITY[7]
        for cid in ["trend", "defect", "pareto"]:
            card = self._cards.get(cid)
            if card and hasattr(card, '_granularity_combo'):
                combo = card._granularity_combo
                combo.blockSignals(True)
                combo.clear()
                for opt in options:
                    combo.addItem(opt["text"], opt["value"])
                combo.blockSignals(False)
        self.refresh()

    def refresh(self):
        attempts = [
            (self._refresh_kpi, "刷新KPI"),
            (lambda: self._refresh_card("trend"), "刷新趋势"),
            (lambda: self._refresh_card("defect"), "刷新缺陷"),
            (lambda: self._refresh_card("pareto"), "刷新Pareto"),
            (lambda: self._refresh_heatmap(), "刷新热力图"),
            (lambda: self._refresh_card("records"), "刷新记录"),
        ]
        for method, name in attempts:
            try:
                method()
            except Exception as e:
                print(f"{name}失败: {e}")
        try:
            if self._days >= 0:
                work_orders = self.service.get_work_orders(self._days)
            else:
                work_orders = self.service.get_work_orders(30)
            self._header.update_work_orders(work_orders)
        except Exception as e:
            print(f"更新工单列表失败: {e}")

    def _refresh_kpi(self):
        if self._days >= 0:
            kpi_trend = self.service.kpi_trend(self._days)
        else:
            kpi_trend = self.service.kpi_trend_custom_date(self._start_date, self._end_date)
        self._kpi_panel.update_data(kpi_trend.get("current", {}), kpi_trend.get("deltas", {}))

    def _refresh_card(self, card_id: str):
        card = self._cards.get(card_id)
        if card is None:
            return
        combo = getattr(card, '_granularity_combo', None)
        granularity = combo.currentData() if combo else "day"

        if card_id == "trend":
            trend = self.service.yield_trend_granularity(self._days, granularity) if self._days >= 0 else \
                    self.service.yield_trend_custom_date(self._start_date, self._end_date, granularity)
            if trend:
                self._trend_chart.set_data(
                    [t["period"] for t in trend],
                    [{"name": "良率", "data": [float(t["yield_rate"]) for t in trend]}],
                    smooth=True, fill=True
                )
        elif card_id == "defect":
            defects = self.service.defect_distribution_granularity(self._days, granularity, 10) if self._days >= 0 else \
                      self.service.defect_distribution_custom_date(self._start_date, self._end_date, granularity, 10)
            if defects:
                labels = [d["name"] for d in defects]
                counts = [d["count"] for d in defects]
                pct_labels = [f"{d['name']}\n{d['pct']}%" for d in defects]
                self._defect_donut.set_data(labels, counts)
                self._defect_bar.set_data(pct_labels, counts, orient="vertical")
        elif card_id == "pareto":
            defects = self.service.defect_distribution_granularity(self._days, granularity, 10) if self._days >= 0 else \
                      self.service.defect_distribution_custom_date(self._start_date, self._end_date, granularity, 10)
            if defects:
                self._pareto_chart.set_data(
                    [d["name"] for d in defects],
                    [d["count"] for d in defects],
                    show_80_line=True
                )
        elif card_id == "records":
            filter_val = self._records_table.get_filter()
            records = self.service.recent_records(20, filter_val, self._days) if self._days >= 0 else \
                      self.service.recent_records_custom_date(20, filter_val, self._start_date, self._end_date)
            self._records_table.update_data(records)

    def _refresh_heatmap(self):
        days = self._days if self._days >= 0 else 30
        data = self.service.heatmap(days)
        if self._heatmap_widget:
            self._heatmap_widget.set_data(data)

    def _on_defect_drilldown(self, defect_name: str):
        BUS.emit(DrillDownEvent(source="defect", filter_type="Defect", value=defect_name))

    def _on_heatmap_drilldown(self, filter_type: str, area: str):
        BUS.emit(DrillDownEvent(source="heatmap", filter_type=filter_type, value=area))

    def _on_records_filter_changed(self, filter_val: str):
        self._refresh_card("records")
