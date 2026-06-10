"""
加载状态组件
提供加载中、空数据、错误状态的统一显示
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
)
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, pyqtProperty, QSize
)
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient
from ui.theme import Theme


class SpinnerWidget(QWidget):
    """旋转加载动画组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(40, 40)
        self._color = QColor(Theme.get_color("primary"))
        self._line_width = 3
    
    def _rotate(self):
        """旋转动画"""
        self._angle = (self._angle + 10) % 360
        self.update()
    
    def start(self):
        """开始动画"""
        self._timer.start(30)
        self.show()
    
    def stop(self):
        """停止动画"""
        self._timer.stop()
        self.hide()
    
    def set_color(self, color: str):
        """设置颜色"""
        self._color = QColor(color)
    
    def set_line_width(self, width: int):
        """设置线宽"""
        self._line_width = width
    
    def paintEvent(self, event):
        """绘制旋转动画"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算中心点和半径
        center = self.rect().center()
        radius = min(self.width(), self.height()) / 2 - self._line_width
        
        # 设置画笔
        pen = QPen(self._color)
        pen.setWidth(self._line_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # 绘制背景圆（灰色）
        bg_color = QColor(self._color)
        bg_color.setAlpha(40)
        bg_pen = QPen(bg_color)
        bg_pen.setWidth(self._line_width)
        painter.setPen(bg_pen)
        painter.drawEllipse(center, radius, radius)
        
        # 绘制旋转弧线
        painter.setPen(pen)
        painter.drawArc(
            int(center.x() - radius),
            int(center.y() - radius),
            int(radius * 2),
            int(radius * 2),
            self._angle * 16,
            120 * 16  # 120度弧长
        )
        
        painter.end()


class LoadingOverlay(QWidget):
    """加载遮罩层"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.hide()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        
        # 旋转动画
        self._spinner = SpinnerWidget()
        layout.addWidget(self._spinner, 0, Qt.AlignCenter)
        
        # 加载文字
        self._text_label = QLabel("加载中...")
        self._text_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_secondary')};
                font-size: {Theme.get_font_size('md')}px;
                background: transparent;
            }}
        """)
        self._text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._text_label)
    
    def set_text(self, text: str):
        """设置加载文字"""
        self._text_label.setText(text)
    
    def showEvent(self, event):
        """显示时启动动画"""
        super().showEvent(event)
        self._spinner.start()
        # 设置半透明背景
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(255, 255, 255, 200))
        self.setPalette(palette)
    
    def hideEvent(self, event):
        """隐藏时停止动画"""
        super().hideEvent(event)
        self._spinner.stop()


class EmptyStateWidget(QWidget):
    """空数据状态组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        
        # 图标
        self._icon_label = QLabel("📭")
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 48px;
                background: transparent;
            }}
        """)
        layout.addWidget(self._icon_label)
        
        # 标题
        self._title_label = QLabel("暂无数据")
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_primary')};
                font-size: {Theme.get_font_size('lg')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                background: transparent;
            }}
        """)
        layout.addWidget(self._title_label)
        
        # 描述
        self._desc_label = QLabel("当前筛选条件下没有找到相关数据")
        self._desc_label.setAlignment(Qt.AlignCenter)
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_muted')};
                font-size: {Theme.get_font_size('base')}px;
                background: transparent;
                max-width: 300px;
            }}
        """)
        layout.addWidget(self._desc_label)
    
    def set_icon(self, icon: str):
        """设置图标"""
        self._icon_label.setText(icon)
    
    def set_title(self, title: str):
        """设置标题"""
        self._title_label.setText(title)
    
    def set_description(self, desc: str):
        """设置描述"""
        self._desc_label.setText(desc)


class ErrorStateWidget(QWidget):
    """错误状态组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        
        # 图标
        self._icon_label = QLabel("⚠️")
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 48px;
                background: transparent;
            }}
        """)
        layout.addWidget(self._icon_label)
        
        # 标题
        self._title_label = QLabel("加载失败")
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('danger')};
                font-size: {Theme.get_font_size('lg')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                background: transparent;
            }}
        """)
        layout.addWidget(self._title_label)
        
        # 错误信息
        self._error_label = QLabel("数据加载时发生错误")
        self._error_label.setAlignment(Qt.AlignCenter)
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(f"""
            QLabel {{
                color: {Theme.get_color('text_muted')};
                font-size: {Theme.get_font_size('base')}px;
                background: transparent;
                max-width: 300px;
            }}
        """)
        layout.addWidget(self._error_label)
        
        # 重试按钮
        self._retry_btn = QPushButton("重试")
        self._retry_btn.setCursor(Qt.PointingHandCursor)
        self._retry_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Theme.get_color('primary')};
                color: {Theme.get_color('text_inverse')};
                padding: 10px 24px;
                border-radius: {Theme.get_radius('md')}px;
                font-weight: {Theme.FONT_WEIGHTS['semibold']};
                font-size: {Theme.get_font_size('base')}px;
                border: none;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background: {Theme.get_color('primary_dark')};
            }}
        """)
        layout.addWidget(self._retry_btn, 0, Qt.AlignCenter)
    
    def set_error(self, message: str):
        """设置错误信息"""
        self._error_label.setText(message)
    
    def on_retry(self, callback):
        """设置重试回调"""
        self._retry_btn.clicked.connect(callback)


class StatusContainer(QWidget):
    """状态容器组件
    支持在正常内容、加载中、空数据、错误状态之间切换
    """
    
    class State:
        NORMAL = "normal"
        LOADING = "loading"
        EMPTY = "empty"
        ERROR = "error"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = self.State.NORMAL
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        # 正常内容容器
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addWidget(self._content_widget)
        
        # 加载状态
        self._loading_widget = LoadingOverlay(self)
        
        # 空数据状态
        self._empty_widget = EmptyStateWidget()
        self._empty_widget.hide()
        self._layout.addWidget(self._empty_widget)
        
        # 错误状态
        self._error_widget = ErrorStateWidget()
        self._error_widget.hide()
        self._layout.addWidget(self._error_widget)
    
    @property
    def content_layout(self):
        """获取内容布局"""
        return self._content_layout
    
    def set_state(self, state: str):
        """设置状态"""
        self._state = state
        
        # 隐藏所有状态
        self._content_widget.show()
        self._loading_widget.hide()
        self._empty_widget.hide()
        self._error_widget.hide()
        
        if state == self.State.LOADING:
            self._loading_widget.setGeometry(self.rect())
            self._loading_widget.show()
            self._loading_widget.raise_()
        elif state == self.State.EMPTY:
            self._content_widget.hide()
            self._empty_widget.show()
        elif state == self.State.ERROR:
            self._content_widget.hide()
            self._error_widget.show()
    
    def set_loading(self, text: str = "加载中..."):
        """设置为加载状态"""
        self._loading_widget.set_text(text)
        self.set_state(self.State.LOADING)
    
    def set_empty(self, title: str = "暂无数据", desc: str = "", icon: str = "📭"):
        """设置为空数据状态"""
        self._empty_widget.set_title(title)
        if desc:
            self._empty_widget.set_description(desc)
        self._empty_widget.set_icon(icon)
        self.set_state(self.State.EMPTY)
    
    def set_error(self, message: str = "数据加载失败"):
        """设置为错误状态"""
        self._error_widget.set_error(message)
        self.set_state(self.State.ERROR)
    
    def set_normal(self):
        """设置为正常状态"""
        self.set_state(self.State.NORMAL)
    
    def on_retry(self, callback):
        """设置重试回调"""
        self._error_widget.on_retry(callback)
    
    def resizeEvent(self, event):
        """调整大小时更新加载遮罩位置"""
        super().resizeEvent(event)
        if self._loading_widget.isVisible():
            self._loading_widget.setGeometry(self.rect())
