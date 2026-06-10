from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QSplitter, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QWidget, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSlot, QSize, QTimer
from PyQt5.QtGui import QPixmap, QPainter

from dashboard.core.dashboard_card import DashboardCard
from dashboard.core.drilldown_bus import BUS, DrillDownEvent
from services.image_service import ImageService


class ImageViewerCard(DashboardCard):
    card_id = "image_viewer"
    card_name = "图片查看器"

    def __init__(self, db_manager, parent=None):
        super().__init__(card_id=self.card_id, card_name=self.card_name, icon="🖼️", parent=parent)
        self.image_service = ImageService(db_manager)
        self.current_images = []
        self._days = 0
        self._start_date = None
        self._end_date = None
        self._build_ui()
        BUS.signal.connect(self._on_drilldown)
        self.name_list.itemClicked.connect(self._on_name_clicked)

    def set_time_range(self, days: int, start_date: str = None, end_date: str = None):
        self._days = days
        self._start_date = start_date
        self._end_date = end_date

    def _build_ui(self):
        layout = self.get_content_layout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.status_label = QLabel("当前筛选：无 | 图片数量：0")
        self.status_label.setStyleSheet("font-size: 12px; color: #606266; padding: 4px 0;")
        self.add_header_widget(self.status_label)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(3)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self.graphics_view = QGraphicsView()
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.graphics_view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        self.graphics_view.wheelEvent = self._zoom_on_wheel
        left_layout.addWidget(self.graphics_view, 1)

        info_panel = QWidget()
        info_panel.setStyleSheet("background: #F8FAFC; border-radius: 4px;")
        info_layout = QHBoxLayout(info_panel)
        info_layout.setContentsMargins(8, 4, 8, 4)
        info_layout.setSpacing(16)
        self.sn_label = QLabel("SN：-")
        self.defect_label = QLabel("缺陷：-")
        self.area_label = QLabel("区域：-")
        self.time_label = QLabel("时间：-")
        for lb in (self.sn_label, self.defect_label, self.area_label, self.time_label):
            lb.setStyleSheet("font-size: 11px; color: #475569; background: transparent;")
        info_layout.addWidget(self.sn_label)
        info_layout.addWidget(self.defect_label)
        info_layout.addWidget(self.area_label)
        info_layout.addStretch()
        info_layout.addWidget(self.time_label)
        left_layout.addWidget(info_panel)

        self.splitter.addWidget(left)

        self.name_list = QListWidget()
        self.name_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E2E8F0; border-radius: 4px;
                background: #FAFBFC; font-size: 11px; color: #1E293B;
            }
            QListWidget::item {
                padding: 6px 8px; border-bottom: 1px solid #F1F5F9;
            }
            QListWidget::item:hover { background: #EFF6FF; }
            QListWidget::item:selected {
                background: #DBEAFE; color: #1E293B;
            }
        """)
        self.splitter.addWidget(self.name_list)

        self.splitter.setSizes([800, 200])
        layout.addWidget(self.splitter, 1)

    def _zoom_on_wheel(self, event):
        factor = 1.15
        if event.angleDelta().y() > 0:
            self.graphics_view.scale(factor, factor)
        else:
            self.graphics_view.scale(1 / factor, 1 / factor)

    @pyqtSlot(DrillDownEvent)
    def _on_drilldown(self, event: DrillDownEvent):
        if event.filter_type == "Defect":
            if self._days >= 0:
                images = self.image_service.get_by_defect(event.value, self._days)
            else:
                images = self.image_service.get_by_defect_custom_date(event.value, self._start_date, self._end_date) if self._start_date else []
        elif event.filter_type == "Area":
            if self._days >= 0:
                images = self.image_service.get_by_area(event.value, self._days)
            else:
                images = self.image_service.get_by_area_custom_date(event.value, self._start_date, self._end_date) if self._start_date else []
        else:
            return
        self.current_images = images
        self._refresh_name_list()
        self.status_label.setText(
            f"当前筛选：{event.filter_type}={event.value} | 图片数量：{len(images)}"
        )
        self._flash_border()
        self._flash_status()
        if images:
            self._show_image(images[0])
            self.name_list.setCurrentRow(0)

    def _refresh_name_list(self):
        self.name_list.clear()
        for idx, img in enumerate(self.current_images, 1):
            sn = img.get("sn", "")
            defect = img.get("defect_name", "")
            text = f"{idx}. {sn}\n{defect}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, img)
            self.name_list.addItem(item)

    @pyqtSlot(QListWidgetItem)
    def _on_name_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if data:
            self._show_image(data)

    def _flash_border(self):
        self.setStyleSheet("""
            DashboardCard {
                border: 2px solid #3B82F6;
                border-radius: 8px;
                background-color: #FFFFFF;
            }
        """)
        QTimer.singleShot(400, self._restore_border)

    def _restore_border(self):
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

    def _flash_status(self):
        self.status_label.setStyleSheet(
            "font-size: 12px; color: #2563EB; font-weight: 600; padding: 4px 0;"
        )
        QTimer.singleShot(400, self._restore_status)

    def _restore_status(self):
        self.status_label.setStyleSheet(
            "font-size: 12px; color: #606266; padding: 4px 0;"
        )

    def _show_image(self, img_data: dict):
        self.scene.clear()
        path = img_data.get("image_path", "")
        pix = QPixmap(path)
        if pix.isNull():
            self.scene.addText("图片加载失败")
            return
        pix_item = QGraphicsPixmapItem(pix)
        self.scene.addItem(pix_item)
        self.graphics_view.fitInView(pix_item, Qt.KeepAspectRatio)
        self.sn_label.setText(f"SN：{img_data.get('sn', '-')}")
        self.defect_label.setText(f"缺陷：{img_data.get('defect_name', '-')}")
        self.area_label.setText(f"区域：{img_data.get('defect_area', '-')}")
        self.time_label.setText(f"时间：{img_data.get('time', '-')}")

    def refresh_data(self, data: dict = None):
        self.current_images = []
        self.name_list.clear()
        self.scene.clear()
        self.status_label.setText("当前筛选：无 | 图片数量：0")
