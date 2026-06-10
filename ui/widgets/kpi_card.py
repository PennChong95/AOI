"""
专业KPI卡片组件
支持动画效果、趋势指示、自定义主题
"""

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, pyqtProperty, QPoint, QSize
)
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QFont, QLinearGradient
from ui.theme import Theme, KPI_CONFIG


class AnimatedNumberLabel(QLabel):
    """带动画效果的数字标签"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._display_value = 0
        self._animation = QPropertyAnimation(self, b"display_value")
        self._animation.setDuration(800)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._is_percentage = False
        self._prefix = ""
        self._suffix = ""
    
    @pyqtProperty(float)
    def display_value(self):
        return self._display_value
    
    @display_value.setter
    def display_value(self, value):
        self._display_value = value
        if self._is_percentage:
            self.setText(f"{self._prefix}{value:.1f}{self._suffix}%")
        else:
            self.setText(f"{self._prefix}{int(value):,}{self._suffix}")
    
    def set_value(self, value, is_percentage=False, prefix="", suffix="", animate=True):
        """设置数值，支持动画"""
        self._is_percentage = is_percentage
        self._prefix = prefix
        self._suffix = suffix
        
        if animate and self._value != value:
            self._animation.stop()
            self._animation.setStartValue(self._display_value)
            self._animation.setEndValue(float(value))
            self._animation.start()
        else:
            self.display_value = float(value)
        
        self._value = value


class TrendIndicator(QWidget):
    """趋势指示器组件（带箭头条状效果）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._delta = 0
        self._is_inverse = False
        self._text = ""
        self._color = QColor("#94A3B8")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(16)
    
    def set_trend(self, delta: float, is_inverse: bool = False):
        """设置趋势值"""
        self._delta = delta
        self._is_inverse = is_inverse
        is_positive = delta > 0
        is_good = is_positive != is_inverse
        
        if delta == 0:
            self._text = "0.0%"
            self._color = QColor(Theme.get_color("text_muted"))
        else:
            arrow = "▲" if is_positive else "▼"
            self._text = f"{arrow}{abs(delta):.1f}%"
            self._color = QColor(Theme.get_color("success") if is_good else Theme.get_color("danger"))
        self.update()
    
    def paintEvent(self, event):
        if not self._text:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景条
        bg = QColor(self._color)
        bg.setAlpha(30)
        path = QPainterPath()
        path.addRoundedRect(0, 1, self.width(), self.height() - 2, 4, 4)
        painter.fillPath(path, bg)
        
        # 绘制箭头和文字
        painter.setPen(self._color)
        font = painter.font()
        font.setPixelSize(11)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self._text)
        painter.end()


class KPICard(QFrame):
    """专业KPI卡片组件"""
    
    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self._key = key
        self._config = KPI_CONFIG.get(key, {})
        self._setup_ui()
        self._setup_style()
        self._setup_shadow()
    
    def _setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)
        
        # 名称
        self._name_label = QLabel(self._config.get("name", ""))
        self._name_label.setAlignment(Qt.AlignCenter)
        self._name_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_secondary')};
                font-size: {Theme.get_font_size('sm') + 2}px;
                font-weight: {Theme.FONT_WEIGHTS['medium']};
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(self._name_label)
        
        # 数值
        color_key = self._config.get("color", "primary")
        self._value_label = AnimatedNumberLabel()
        self._value_label.setAlignment(Qt.AlignCenter)
        self._value_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color(color_key)};
                font-size: {Theme.get_font_size('4xl')}px;
                font-weight: {Theme.FONT_WEIGHTS['bold']};
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(self._value_label)
        
        # 趋势指示器
        self._trend_indicator = TrendIndicator()
        layout.addWidget(self._trend_indicator)
    
    def _setup_style(self):
        """设置卡片样式"""
        color_key = self._config.get("color", "primary")
        color = Theme.get_color(color_key)
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {Theme.get_color('bg_card')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: {Theme.get_radius('lg')}px;
            }}
            QFrame:hover {{
                border-color: {color};
            }}
        """)
    
    def _setup_shadow(self):
        """设置阴影效果"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
    
    def set_value(self, value, is_percentage=False):
        """设置数值"""
        self._value_label.set_value(value, is_percentage=is_percentage, animate=True)
    
    def set_trend(self, delta: float):
        """设置趋势"""
        # ng类指标下降是好事，需要反向
        is_inverse = self._key in ("ng", "review_ng")
        self._trend_indicator.set_trend(delta, is_inverse=is_inverse)


