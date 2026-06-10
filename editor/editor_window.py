import os, uuid, copy
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QComboBox,
    QListWidget, QListWidgetItem, QLabel, QPushButton, QColorDialog,
    QMessageBox, QFileDialog, QInputDialog, QLineEdit, QFormLayout,
    QGroupBox, QDoubleSpinBox, QSpinBox, QCheckBox, QSplitter,
    QStatusBar, QToolButton, QApplication, QGraphicsItem,
)
from PyQt5.QtCore import Qt, QPointF, QSizeF, QSize, QRectF, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPainter, QPen, QFont
from utils.ui_utils import scale_css, sf, sp

from editor.product_layout import (
    Region, ShapeType, ProductLayoutModel, LayoutPersistence,
    RegionHierarchyManager, product_layout_path, LAYOUT_DIR,
)
from editor.layout_manager import ProductLayoutManager
from editor.region_items import (
    RegionItemBase, RectRegionItem, CircleRegionItem,
)
from editor.region_scene import RegionScene
from editor.region_view import RegionGraphicsView


ICON_COLORS = {
    "select": "#4F6CF7", "rect": "#EF4444", "circle": "#10B981",
    "polygon": "#EC4899",
}
TOOL_ICON_SHAPES = {
    "select": "select", "rect": "rect", "circle": "circle",
    "polygon": "polygon",
}

SHAPE_TYPE_MAP = {
    ShapeType.RECTANGLE: RectRegionItem,
    ShapeType.CIRCLE: CircleRegionItem,
}

TOOL_TO_SHAPE = {
    "rect": ShapeType.RECTANGLE, "circle": ShapeType.CIRCLE,
    "polygon": ShapeType.POLYGON,
}


def _make_icon(color: str, shape: str = "rect") -> QIcon:
    pix = QPixmap(24, 24)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(color)
    p.setPen(QPen(c, 2))
    if shape == "select":
        p.drawLine(6, 20, 18, 8)
        p.drawLine(18, 8, 12, 6)
        p.drawLine(18, 8, 20, 14)
    elif shape == "rect":
        p.drawRect(4, 4, 16, 16)
    elif shape == "circle":
        p.drawEllipse(4, 4, 16, 16)
    elif shape == "polygon":
        pts = [QPointF(12, 4), QPointF(20, 10), QPointF(16, 20), QPointF(8, 20), QPointF(4, 10)]
        p.drawPolygon(pts)
    elif shape in ("up", "down", "top", "bottom"):
        if shape == "up":
            p.drawLine(12, 20, 12, 4); p.drawLine(12, 4, 6, 10); p.drawLine(12, 4, 18, 10)
        elif shape == "down":
            p.drawLine(12, 4, 12, 20); p.drawLine(12, 20, 6, 14); p.drawLine(12, 20, 18, 14)
        elif shape == "top":
            p.drawLine(12, 20, 12, 4); p.drawLine(12, 4, 6, 10); p.drawLine(12, 4, 18, 10)
            p.drawLine(6, 22, 18, 22)
        elif shape == "bottom":
            p.drawLine(12, 4, 12, 20); p.drawLine(12, 20, 6, 14); p.drawLine(12, 20, 18, 14)
            p.drawLine(6, 2, 18, 2)
    p.end()
    return QIcon(pix)


