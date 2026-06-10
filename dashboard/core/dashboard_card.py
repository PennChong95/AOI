from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt5.QtCore import Qt


class DashboardCard(QFrame):
    """所有看板卡片的统一基类"""

    def __init__(self, card_id: str = "", card_name: str = "", icon: str = "", parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.card_name = card_name
        self._icon = icon
        self._title_label = None
        self._content_widget = None

        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("""
            DashboardCard {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background-color: #FFFFFF;
            }
            DashboardCard:hover {
                border-color: #3B82F6;
            }
        """)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(8, 6, 8, 8)
        self._main_layout.setSpacing(4)

        self._build_header()
        self._build_content()

    def _build_header(self):
        header = QWidget()
        header.setStyleSheet("background: transparent; border: none;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(4)

        title = self._icon + "  " + self.card_name if self._icon else self.card_name
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("""
            font-size: 13px; font-weight: 600; color: #1E293B;
            background: transparent; border: none;
        """)
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()

        self._main_layout.addWidget(header)

    def _build_content(self):
        """子类覆写：创建图表并放入 get_content_layout()"""
        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: transparent; border: none;")
        self._main_layout.addWidget(self._content_widget, 1)

    def get_content_layout(self):
        if self._content_widget is None:
            return None
        layout = self._content_widget.layout()
        if layout is None:
            layout = QVBoxLayout(self._content_widget)
            layout.setContentsMargins(0, 0, 0, 0)
        return layout

    def add_header_widget(self, widget):
        """在标题栏右侧追加控件"""
        header = self._main_layout.itemAt(0)
        if header and header.widget():
            hl = header.widget().layout()
            if hl:
                hl.addWidget(widget)

    def refresh_data(self, data: dict = None):
        raise NotImplementedError

    def set_data(self, *args, **kwargs):
        pass