class KPISummaryPanel(QFrame):
    """KPI摘要面板（所有指标在一个面板上）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self):
        """设置UI布局"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)
        
        # 设置最小高度
        self.setMinimumHeight(120)
        
        # KPI项配置
        kpi_items = [
            {"key": "total", "name": "总投入", "icon": "📊", "color": "primary", "is_pct": False},
            {"key": "ok", "name": "OK数", "icon": "✓", "color": "success", "is_pct": False},
            {"key": "ng", "name": "NG数", "icon": "✕", "color": "danger", "is_pct": False},
            {"key": "yield_rate", "name": "良率", "icon": "◎", "color": "info", "is_pct": True},
            {"key": "review_ok", "name": "复判OK", "icon": "✓", "color": "success", "is_pct": False},
            {"key": "review_ng", "name": "复判NG", "icon": "✕", "color": "danger", "is_pct": False},
        ]
        
        self._items = {}
        
        for i, item in enumerate(kpi_items):
            # 添加分隔线（除了第一个）
            if i > 0:
                separator = QFrame()
                separator.setFrameShape(QFrame.VLine)
                separator.setStyleSheet(f"""
                    QFrame {{
                        background: {Theme.get_color('border')};
                        max-width: 1px;
                        margin: 4px 8px;
                    }}
                """)
                layout.addWidget(separator)
            
            # 创建KPI项
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(8, 0, 8, 0)
            item_layout.setSpacing(4)
            
            # 名称
            name_label = QLabel(item["name"])
            name_label.setStyleSheet(f"""
                QLabel {{
                    color: {Theme.get_color('text_secondary')};
                    font-size: {Theme.get_font_size('sm')}px;
                    font-weight: {Theme.FONT_WEIGHTS['bold']};
                    background: transparent;
                    border: none;
                }}
            """)
            name_label.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(name_label)
            
            # 数值
            value_label = AnimatedNumberLabel()
            value_label.setStyleSheet(f"""
                QLabel {{
                    color: {Theme.get_color(item['color'])};
                    font-size: {Theme.get_font_size('2xl')}px;
                    font-weight: {Theme.FONT_WEIGHTS['bold']};
                    background: transparent;
                    border: none;
                }}
            """)
            value_label.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(value_label)
            
            # 趋势
            trend_label = QLabel()
            trend_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {Theme.get_font_size('xs')}px;
                    font-weight: {Theme.FONT_WEIGHTS['semibold']};
                    background: transparent;
                    border: none;
                }}
            """)
            trend_label.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(trend_label)
            
            layout.addWidget(item_widget, 1)
            
            # 存储引用
            self._items[item["key"]] = {
                "value_label": value_label,
                "trend_label": trend_label,
                "is_pct": item["is_pct"],
            }
    
    def _setup_style(self):
        """设置卡片样式"""
        self.setStyleSheet(f"""
            QFrame {{
                background: {Theme.get_color('bg_card')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: {Theme.get_radius('lg')}px;
            }}
            QFrame:hover {{
                border-color: {Theme.get_color('primary_light')};
            }}
        """)
    
    def update_data(self, current: dict, deltas: dict):
        """更新数据"""
        for key, item in self._items.items():
            val = current.get(key, 0)
            delta = deltas.get(key, 0)
            is_pct = item["is_pct"]
            
            # 更新数值
            item["value_label"].set_value(val, is_percentage=is_pct, animate=True)
            
            # 更新趋势
            is_inverse = key in ("ng", "review_ng")
            is_positive = delta > 0
            is_good = is_positive != is_inverse
            
            if delta == 0:
                color = Theme.get_color("text_muted")
                text = "→ 0%"
            elif is_good:
                color = Theme.get_color("success")
                arrow = "↑" if is_positive else "↓"
                text = f"{arrow} {abs(delta):.1f}%"
            else:
                color = Theme.get_color("danger")
                arrow = "↑" if is_positive else "↓"
                text = f"{arrow} {abs(delta):.1f}%"
            
            item["trend_label"].setText(text)
            item["trend_label"].setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: {Theme.get_font_size('xs')}px;
                    font-weight: {Theme.FONT_WEIGHTS['semibold']};
                    background: transparent;
                    border: none;
                }}
            """)


