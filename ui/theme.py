"""
统一主题配色系统
提供一致的视觉风格和配色方案
"""

from enum import Enum
from typing import Dict, Any


class ColorRole(Enum):
    """颜色角色枚举"""
    PRIMARY = "primary"
    PRIMARY_LIGHT = "primary_light"
    PRIMARY_DARK = "primary_dark"
    SECONDARY = "secondary"
    SUCCESS = "success"
    SUCCESS_LIGHT = "success_light"
    DANGER = "danger"
    DANGER_LIGHT = "danger_light"
    WARNING = "warning"
    WARNING_LIGHT = "warning_light"
    INFO = "info"
    INFO_LIGHT = "info_light"
    BG_PRIMARY = "bg_primary"
    BG_SECONDARY = "bg_secondary"
    BG_CARD = "bg_card"
    BG_HOVER = "bg_hover"
    TEXT_PRIMARY = "text_primary"
    TEXT_SECONDARY = "text_secondary"
    TEXT_MUTED = "text_muted"
    TEXT_INVERSE = "text_inverse"
    BORDER = "border"
    BORDER_LIGHT = "border_light"
    SHADOW = "shadow"
    OVERLAY = "overlay"


class Theme:
    """主题管理类"""
    
    # 现代专业配色方案
    COLORS: Dict[str, str] = {
        # 主色调 - 蓝色系
        "primary": "#3B82F6",
        "primary_light": "#93C5FD",
        "primary_lighter": "#DBEAFE",
        "primary_dark": "#2563EB",
        "primary_darker": "#1D4ED8",
        
        # 辅助色 - 紫色系
        "secondary": "#8B5CF6",
        "secondary_light": "#C4B5FD",
        "secondary_dark": "#7C3AED",
        
        # 语义色
        "success": "#10B981",
        "success_light": "#A7F3D0",
        "success_lighter": "#D1FAE5",
        "success_dark": "#059669",
        
        "danger": "#EF4444",
        "danger_light": "#FCA5A5",
        "danger_lighter": "#FEE2E2",
        "danger_dark": "#DC2626",
        
        "warning": "#F59E0B",
        "warning_light": "#FCD34D",
        "warning_lighter": "#FEF3C7",
        "warning_dark": "#D97706",
        
        "info": "#06B6D4",
        "info_light": "#67E8F9",
        "info_lighter": "#CFFAFE",
        "info_dark": "#0891B2",
        
        # 背景色
        "bg_primary": "#F8FAFC",
        "bg_secondary": "#F1F5F9",
        "bg_card": "#FFFFFF",
        "bg_hover": "#F8FAFC",
        "bg_active": "#EEF2FF",
        "bg_sidebar": "#1E293B",
        "bg_sidebar_hover": "#334155",
        "bg_sidebar_active": "#3B82F6",
        
        # 文字色
        "text_primary": "#1E293B",
        "text_secondary": "#475569",
        "text_muted": "#94A3B8",
        "text_inverse": "#FFFFFF",
        "text_sidebar": "#CBD5E1",
        "text_sidebar_active": "#FFFFFF",
        
        # 边框色
        "border": "#E2E8F0",
        "border_light": "#F1F5F9",
        "border_focus": "#3B82F6",
        "border_error": "#EF4444",
        
        # 特殊色
        "shadow": "rgba(0, 0, 0, 0.1)",
        "shadow_light": "rgba(0, 0, 0, 0.05)",
        "shadow_dark": "rgba(0, 0, 0, 0.2)",
        "overlay": "rgba(0, 0, 0, 0.5)",
        
        # 图表配色
        "chart_colors": "#3B82F6,#8B5CF6,#10B981,#F59E0B,#EF4444,#EC4899,#06B6D4,#F97316,#84CC16,#64748B",
    }
    
    # 间距系统
    SPACING = {
        "xs": 4,
        "sm": 8,
        "md": 12,
        "lg": 16,
        "xl": 24,
        "2xl": 32,
        "3xl": 48,
    }
    
    # 圆角系统
    BORDER_RADIUS = {
        "sm": 4,
        "md": 6,
        "lg": 8,
        "xl": 12,
        "2xl": 16,
        "full": 9999,
    }
    
    # 字体系统
    FONT_SIZES = {
        "xs": 10,
        "sm": 11,
        "base": 12,
        "md": 13,
        "lg": 14,
        "xl": 16,
        "2xl": 18,
        "3xl": 20,
        "4xl": 24,
        "5xl": 30,
    }
    
    FONT_WEIGHTS = {
        "normal": 400,
        "medium": 500,
        "semibold": 600,
        "bold": 700,
    }
    
    # 动画时长
    ANIMATION_DURATION = {
        "fast": 150,
        "normal": 250,
        "slow": 350,
    }
    
    @classmethod
    def get_color(cls, role: str) -> str:
        """获取颜色值"""
        return cls.COLORS.get(role, "#000000")
    
    @classmethod
    def get_spacing(cls, size: str) -> int:
        """获取间距值"""
        return cls.SPACING.get(size, 8)
    
    @classmethod
    def get_radius(cls, size: str) -> int:
        """获取圆角值"""
        return cls.BORDER_RADIUS.get(size, 6)
    
    @classmethod
    def get_font_size(cls, size: str) -> int:
        """获取字体大小"""
        return cls.FONT_SIZES.get(size, 12)
    
    @classmethod
    def get_chart_colors(cls) -> list:
        """获取图表颜色列表"""
        return cls.COLORS["chart_colors"].split(",")