class ProductLayoutEditorWindow(QDialog):
    sig_region_saved = pyqtSignal(str)

    def __init__(self, parent=None, default_size: QSizeF = None, initial_product: str = ""):
        super().__init__(parent)
        self.setWindowTitle("产品示意图编辑器")
        self.setMinimumSize(sp(1000), sp(700))
        self.resize(sp(1200), sp(800))

        self._regions: list[Region] = []
        self._default_size = default_size or QSizeF(1920, 1080)
        self._current_tool = "select"
        self._modified = False
        self._clipboard: Region = None
        self._layout_manager = ProductLayoutManager.instance()
        self._background_path = ""
        self._initial_product = initial_product

        pw, ph = self._default_size.width(), self._default_size.height()
        self._scene = RegionScene(self)
        self._scene.set_product_bounds(0, 0, pw, ph)
        self._scene.setSceneRect(-50, -50, pw + 100, ph + 100)
        self._view = RegionGraphicsView(self._scene, self)
        self._view.setup_focus()

        self._setup_ui()
        self._connect_signals()
        self._refresh_product_combo()

        self.setStyleSheet(self._style())

    def _connect_signals(self):
        self._scene.selectionChanged.connect(self._on_selection_changed)
        self._scene.deleteRequested.connect(self._delete_selected)
        self._scene.pasteRequested.connect(self._paste_region)
        self._view.drawRequested.connect(self._on_scene_clicked)

    def _style(self):
        return scale_css("""
        QDialog { background-color: #F8FAFC; }
        QToolButton { padding: 6px 10px; border-radius: 6px; color: #1E293B;
            font-size: 12px; font-weight: 600; }
        QToolButton:hover { background-color: #F1F5F9; }
        QToolButton:checked { background-color: #EEF2FF; color: #4F6CF7; }
        QPushButton { padding: 7px 16px; border: none; border-radius: 6px;
            font-size: 12px; font-weight: 600; }
        QComboBox { padding: 4px 8px; border: 1px solid #CBD5E1;
            border-radius: 4px; font-size: 13px; background: #FFFFFF;
            color: #1E293B; min-width: 160px; }
        QComboBox:focus { border-color: #4F6CF7; }
        QComboBox::drop-down { border: none; width: 24px; }
        QComboBox QAbstractItemView { background: #FFFFFF; color: #1E293B;
            selection-background-color: #EEF0FF; selection-color: #4F6CF7;
            border: 1px solid #CBD5E1; outline: none; }
        QListWidget { background: #FFFFFF; border: 1px solid #E2E8F0;
            border-radius: 6px; font-size: 12px; }
        QListWidget::item { padding: 6px 10px; border-radius: 4px; }
        QListWidget::item:selected { background-color: #EEF0FF; color: #4F6CF7; }
        QGroupBox { font-size: 12px; font-weight: 600; color: #4F6CF7;
            border: 1px solid #E2E8F0; border-radius: 8px; margin-top: 8px;
            padding: 12px 10px 8px; background-color: #FFFFFF; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
        QLabel { color: #1E293B; font-size: 12px; }
        QLineEdit, QDoubleSpinBox, QSpinBox { padding: 6px 8px;
            border: 1px solid #E2E8F0; border-radius: 4px;
            background: #F8FAFC; color: #1E293B; font-size: 12px; }
        QLineEdit:focus { border-color: #4F6CF7; background: #FFFFFF; }
        QStatusBar { background: #F1F5F9; color: #64748B; font-size: 11px; }
        """)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_toolbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._view)
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([750, 250])
        root.addWidget(splitter, 1)

        root.addWidget(self._build_bottom_bar())
        self._status_bar = QStatusBar()
        self._status_bar.showMessage("就绪")
        root.addWidget(self._status_bar)

    def _build_top_bar(self):
        bar = QWidget()
        bar.setStyleSheet("background: #FFFFFF; border-bottom: 1px solid #E2E8F0;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        layout.addWidget(QLabel("产品："))

        self._product_combo = QComboBox()
        self._product_combo.currentTextChanged.connect(self._on_product_changed)
        layout.addWidget(self._product_combo)

        for txt, tip, color, cb in [
            ("新建", "新建产品示意图", "#10B981", self._new_layout),
            ("加载", "加载已有布局文件", "#4F6CF7", self._load_layout_file),
            ("保存", "保存当前布局", "#F59E0B", self._save_only),
            ("另存为", "另存为新布局", "#8B5CF6", self._save_as),
            ("删除", "删除当前产品", "#EF4444", self._delete_layout),
        ]:
            btn = QPushButton(txt)
            btn.setAutoDefault(False)
            btn.setToolTip(tip)
            btn.setStyleSheet(f"QPushButton{{background:{color};color:white;padding:4px 12px;border-radius:4px;font-weight:600;}}"
                              f"QPushButton:hover{{background:{QColor(color).darker(110).name()};}}")
            btn.clicked.connect(cb)
            layout.addWidget(btn)

        btn_set_bg = QPushButton("背景图")
        btn_set_bg.setAutoDefault(False)
        btn_set_bg.setStyleSheet("QPushButton{background:#64748B;color:white;padding:4px 12px;border-radius:4px;font-weight:600;}"
                                 "QPushButton:hover{background:#475569;}")
        btn_set_bg.clicked.connect(self._set_background)
        layout.addWidget(btn_set_bg)

        layout.addStretch()
        return bar

    def _build_toolbar(self):
        bar = QWidget()
        bar.setStyleSheet("background: #FFFFFF; border-bottom: 1px solid #E2E8F0;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(3)

        self._tool_group = []
        tools = [
            ("select", "选择", "select"),
            ("rect", "矩形", "rect"),
            ("circle", "圆形", "circle"),
        ]
        for tid, txt, s in tools:
            btn = QToolButton()
            btn.setIcon(_make_icon(ICON_COLORS.get(tid, "#4F6CF7"), TOOL_ICON_SHAPES.get(tid, "rect")))
            btn.setText(txt)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setCheckable(True)
            btn.setChecked(tid == "select")
            btn.setProperty("tool_id", tid)
            btn.clicked.connect(lambda checked, t=tid: self._on_tool_selected(t))
            layout.addWidget(btn)
            self._tool_group.append(btn)

        sep = QWidget(); sep.setFixedWidth(1)
        sep.setStyleSheet("background: #E2E8F0;")
        layout.addWidget(sep)

        for tip, icon_shape, method in [
            ("置于顶层", "top", self._bring_to_front),
            ("上移一层", "up", self._bring_forward),
            ("下移一层", "down", self._send_backward),
            ("置于底层", "bottom", self._send_to_back),
        ]:
            btn = QToolButton()
            btn.setIcon(_make_icon("#4F6CF7", icon_shape))
            btn.setText(tip)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.clicked.connect(method)
            layout.addWidget(btn)

        btn_del = QToolButton()
        btn_del.setText("删除")
        btn_del.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        btn_del.clicked.connect(self._delete_selected)
        layout.addWidget(btn_del)

        layout.addStretch()

        btn_apply = QPushButton("应用到主界面")
        btn_apply.setAutoDefault(False)
        btn_apply.setStyleSheet("QPushButton{background:#4F6CF7;color:white;padding:6px 18px;border-radius:6px;font-weight:700;font-size:13px;}"
                                "QPushButton:hover{background:#3B5DE7;}")
        btn_apply.clicked.connect(self._apply_to_main)
        layout.addWidget(btn_apply)

        return bar

    def _build_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self._region_list = QListWidget()
        self._region_list.itemClicked.connect(self._on_list_item_clicked)
        layout.addWidget(QLabel("区域列表"))
        layout.addWidget(self._region_list, 1)

        prop_grp = QGroupBox("属性")
        pf = QFormLayout(prop_grp)
        pf.setSpacing(4)
        self._prop_name = QLineEdit()
        self._prop_name.editingFinished.connect(self._on_prop_name_done)
        self._prop_name.installEventFilter(self)
        pf.addRow("名称:", self._prop_name)
        self._prop_x = QDoubleSpinBox(); self._prop_x.setRange(-10000, 10000); self._prop_x.valueChanged.connect(self._on_prop_changed); pf.addRow("X:", self._prop_x)
        self._prop_y = QDoubleSpinBox(); self._prop_y.setRange(-10000, 10000); self._prop_y.valueChanged.connect(self._on_prop_changed); pf.addRow("Y:", self._prop_y)
        self._prop_w = QDoubleSpinBox(); self._prop_w.setRange(1, 10000); self._prop_w.valueChanged.connect(self._on_prop_changed); pf.addRow("宽度:", self._prop_w)
        self._prop_h = QDoubleSpinBox(); self._prop_h.setRange(1, 10000); self._prop_h.valueChanged.connect(self._on_prop_changed); pf.addRow("高度:", self._prop_h)
        self._prop_color_btn = QPushButton(); self._prop_color_btn.setAutoDefault(False); self._prop_color_btn.setFixedSize(32, 24)
        self._prop_color_btn.setStyleSheet("background: #00A0FF; border: 1px solid #CBD5E1; border-radius: 4px;")
        self._prop_color_btn.clicked.connect(self._pick_color); pf.addRow("颜色:", self._prop_color_btn)
        self._prop_z = QSpinBox(); self._prop_z.setRange(-100, 100); self._prop_z.valueChanged.connect(self._on_prop_changed); pf.addRow("层级:", self._prop_z)
        self._prop_visible = QCheckBox("可见"); self._prop_visible.setChecked(True); self._prop_visible.stateChanged.connect(self._on_prop_changed); pf.addRow(self._prop_visible)
        layout.addWidget(prop_grp)
        return panel

    def _build_bottom_bar(self):
        bar = QWidget()
        bar.setStyleSheet("background: #FFFFFF; border-top: 1px solid #E2E8F0;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)
        layout.addStretch()

        for txt, color, cb in [
            ("取消", "#EDF2F7", self._cancel),
            ("保存并关闭", "#4F6CF7", self._save_and_close),
        ]:
            btn = QPushButton(txt)
            btn.setAutoDefault(False)
            btn.setStyleSheet(f"QPushButton{{background:{color};color:{'white' if color != '#EDF2F7' else '#4A5568'};padding:7px 18px;border-radius:6px;font-weight:600;}}")
            btn.clicked.connect(cb)
            layout.addWidget(btn)
        return bar

    # ---- Product / Layout Management ----

    def _refresh_product_combo(self):
        self._product_combo.blockSignals(True)
        self._product_combo.clear()
        names = self._layout_manager.list_products()
        for n in names:
            self._product_combo.addItem(n)
        self._product_combo.blockSignals(False)

    def _on_product_changed(self, name: str):
        if not name:
            return
        layout = self._layout_manager.load_layout(name)
        if layout:
            self._load_layout(layout)

    def _load_layout(self, layout: ProductLayoutModel):
        self._regions = copy.deepcopy(layout.regions)
        self._background_path = layout.background_image
        cw, ch = layout.canvas_width, layout.canvas_height
        self._scene.set_product_bounds(0, 0, cw, ch)
        self._scene.setSceneRect(-50, -50, cw + 100, ch + 100)
        self._clear_scene()
        if self._background_path and os.path.exists(self._background_path):
            self._scene.set_background_image(self._background_path)
        self._load_regions_to_scene()
        self._rebuild_region_list()
        self._clear_property_panel()
        self._modified = False
        self._status_bar.showMessage(f"已加载: {layout.product_name} ({len(self._regions)}个区域)")
        QApplication.instance().processEvents()
        self._view.zoom_fit()

    def _new_layout(self):
        name, ok = QInputDialog.getText(self, "新建产品示意图", "产品名称：")
        if not ok or not name.strip():
            return
        name = name.strip()
        existing = self._layout_manager.list_products()
        if name in existing:
            QMessageBox.warning(self, "提示", f"产品 [{name}] 已存在")
            return
        layout = ProductLayoutModel(
            product_name=name,
            canvas_width=int(self._default_size.width()),
            canvas_height=int(self._default_size.height()),
        )
        ok = self._layout_manager.save_layout(layout)
        if not ok:
            QMessageBox.critical(self, "错误", "保存失败")
            return
        self._refresh_product_combo()
        idx = self._product_combo.findText(name)
        if idx >= 0:
            self._product_combo.setCurrentIndex(idx)
        self._load_layout(layout)
        self._status_bar.showMessage(f"已新建产品: {name}")

    def _load_layout_file(self):
        layouts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), LAYOUT_DIR)
        path, _ = QFileDialog.getOpenFileName(
            self, "加载布局文件", layouts_dir, "布局文件 (*.region.json *.json);;所有文件 (*)"
        )
        if not path:
            return
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            layout = ProductLayoutModel.from_dict(data)
            if not layout.product_name:
                base = os.path.splitext(os.path.basename(path))[0]
                layout.product_name = base
            ok = self._layout_manager.save_layout(layout)
            if not ok:
                QMessageBox.warning(self, "提示", "保存布局失败")
                return
            self._refresh_product_combo()
            idx = self._product_combo.findText(layout.product_name)
            if idx >= 0:
                self._product_combo.setCurrentIndex(idx)
            self._load_layout(layout)
            self._status_bar.showMessage(f"已加载: {path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载失败: {e}")

    def _set_background(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图", "", "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
        )
        if not path:
            return
        self._background_path = path
        self._scene.set_background_image(path)
        self._modified = True
        self._status_bar.showMessage(f"背景图: {os.path.basename(path)}")

    # ---- Save / SaveAs ----

    def _persist_current(self) -> bool:
        name = self._product_combo.currentText()
        if not name:
            return False
        self._sync_scene_to_data()
        pw = int(self._scene._product_bounds.width())
        ph = int(self._scene._product_bounds.height())
        layout = ProductLayoutModel(
            product_name=name,
            canvas_width=pw,
            canvas_height=ph,
            background_image=self._background_path,
            regions=self._regions,
        )
        return self._layout_manager.save_layout(layout)

    def _save_only(self):
        name = self._product_combo.currentText()
        if not name:
            QMessageBox.information(self, "提示", "请先选择或新建产品")
            return
        if self._persist_current():
            self._modified = False
            path = product_layout_path(name)
            self._status_bar.showMessage(f"已保存: {path}")
            self.sig_region_saved.emit(name)

    def _save_as(self):
        name, ok = QInputDialog.getText(self, "另存为", "新产品名称：")
        if not ok or not name.strip():
            return
        name = name.strip()
        existing = self._layout_manager.list_products()
        if name in existing:
            ret = QMessageBox.question(self, "确认", f"产品 [{name}] 已存在，是否覆盖？",
                                       QMessageBox.Yes | QMessageBox.No)
            if ret != QMessageBox.Yes:
                return
        self._sync_scene_to_data()
        pw = int(self._scene._product_bounds.width())
        ph = int(self._scene._product_bounds.height())
        layout = ProductLayoutModel(
            product_name=name,
            canvas_width=pw,
            canvas_height=ph,
            background_image=self._background_path,
            regions=self._regions,
        )
        ok = self._layout_manager.save_layout(layout)
        if ok:
            self._refresh_product_combo()
            idx = self._product_combo.findText(name)
            if idx >= 0:
                self._product_combo.setCurrentIndex(idx)
            self._modified = False
            self._status_bar.showMessage(f"已另存为: {name}")

    def _apply_to_main(self):
        name = self._product_combo.currentText()
        if not name:
            QMessageBox.information(self, "提示", "请先选择或新建产品")
            return
        if self._modified:
            ret = QMessageBox.question(self, "确认", "有未保存的修改，是否先保存？",
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if ret == QMessageBox.Cancel:
                return
            if ret == QMessageBox.Yes:
                self._persist_current()
                self._modified = False
                layout = self._layout_manager.current_layout
            else:
                self._sync_scene_to_data()
                layout = ProductLayoutModel(
                    product_name=name,
                    canvas_width=int(self._scene._product_bounds.width()),
                    canvas_height=int(self._scene._product_bounds.height()),
                    background_image=self._background_path,
                    regions=self._regions,
                )
        else:
            layout = self._layout_manager.current_layout
        if layout:
            self._layout_manager.apply_layout(layout)
            self._status_bar.showMessage(f"已应用到主界面: {name}")

    def _delete_layout(self):
        name = self._product_combo.currentText()
        if not name:
            QMessageBox.information(self, "提示", "请先选择要删除的产品")
            return
        ret = QMessageBox.question(self, "确认删除", f"确定要删除产品 [{name}] 及其所有区域配置吗？\n此操作不可撤销。",
                                   QMessageBox.Yes | QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        self._layout_manager.delete_layout(name)
        self._regions.clear()
        self._clear_scene()
        self._clear_property_panel()
        self._rebuild_region_list()
        self._refresh_product_combo()
        self._modified = False
        self._background_path = ""
        self._scene.set_background_image("")
        self._status_bar.showMessage(f"已删除: {name}")

    def _cancel(self):
        if self._modified:
            ret = QMessageBox.question(self, "确认", "有未保存的修改，确定放弃？",
                                       QMessageBox.Yes | QMessageBox.No)
            if ret != QMessageBox.Yes:
                return
        self.reject()

    def _save_and_close(self):
        name = self._product_combo.currentText()
        if not name:
            self.reject()
            return
        self._sync_scene_to_data()
        pw = int(self._scene._product_bounds.width())
        ph = int(self._scene._product_bounds.height())
        layout = ProductLayoutModel(
            product_name=name,
            canvas_width=pw,
            canvas_height=ph,
            background_image=self._background_path,
            regions=self._regions,
        )
        if self._layout_manager.save_layout(layout):
            self._layout_manager.apply_layout(layout)
            self.accept()

    # ---- Drawing Tools ----

    def _on_tool_selected(self, tool_id: str):
        self._current_tool = tool_id
        for btn in self._tool_group:
            btn.setChecked(btn.property("tool_id") == tool_id)
        if tool_id == "select":
            self._view.set_draw_mode(False)
            for item in self._scene.items():
                if isinstance(item, RegionItemBase):
                    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        else:
            self._view.set_draw_mode(True)
            for item in self._scene.items():
                if isinstance(item, RegionItemBase):
                    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self._status_bar.showMessage(f"点击画布开始绘制 {tool_id}")

    def _on_scene_clicked(self, pos: QPointF):
        if self._current_tool == "select":
            return
        shape_type = TOOL_TO_SHAPE.get(self._current_tool)
        if not shape_type:
            return
        b = self._scene._product_bounds
        sx = max(b.left(), min(b.right() - 120, pos.x()))
        sy = max(b.top(), min(b.bottom() - 90, pos.y()))
        region = Region(
            name=f"区域{len(self._regions) + 1}",
            shape_type=shape_type, x=sx, y=sy,
            width=120, height=90,
            border_radius=0,
            color="#00A0FF", z_order=len(self._regions),
        )
        self._regions.append(region)
        item_class = SHAPE_TYPE_MAP.get(shape_type)
        if not item_class:
            return
        item = item_class(region.id)
        item.setPos(region.x, region.y)
        item.m_width = region.width
        item.m_height = region.height
        item.m_color = QColor(region.color)
        item.m_name = region.name
        item.setZValue(region.z_order)
        item.set_bounds(self._scene._product_bounds)
        self._connect_item_signals(item)
        self._scene.addItem(item)
        self._rebuild_region_list()
        self._modified = True
        self._status_bar.showMessage(f"已创建: {region.name}")
        self._on_tool_selected("select")

    # ---- Selection & Properties ----

    def _on_selection_changed(self):
        selected = self._scene.selectedItems()
        if selected and isinstance(selected[0], RegionItemBase):
            self._update_property_panel(selected[0])
            self._highlight_list_item(selected[0].region_id)
        else:
            self._clear_property_panel()

    def eventFilter(self, obj, event):
        if obj is self._prop_name and event.type() == event.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self._on_prop_name_done()
                return True
        return super().eventFilter(obj, event)

    def _on_item_selected(self, region_id: str):
        item = self._scene.get_region_item_by_id(region_id)
        if item:
            self._scene.clearSelection()
            item.setSelected(True)

    def _connect_item_signals(self, item: RegionItemBase):
        item.region_selected.connect(self._on_item_selected)
        item.contextMenuAction.connect(self._on_context_menu_action)

    def _on_context_menu_action(self, region_id: str, action: str):
        if action == "delete":
            item = self._scene.get_region_item_by_id(region_id)
            if item:
                item.setSelected(True)
                self._delete_selected()
        elif action == "rename":
            item = self._scene.get_region_item_by_id(region_id)
            if item:
                item.setSelected(True)
                self._on_selection_changed()
                self._rename_region(region_id)
        elif action == "copy":
            self._copy_region(region_id)
        elif action == "paste":
            self._paste_region()
        elif action in ("bring_forward", "send_backward", "bring_to_front", "send_to_back"):
            item = self._scene.get_region_item_by_id(region_id)
            if item:
                item.setSelected(True)
                {
                    "bring_forward": self._bring_forward,
                    "send_backward": self._send_backward,
                    "bring_to_front": self._bring_to_front,
                    "send_to_back": self._send_to_back,
                }[action]()

    # ---- Property Panel ----

    def _update_property_panel(self, item: RegionItemBase):
        for w in (self._prop_name, self._prop_x, self._prop_y, self._prop_w, self._prop_h, self._prop_z, self._prop_visible):
            w.blockSignals(True)
        region = self._find_region(item.region_id)
        if region:
            self._prop_name.setText(region.name)
            self._prop_x.setValue(region.x)
            self._prop_y.setValue(region.y)
            self._prop_w.setValue(region.width)
            self._prop_h.setValue(region.height)
            self._prop_z.setValue(region.z_order)
            self._prop_visible.setChecked(region.visible)
            self._prop_color_btn.setStyleSheet(f"background: {region.color}; border: 1px solid #CBD5E1; border-radius: 4px;")
        for w in (self._prop_name, self._prop_x, self._prop_y, self._prop_w, self._prop_h, self._prop_z, self._prop_visible):
            w.blockSignals(False)

    def _clear_property_panel(self):
        for w in (self._prop_name, self._prop_x, self._prop_y, self._prop_w, self._prop_h, self._prop_z, self._prop_visible):
            w.blockSignals(True)
        self._prop_name.clear()
        self._prop_x.setValue(0)
        self._prop_y.setValue(0)
        self._prop_w.setValue(100)
        self._prop_h.setValue(100)
        self._prop_z.setValue(0)
        self._prop_visible.setChecked(True)
        for w in (self._prop_name, self._prop_x, self._prop_y, self._prop_w, self._prop_h, self._prop_z, self._prop_visible):
            w.blockSignals(False)

    def _on_prop_name_done(self):
        selected = self._scene.selectedItems()
        if not selected or not isinstance(selected[0], RegionItemBase):
            return
        region = self._find_region(selected[0].region_id)
        if not region:
            return
        region.name = self._prop_name.text().strip()
        selected[0].m_name = region.name
        selected[0].update()
        self._rebuild_region_list()
        self._modified = True

    def _on_prop_changed(self):
        selected = self._scene.selectedItems()
        if not selected or not isinstance(selected[0], RegionItemBase):
            return
        item = selected[0]
        region = self._find_region(item.region_id)
        if not region:
            return
        s = self.sender()
        if s == self._prop_x:
            region.x = self._prop_x.value(); item.setPos(region.x, region.y)
        elif s == self._prop_y:
            region.y = self._prop_y.value(); item.setPos(region.x, region.y)
        elif s == self._prop_w:
            region.width = self._prop_w.value(); item.m_width = region.width; item.update()
        elif s == self._prop_h:
            region.height = self._prop_h.value(); item.m_height = region.height; item.update()
        elif s == self._prop_z:
            region.z_order = self._prop_z.value(); item.setZValue(region.z_order)
        elif s == self._prop_visible:
            region.visible = self._prop_visible.isChecked(); item._hidden = not region.visible; item.update()
        self._modified = True

    def _pick_color(self):
        selected = self._scene.selectedItems()
        if not selected or not isinstance(selected[0], RegionItemBase):
            return
        item = selected[0]
        region = self._find_region(item.region_id)
        if not region:
            return
        color = QColorDialog.getColor(QColor(region.color), self, "选择颜色")
        if color.isValid():
            region.color = color.name()
            item.m_color = color
            self._prop_color_btn.setStyleSheet(f"background: {color.name()}; border: 1px solid #CBD5E1; border-radius: 4px;")
            item.update()
            self._modified = True

    def _find_region(self, region_id: str) -> Region:
        for r in self._regions:
            if r.id == region_id:
                return r
        return None

    def _rebuild_region_list(self):
        self._region_list.blockSignals(True)
        self._region_list.clear()
        for r in self._regions:
            item = QListWidgetItem(f"{r.name or r.id[:8]} ({r.shape_type.value})")
            item.setData(Qt.UserRole, r.id)
            item.setForeground(QColor("#1E293B") if r.visible else QColor("#CBD5E1"))
            self._region_list.addItem(item)
        self._region_list.blockSignals(False)

    def _highlight_list_item(self, region_id: str):
        for i in range(self._region_list.count()):
            item = self._region_list.item(i)
            if item.data(Qt.UserRole) == region_id:
                self._region_list.setCurrentItem(item)
                break

    def _on_list_item_clicked(self, list_item):
        region_id = list_item.data(Qt.UserRole)
        item = self._scene.get_region_item_by_id(region_id)
        if item:
            self._scene.clearSelection()
            item.setSelected(True)
            self._view.centerOn(item)

    # ---- Delete / Copy / Paste / Rename ----

    def _delete_selected(self):
        selected = self._scene.selectedItems()
        if not selected:
            return
        for item in selected:
            if isinstance(item, RegionItemBase):
                self._regions = [r for r in self._regions if r.id != item.region_id]
                self._scene.removeItem(item)
        self._rebuild_region_list()
        self._clear_property_panel()
        self._modified = True
        self._status_bar.showMessage("已删除选中区域")

    def _rename_region(self, region_id: str):
        region = self._find_region(region_id)
        if not region:
            return
        name, ok = QInputDialog.getText(self, "重命名", "区域名称:", text=region.name)
        if ok and name.strip():
            region.name = name.strip()
            item = self._scene.get_region_item_by_id(region_id)
            if item:
                self._update_property_panel(item)
            self._rebuild_region_list()
            self._modified = True

    def _copy_region(self, region_id: str):
        item = self._scene.get_region_item_by_id(region_id)
        region = self._find_region(region_id)
        if item and region:
            region.x = item.pos().x()
            region.y = item.pos().y()
            region.width = item.m_width
            region.height = item.m_height
            self._clipboard = copy.deepcopy(region)
            self._update_clipboard_state()

    def _update_clipboard_state(self):
        has = self._clipboard is not None
        for item in self._scene.items():
            if isinstance(item, RegionItemBase):
                item._clipboard_available = has
        self._scene._clipboard_available = has

    def _paste_region(self):
        if not self._clipboard:
            QMessageBox.information(self, "提示", "没有已复制的区域")
            return
        new_region = Region(
            name=self._clipboard.name + "_副本",
            shape_type=self._clipboard.shape_type,
            x=self._clipboard.x + 20, y=self._clipboard.y + 20,
            width=self._clipboard.width, height=self._clipboard.height,
            border_radius=self._clipboard.border_radius,
            color=self._clipboard.color, z_order=len(self._regions),
        )
        self._regions.append(new_region)
        item_class = SHAPE_TYPE_MAP.get(new_region.shape_type)
        if not item_class:
            return
        item = item_class(new_region.id)
        item.setPos(new_region.x, new_region.y)
        item.m_width = new_region.width
        item.m_height = new_region.height
        item.m_color = QColor(new_region.color)
        item.m_name = new_region.name
        item._hidden = not new_region.visible
        item.set_bounds(self._scene._product_bounds)
        self._connect_item_signals(item)
        self._scene.addItem(item)
        self._rebuild_region_list()
        self._modified = True
        self._status_bar.showMessage(f"已粘贴: {new_region.name}")

    # ---- Z-Order ----

    def _bring_forward(self):
        self._z_op(lambda m: m.bring_forward)

    def _send_backward(self):
        self._z_op(lambda m: m.send_backward)

    def _bring_to_front(self):
        self._z_op(lambda m: m.bring_to_front)

    def _send_to_back(self):
        self._z_op(lambda m: m.send_to_back)

    def _z_op(self, op_fn):
        selected = self._scene.selectedItems()
        if not selected or not isinstance(selected[0], RegionItemBase):
            return
        item = selected[0]
        region = self._find_region(item.region_id)
        if region:
            mgr = RegionHierarchyManager(self._regions)
            op_fn(mgr)(region)
            item.setZValue(region.z_order)
            self._prop_z.setValue(region.z_order)
            self._modified = True

    # ---- Utilities ----

    def _sync_scene_to_data(self):
        for item in self._scene.items():
            if isinstance(item, RegionItemBase):
                region = self._find_region(item.region_id)
                if region:
                    region.x = item.pos().x()
                    region.y = item.pos().y()
                    region.width = item.m_width
                    region.height = item.m_height

    def _load_regions_to_scene(self):
        for region in self._regions:
            item_class = SHAPE_TYPE_MAP.get(region.shape_type)
            if not item_class:
                continue
            item = item_class(region.id)
            item.setPos(region.x, region.y)
            item.m_width = region.width
            item.m_height = region.height
            item.m_color = QColor(region.color)
            item.m_name = region.name
            item.setZValue(region.z_order)
            item._hidden = not region.visible
            item.set_bounds(self._scene._product_bounds)
            self._connect_item_signals(item)
            self._scene.addItem(item)
        self._rebuild_region_list()

    def _clear_scene(self):
        for item in self._scene.items():
            if isinstance(item, RegionItemBase):
                self._scene.removeItem(item)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_product_combo()
        QApplication.instance().processEvents()
        target = self._initial_product or self._product_combo.currentText()
        if target:
            idx = self._product_combo.findText(target)
            if idx >= 0:
                self._product_combo.setCurrentIndex(idx)
            else:
                target = self._product_combo.currentText()
            if target:
                layout = self._layout_manager.load_layout(target)
                if layout:
                    self._load_layout(layout)
        self._view.zoom_fit()

    def get_product_name(self) -> str:
        return self._product_combo.currentText()

    def get_regions(self) -> list:
        self._sync_scene_to_data()
        return self._regions


RegionEditorWindow = ProductLayoutEditorWindow
