"""
页面基类
提供统一的页面结构和通用功能
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor
from services.dashboard_service import DashboardService
from ui.theme import Theme, get_toggle_button_style
from ui.widgets.loading_widget import StatusContainer


# 时间选项配置
TIME_OPTIONS = [
    {"text": "今天", "days": 0, "icon": "📅"},
    {"text": "近7天", "days": 7, "icon": "📆"},
    {"text": "近30天", "days": 30, "icon": "🗓️"},
]

# 粒度选项配置
GRANULARITY_OPTIONS = [
    {"text": "按天", "value": "day", "icon": "📊"},
    {"text": "按周", "value": "week", "icon": "📈"},
    {"text": "按月", "value": "month", "icon": "📉"},
]


class TimeFilterBar(QWidget):
    """时间筛选栏组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_days = 0
        self._buttons = {}
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标签
        label = QLabel("时间范围:")
        label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_secondary')};
                font-size: {Theme.get_font_size('sm')}px;
                font-weight: {Theme.FONT_WEIGHTS['medium']};
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(label)
        
        # 时间按钮
        for config in TIME_OPTIONS:
            btn = QPushButton(f"{config['icon']} {config['text']}")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._get_button_style())
            btn.clicked.connect(lambda checked, d=config['days']: self._on_clicked(d))
            layout.addWidget(btn)
            self._buttons[config['days']] = btn
        
        # 默认选中
        self._buttons[0].setChecked(True)
        
        layout.addStretch()
    
    def _get_button_style(self):
        """获取按钮样式"""
        c = Theme.COLORS
        r = Theme.BORDER_RADIUS
        f = Theme.FONT_SIZES
        
        return f"""
            QPushButton {{
                background: {c['bg_card']};
                color: {c['text_secondary']};
                padding: 8px 16px;
                border-radius: {r['md']}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                font-size: {f['sm']}px;
                border: 1px solid {c['border']};
                min-width: 80px;
            }}
            QPushButton:hover {{
                background: {c['bg_active']};
                border-color: {c['primary_light']};
                color: {c['primary']};
            }}
            QPushButton:checked {{
                background: {c['primary']};
                color: {c['text_inverse']};
                border-color: {c['primary_dark']};
            }}
        """
    
    def _on_clicked(self, days: int):
        """按钮点击事件"""
        self._current_days = days
        for d, btn in self._buttons.items():
            btn.setChecked(d == days)
        self.timeChanged.emit(days)
    
    def get_days(self) -> int:
        """获取当前选中的天数"""
        return self._current_days
    
    # 自定义信号
    from PyQt5.QtCore import pyqtSignal
    timeChanged = pyqtSignal(int)


class GranularityFilterBar(QWidget):
    """粒度筛选栏组件"""
    
    def __init__(self, options=None, default="day", parent=None):
        super().__init__(parent)
        self._options = options or GRANULARITY_OPTIONS
        self._current_value = default
        self._buttons = {}
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标签
        label = QLabel("统计粒度:")
        label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_secondary')};
                font-size: {Theme.get_font_size('sm')}px;
                font-weight: {Theme.FONT_WEIGHTS['medium']};
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(label)
        
        # 粒度按钮
        for config in self._options:
            btn = QPushButton(f"{config['icon']} {config['text']}")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(self._get_button_style())
            btn.clicked.connect(lambda checked, v=config['value']: self._on_clicked(v))
            layout.addWidget(btn)
            self._buttons[config['value']] = btn
        
        # 默认选中
        if self._current_value in self._buttons:
            self._buttons[self._current_value].setChecked(True)
        
        layout.addStretch()
    
    def _get_button_style(self):
        """获取按钮样式"""
        c = Theme.COLORS
        r = Theme.BORDER_RADIUS
        f = Theme.FONT_SIZES
        
        return f"""
            QPushButton {{
                background: {c['bg_card']};
                color: {c['text_secondary']};
                padding: 6px 12px;
                border-radius: {r['md']}px;
                font-weight: {Theme.FONT_WEIGHTS['medium']};
                font-size: {f['xs']}px;
                border: 1px solid {c['border']};
                min-width: 60px;
            }}
            QPushButton:hover {{
                background: {c['bg_active']};
                border-color: {c['primary_light']};
                color: {c['primary']};
            }}
            QPushButton:checked {{
                background: {c['primary']};
                color: {c['text_inverse']};
                border-color: {c['primary_dark']};
            }}
        """
    
    def _on_clicked(self, value: str):
        """按钮点击事件"""
        self._current_value = value
        for v, btn in self._buttons.items():
            btn.setChecked(v == value)
        self.granularityChanged.emit(value)
    
    def get_value(self) -> str:
        """获取当前选中的粒度"""
        return self._current_value
    
    # 自定义信号
    from PyQt5.QtCore import pyqtSignal
    granularityChanged = pyqtSignal(str)