def get_dashboard_style() -> str:
    """获取看板主样式"""
    c = Theme.COLORS
    r = Theme.BORDER_RADIUS
    f = Theme.FONT_SIZES
    
    return f"""
    /* 主对话框和QWidget */
    QDialog, QWidget {{
        background-color: {c['bg_primary']};
        color: {c['text_primary']};
        font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei UI", -apple-system, sans-serif;
        font-size: {f['base']}px;
    }}
    
    /* 按钮基础样式 */
    QPushButton {{
        padding: 7px 16px;
        border: none;
        border-radius: {r['md']}px;
        font-size: {f['base']}px;
        font-weight: {Theme.FONT_WEIGHTS['semibold']};
        background: {c['bg_secondary']};
        color: {c['text_secondary']};
    }}
    QPushButton:hover {{
        background: {c['border']};
    }}
    QPushButton:pressed {{
        background: {c['border_light']};
    }}
    QPushButton:disabled {{
        background: {c['bg_secondary']};
        color: {c['text_muted']};
    }}
    
    /* 主要按钮 */
    QPushButton[primary="true"] {{
        background: {c['primary']};
        color: {c['text_inverse']};
    }}
    QPushButton[primary="true"]:hover {{
        background: {c['primary_dark']};
    }}
    
    /* 标签 */
    QLabel {{
        color: {c['text_primary']};
        font-size: {f['md']}px;
    }}
    
    /* 表格 */
    QTableWidget {{
        background: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: {r['lg']}px;
        font-size: {f['base']}px;
        gridline-color: {c['border_light']};
        alternate-background-color: {c['bg_primary']};
        selection-background-color: {c['primary_lighter']};
        selection-color: {c['text_primary']};
    }}
    QTableWidget::item {{
        padding: 8px 12px;
        border-bottom: 1px solid {c['border_light']};
    }}
    QTableWidget::item:hover {{
        background: {c['bg_active']};
    }}
    QTableWidget::item:selected {{
        background: {c['primary_lighter']};
        color: {c['text_primary']};
    }}
    
    /* 表头 */
    QHeaderView::section {{
        background: {c['bg_secondary']};
        color: {c['text_secondary']};
        font-weight: {Theme.FONT_WEIGHTS['semibold']};
        font-size: {f['sm']}px;
        border: none;
        border-bottom: 2px solid {c['border']};
        border-right: 1px solid {c['border_light']};
        padding: 10px 12px;
    }}
    QHeaderView::section:hover {{
        background: {c['bg_active']};
        color: {c['primary']};
    }}
    
    /* 下拉框 */
    QComboBox {{
        padding: 8px 12px;
        border: 1px solid {c['border']};
        border-radius: {r['md']}px;
        background: {c['bg_card']};
        color: {c['text_primary']};
        font-size: {f['base']}px;
        min-width: 100px;
    }}
    QComboBox:focus {{
        border-color: {c['primary']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}
    QComboBox QAbstractItemView {{
        background: {c['bg_card']};
        color: {c['text_primary']};
        selection-background-color: {c['primary_lighter']};
        selection-color: {c['primary']};
        border: 1px solid {c['border']};
        border-radius: {r['md']}px;
        outline: none;
        padding: 4px;
    }}
    
    /* 分组框 */
    QGroupBox {{
        font-size: {f['md']}px;
        font-weight: {Theme.FONT_WEIGHTS['semibold']};
        color: {c['primary']};
        border: 1px solid {c['border']};
        border-radius: {r['lg']}px;
        margin-top: 12px;
        padding: 20px 16px 16px;
        background-color: {c['bg_card']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 8px;
    }}
    
    /* 滚动区域 */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    
    /* 滚动条 */
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['text_muted']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['border']};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c['text_muted']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    
    /* 输入框 */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        padding: 8px 12px;
        border: 1px solid {c['border']};
        border-radius: {r['md']}px;
        background: {c['bg_card']};
        color: {c['text_primary']};
        font-size: {f['base']}px;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {c['primary']};
    }}
    
    /* 复选框和单选框 */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        font-size: {f['base']}px;
        color: {c['text_primary']};
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
    }}
    
    /* 进度条 */
    QProgressBar {{
        border: none;
        border-radius: {r['full']}px;
        background: {c['bg_secondary']};
        text-align: center;
        font-size: {f['xs']}px;
        color: {c['text_inverse']};
        height: 8px;
    }}
    QProgressBar::chunk {{
        background: {c['primary']};
        border-radius: {r['full']}px;
    }}
    
    /* 工具提示 */
    QToolTip {{
        background: {c['text_primary']};
        color: {c['text_inverse']};
        border: none;
        border-radius: {r['md']}px;
        padding: 8px 12px;
        font-size: {f['sm']}px;
    }}
    
    /* Tab页 */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        border-radius: {r['lg']}px;
        background: {c['bg_card']};
        margin-top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {c['text_secondary']};
        padding: 10px 20px;
        border: none;
        border-bottom: 2px solid transparent;
        font-size: {f['base']}px;
        font-weight: {Theme.FONT_WEIGHTS['medium']};
    }}
    QTabBar::tab:hover {{
        color: {c['primary']};
        background: {c['bg_active']};
    }}
    QTabBar::tab:selected {{
        color: {c['primary']};
        border-bottom-color: {c['primary']};
    }}
    """