class KPICardMini(QFrame):
    """迷你KPI卡片（用于紧凑布局）"""
    
    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self._key = key
        self._config = KPI_CONFIG.get(key, {})
        self._setup_ui()
        self._setup_style()
    
    def _setup_ui(self):
        """设置UI布局"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        # 图标
        color_key = self._config.get("color", "primary")
        color = Theme.get_color(color_key)
        
        icon_map = {
            "total": "📊",
            "ok": "✓",
            "ng": "✕",
            "yield": "◎",
            "review_ok": "✓",
            "review_ng": "✕",
        }
        
        self._icon_label = QLabel(icon_map.get(self._config.get("icon", ""), "●"))
        self._icon_label.setFixedSize(32, 32)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setStyleSheet(f"""
            QLabel {{
                background: {Theme.get_color(self._config.get('bg_color', 'primary_lighter'))};
                color: {color};
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self._icon_label)
        
        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self._name_label = QLabel(self._config.get("name", ""))
        self._name_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_muted')};
                font-size: {Theme.get_font_size('xs')}px;
                background: transparent;
                border: none;
            }}
        """)
        info_layout.addWidget(self._name_label)
        
        value_layout = QHBoxLayout()
        value_layout.setSpacing(6)
        
        self._value_label = AnimatedNumberLabel()
        self._value_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_primary')};
                font-size: {Theme.get_font_size('xl')}px;
                font-weight: {Theme.FONT_WEIGHTS['bold']};
                background: transparent;
                border: none;
            }}
        """)
        value_layout.addWidget(self._value_label)
        
        self._trend_label = QLabel()
        self._trend_label.setStyleSheet(f"""
            QLabel {{
                font-size: {Theme.get_font_size('xs')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                background: transparent;
                border: none;
            }}
        """)
        value_layout.addWidget(self._trend_label)
        value_layout.addStretch()
        
        info_layout.addLayout(value_layout)
        layout.addLayout(info_layout, 1)
    
    def _setup_style(self):
        """设置卡片样式"""
        self.setStyleSheet(f"""
            QFrame {{
                background: {Theme.get_color('bg_card')};
                border: 1px solid {Theme.get_color('border')};
                border-radius: {Theme.get_radius('md')}px;
            }}
            QFrame:hover {{
                border-color: {Theme.get_color('primary')};
                background: {Theme.get_color('bg_hover')};
            }}
        """)
    
    def set_value(self, value, is_percentage=False):
        """设置数值"""
        self._value_label.set_value(value, is_percentage=is_percentage, animate=True)
    
    def set_trend(self, delta: float):
        """设置趋势"""
        is_inverse = self._key in ("ng", "review_ng")
        is_positive = delta > 0
        is_good = is_positive != is_inverse
        
        if delta == 0:
            color = Theme.get_color("text_muted")
            text = "→ 0%"
        elif is_good:
            color = Theme.get_color("success")
            arrow = "↑" if is_positive else "↓"
            text = f"{arrow} {abs(delta):.1f}%"
        else:
            color = Theme.get_color("danger")
            arrow = "↑" if is_positive else "↓"
            text = f"{arrow} {abs(delta):.1f}%"
        
        self._trend_label.setText(text)
        self._trend_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: {Theme.get_font_size('xs')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                background: transparent;
                border: none;
            }}
        """)


class KPIStripPanel(QWidget):
    """可配置的KPI卡片条：水平等宽排列，高度固定"""

    def __init__(self, enabled_keys: list = None, parent=None):
        super().__init__(parent)
        self._enabled_keys = enabled_keys or ["total", "ok", "ng", "yield_rate", "review_ok", "review_ng"]
        self._cards = {}
        self._setup_ui()

    def _setup_ui(self):
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._rebuild()

    def set_enabled_keys(self, keys: list):
        if set(keys) != set(self._enabled_keys):
            self._enabled_keys = keys
            self._rebuild()

    def _rebuild(self):
        for card in self._cards.values():
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for key in self._enabled_keys:
            card = KPICard(key)
            self._layout.addWidget(card, 1)
            self._cards[key] = card

    def update_data(self, current: dict, deltas: dict):
        for key, card in self._cards.items():
            val = current.get(key, 0)
            delta = deltas.get(key, 0)
            is_pct = key in ("yield_rate", "post_review_yield_rate")
            card.set_value(val, is_percentage=is_pct)
            card.set_trend(delta)


def create_kpi_card(key: str, compact: bool = False) -> QFrame:
    """工厂方法：创建KPI卡片"""
    if compact:
        return KPICardMini(key)
    else:
        return KPICard(key)


def create_kpi_summary_panel() -> KPISummaryPanel:
    """工厂方法：创建KPI摘要面板"""
    return KPISummaryPanel()