class SectionTitle(QWidget):
    """区域标题组件"""
    
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self._setup_ui(title, subtitle)
    
    def _setup_ui(self, title: str, subtitle: str):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_primary')};
                font-size: {Theme.get_font_size('lg')}px;
                font-weight: {Theme.FONT_WEIGHTS['bold']};
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(title_label)
        
        # 副标题
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet(f"""
                QLabel {{
                    color: {Theme.get_color('text_muted')};
                    font-size: {Theme.get_font_size('sm')}px;
                    background: transparent;
                    border: none;
                }}
            """)
            layout.addWidget(subtitle_label)


class ChartCard(QFrame):
    """图表卡片容器"""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._setup_ui(title)
    
    def _setup_ui(self, title: str):
        """设置UI"""
        self.setStyleSheet(f"""
            QFrame {{
                background: {Theme.get_color('bg_card')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: {Theme.get_radius('lg')}px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet(f"""
                QLabel {{
                    color: {Theme.get_color('text_primary')};
                    font-size: {Theme.get_font_size('md')}px;
                    font-weight: {Theme.FONT_WEIGHTS['semibold']};
                    background: transparent;
                    border: none;
                }}
            """)
            layout.addWidget(title_label)
        
        # 内容区域
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._content, 1)
    
    @property
    def content_layout(self):
        """获取内容布局"""
        return self._content_layout


class BasePage(QWidget):
    """页面基类"""
    
    def __init__(self, service: DashboardService, parent=None):
        super().__init__(parent)
        self.service = service
        self._days = 0
        self._granularity = "day"
        
        # 主布局
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(24, 20, 24, 20)
        self._main_layout.setSpacing(16)
        
        # 状态容器
        self._status_container = StatusContainer()
        self._main_layout.addWidget(self._status_container)
        
        # 内容布局（在状态容器内）
        self._content_layout = self._status_container.content_layout
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(16)
        
        # 滚动区域
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)
        
        # 设置重试回调
        self._status_container.on_retry(self.refresh)
    
    def _add_time_filter(self):
        """添加时间筛选栏"""
        self._time_filter = TimeFilterBar()
        self._time_filter.timeChanged.connect(self._on_time_changed)
        self._content_layout.addWidget(self._time_filter)
    
    def _add_granularity_filter(self, options=None, default="day"):
        """添加粒度筛选栏"""
        self._granularity_filter = GranularityFilterBar(options, default)
        self._granularity_filter.granularityChanged.connect(
            lambda g: self._on_granularity_changed(g)
        )
        self._content_layout.addWidget(self._granularity_filter)
        return default
    
    def _add_section_title(self, title: str, subtitle: str = ""):
        """添加区域标题"""
        section = SectionTitle(title, subtitle)
        self._content_layout.addWidget(section)
        return section
    
    def _add_chart_card(self, title: str = "") -> ChartCard:
        """添加图表卡片"""
        card = ChartCard(title)
        self._content_layout.addWidget(card, 1)
        return card
    
    def _on_time_changed(self, days: int):
        """时间变化事件"""
        self._days = days
        self.refresh()
    
    def _on_granularity_changed(self, value: str):
        """粒度变化事件"""
        self._granularity = value
        self.refresh()
    
    def refresh(self):
        """刷新页面数据（子类重写）"""
        pass
    
    def set_loading(self, text: str = "加载数据中..."):
        """设置加载状态"""
        self._status_container.set_loading(text)
    
    def set_empty(self, title: str = "暂无数据", desc: str = ""):
        """设置空数据状态"""
        self._status_container.set_empty(title, desc)
    
    def set_error(self, message: str = "数据加载失败"):
        """设置错误状态"""
        self._status_container.set_error(message)
    
    def set_normal(self):
        """设置正常状态"""
        self._status_container.set_normal()