def get_sidebar_style() -> str:
    """获取侧边栏样式"""
    c = Theme.COLORS
    f = Theme.FONT_SIZES
    
    return f"""
    QListWidget {{
        background: {c['bg_sidebar']};
        border: none;
        padding: 12px 8px;
        outline: none;
    }}
    QListWidget::item {{
        color: {c['text_sidebar']};
        padding: 14px 20px;
        font-size: {f['md']}px;
        font-weight: {Theme.FONT_WEIGHTS['medium']};
        border: none;
        border-radius: 8px;
        margin: 2px 4px;
    }}
    QListWidget::item:hover {{
        background: {c['bg_sidebar_hover']};
        color: {c['text_inverse']};
    }}
    QListWidget::item:selected {{
        background: {c['bg_sidebar_active']};
        color: {c['text_sidebar_active']};
        font-weight: {Theme.FONT_WEIGHTS['semibold']};
    }}
    """


def get_toggle_button_style() -> str:
    """获取切换按钮样式"""
    c = Theme.COLORS
    r = Theme.BORDER_RADIUS
    f = Theme.FONT_SIZES
    
    return f"""
    QPushButton {{
        background: {c['primary_lighter']};
        color: {c['primary']};
        padding: 6px 14px;
        border-radius: {r['md']}px;
        font-weight: {Theme.FONT_WEIGHTS['semibold']};
        font-size: {f['base']}px;
        border: 1px solid transparent;
    }}
    QPushButton:hover {{
        background: {c['primary_light']};
        border-color: {c['primary']};
    }}
    QPushButton:checked {{
        background: {c['primary']};
        color: {c['text_inverse']};
        border-color: {c['primary_dark']};
    }}
    """


def get_card_style(hover_color: str = None) -> str:
    """获取卡片样式"""
    c = Theme.COLORS
    r = Theme.BORDER_RADIUS
    hover = hover_color or c['primary']
    
    return f"""
    QFrame {{
        background: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: {r['lg']}px;
        padding: 16px;
    }}
    QFrame:hover {{
        border-color: {hover};
        box-shadow: 0 4px 12px {c['shadow_light']};
    }}
    """


def get_primary_button_style() -> str:
    """获取主要按钮样式"""
    c = Theme.COLORS
    r = Theme.BORDER_RADIUS
    f = Theme.FONT_SIZES
    
    return f"""
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c['primary']}, stop:1 {c['primary_dark']});
        color: {c['text_inverse']};
        padding: 10px 24px;
        border-radius: {r['md']}px;
        font-weight: {Theme.FONT_WEIGHTS['semibold']};
        font-size: {f['md']}px;
        border: none;
    }}
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c['primary_dark']}, stop:1 {c['primary_darker']});
    }}
    QPushButton:pressed {{
        background: {c['primary_darker']};
    }}
    QPushButton:disabled {{
        background: {c['border']};
        color: {c['text_muted']};
    }}
    """


def get_danger_button_style() -> str:
    """获取危险按钮样式"""
    c = Theme.COLORS
    r = Theme.BORDER_RADIUS
    f = Theme.FONT_SIZES
    
    return f"""
    QPushButton {{
        background: {c['danger']};
        color: {c['text_inverse']};
        padding: 10px 24px;
        border-radius: {r['md']}px;
        font-weight: {Theme.FONT_WEIGHTS['semibold']};
        font-size: {f['md']}px;
        border: none;
    }}
    QPushButton:hover {{
        background: {c['danger_dark']};
    }}
    QPushButton:pressed {{
        background: {c['danger_dark']};
    }}
    """


# KPI卡片配置
KPI_CONFIG = {
    "total": {
        "name": "总检测数",
        "icon": "total",
        "color": "primary",
        "bg_color": "primary_lighter",
    },
    "ok": {
        "name": "OK数",
        "icon": "ok",
        "color": "success",
        "bg_color": "success_lighter",
    },
    "ng": {
        "name": "NG数",
        "icon": "ng",
        "color": "danger",
        "bg_color": "danger_lighter",
    },
    "yield_rate": {
        "name": "良率",
        "icon": "yield",
        "color": "info",
        "bg_color": "info_lighter",
    },
    "review_ok": {
        "name": "复判OK",
        "icon": "review_ok",
        "color": "success",
        "bg_color": "success_lighter",
    },
    "review_ng": {
        "name": "复判NG",
        "icon": "review_ng",
        "color": "danger",
        "bg_color": "danger_lighter",
    },
    "post_review_yield_rate": {
        "name": "复判后良率",
        "icon": "yield",
        "color": "info",
        "bg_color": "info_lighter",
    },
}

# 趋势方向配置
TREND_CONFIG = {
    "up_good": {
        "arrow": "↑",
        "color": "success",
    },
    "up_bad": {
        "arrow": "↑",
        "color": "danger",
    },
    "down_good": {
        "arrow": "↓",
        "color": "success",
    },
    "down_bad": {
        "arrow": "↓",
        "color": "danger",
    },
    "neutral": {
        "arrow": "→",
        "color": "text_muted",
    },
}
