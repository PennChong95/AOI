import os
import cv2
import numpy as np
import pyqtgraph as pg
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox,
    QApplication, QDoubleSpinBox, QFrame, QSizePolicy,
    QListView, QGridLayout, QMenu, QAction, QDialog, QStackedWidget,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle,
)
from PyQt5.QtCore import Qt, QRectF, QEvent, QTimer, QSize, QSizeF
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QPen, QCursor
from database.manager import DBManager
from services.query_service import QueryService, DefectListItem, QueryResult, RESULT_LABELS
from services.review_service import ReviewService
from utils.config_manager import (
    ConfigManager, LogManager, role_display_name, UserManager,
    ROLE_ADMIN, ROLE_INSPECTOR, ROLE_OPERATOR,
)
from utils.image_utils import ImageUtils
from utils.ui_utils import scale_css, sf, sp
from review.thumbnail_panel import ThumbnailPanel, ThumbInfo
from review.product_view_widget import ProductViewWidget
from editor.product_layout import Region, ShapeType, ProductLayoutModel, LayoutPersistence, LegacyRegionPersistence
from editor.layout_manager import ProductLayoutManager
from editor.editor_window import RegionEditorWindow
from editor.region_matcher import RegionNameMatcher
from modes.settings import InteractionMode, RejudgeSettings
from modes.mode_switch import ModeSwitchManager
from database.models import (
    DefectDetailInfo, InspectionDetailEntity,
    FINAL_RESULT_OK, FINAL_RESULT_NG, REVIEW_OK,
)


class SchematicWrapper(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._view = ProductViewWidget(self)
        self._view.region_clicked.connect(self._on_schematic_clicked)
        self._view.region_hovered.connect(self._on_region_hovered)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

    def set_layout(self, layout: ProductLayoutModel):
        self._view.set_layout(layout)

    def set_regions(self, regions: list, canvas_width=1000, canvas_height=1000, product_name=""):
        self._view.set_regions(regions, canvas_width, canvas_height, product_name)

    def set_highlight_region(self, region_id: str):
        self._view.set_highlight_region(region_id)

    def set_ng_regions(self, region_ids: set):
        self._view.set_ng_regions(region_ids)

    def set_selected_region(self, region_id: str):
        self._view.set_selected_region(region_id)

    def clear_selected_region(self):
        self._view.clear_selected_region()

    def set_background_image(self, path: str):
        self._view.set_background_image(path)

    def _on_schematic_clicked(self, region_id: str):
        if self._mw and self._mw._mode_manager.current:
            self._mw._mode_manager.current.on_region_clicked(region_id)

    def _on_region_hovered(self, region_id: str):
        pass


class ReAuthDialog(QDialog):
    def __init__(self, username: str, role: str, parent=None):
        super().__init__(parent)
        self.username = username
        self.role = role
        self._authenticated = False
        self._reauth_mode = "fingerprint"
        self.setWindowTitle("身份验证")
        self.setFixedSize(400, 320)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel { color: #1E293B; font-size: 14px; }
            QLineEdit {
                padding: 12px 16px; border: 1px solid #E2E8F0;
                border-radius: 8px; background-color: #F8FAFC;
                color: #1E293B; font-size: 14px;
            }
            QLineEdit:focus { border-color: #4F6CF7; background-color: #ffffff; }
            QPushButton {
                padding: 12px 24px; border: none; border-radius: 8px;
                font-size: 14px; font-weight: 600;
            }
            QPushButton#btnFpReauth {
                background-color: #4F6CF7; color: white;
                min-height: 40px; font-size: 15px;
            }
            QPushButton#btnFpReauth:hover { background-color: #3B5DE7; }
            QPushButton#btnConfirm {
                background-color: #10B981; color: white;
            }
            QPushButton#btnConfirm:hover { background-color: #059669; }
            QPushButton#btnSwitchAuth {
                background-color: #EDF2F7; color: #4A5568;
            }
            QPushButton#btnSwitchAuth:hover { background-color: #E2E8F0; }
            QFrame#fpFrame {
                background-color: #F0F4FF;
                border: 2px dashed #4F6CF7;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        self._stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self._stack.addWidget(self._build_fingerprint_page())
        self._stack.addWidget(self._build_password_page())

        from utils.config_manager import UserManager, can_login_with_password
        user = UserManager.find_by_username(self.username)
        has_fp = bool(user and user.get("fingerprint_template", ""))
        can_pwd = can_login_with_password(self.role)

        if has_fp:
            self._reauth_mode = "fingerprint"
            self._stack.setCurrentIndex(0)
            self._start_fp_scan()
        elif can_pwd:
            self._reauth_mode = "password"
            self._stack.setCurrentIndex(1)
        else:
            self._reauth_mode = "password"
            self._stack.setCurrentIndex(1)
            self._fp_status.setText("未绑定指纹，请使用密码验证")

    def _build_fingerprint_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(12)

        msg = QLabel(f"用户 [{self.username}] 登录已超时\n请按压指纹重新验证")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg)

        fp_frame = QFrame()
        fp_frame.setObjectName("fpFrame")
        fp_layout = QVBoxLayout(fp_frame)
        fp_layout.setAlignment(Qt.AlignCenter)

        self._fp_prompt = QLabel("请按压手指到指纹采集器")
        self._fp_prompt.setAlignment(Qt.AlignCenter)
        self._fp_prompt.setStyleSheet("color: #4F6CF7; font-size: 14px; font-weight: 600;")
        fp_layout.addWidget(self._fp_prompt)

        self._fp_status = QLabel("等待指纹...")
        self._fp_status.setAlignment(Qt.AlignCenter)
        self._fp_status.setStyleSheet("color: #94A3B8; font-size: 12px;")
        fp_layout.addWidget(self._fp_status)

        layout.addWidget(fp_frame)

        self._fp_retry_btn = QPushButton("重新识别")
        self._fp_retry_btn.setObjectName("btnFpReauth")
        self._fp_retry_btn.clicked.connect(self._start_fp_scan)
        self._fp_retry_btn.setVisible(False)
        layout.addWidget(self._fp_retry_btn)

        from utils.config_manager import can_login_with_password
        if can_login_with_password(self.role):
            btn_switch = QPushButton("使用密码验证")
            btn_switch.setObjectName("btnSwitchAuth")
            btn_switch.clicked.connect(self._switch_to_password)
            layout.addWidget(btn_switch)

        return page

    def _build_password_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(12)

        msg = QLabel(f"用户 [{self.username}] 登录已超时，请重新验证身份")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg)

        self.input_pass = QLineEdit()
        self.input_pass.setPlaceholderText("请输入密码验证")
        self.input_pass.setEchoMode(QLineEdit.Password)
        self.input_pass.returnPressed.connect(self._verify_password)
        layout.addWidget(self.input_pass)

        self._pwd_status = QLabel("")
        self._pwd_status.setAlignment(Qt.AlignCenter)
        self._pwd_status.setStyleSheet("color: #EF4444; font-size: 12px;")
        layout.addWidget(self._pwd_status)

        btn_confirm = QPushButton("确认验证")
        btn_confirm.setObjectName("btnConfirm")
        btn_confirm.clicked.connect(self._verify_password)
        layout.addWidget(btn_confirm)

        from utils.config_manager import UserManager
        user = UserManager.find_by_username(self.username)
        has_fp = bool(user and user.get("fingerprint_template", ""))
        if has_fp:
            btn_switch = QPushButton("使用指纹验证")
            btn_switch.setObjectName("btnSwitchAuth")
            btn_switch.clicked.connect(self._switch_to_fp)
            layout.addWidget(btn_switch)

        return page

    def _switch_to_fp(self):
        self._stack.setCurrentIndex(0)
        self._start_fp_scan()

    def _start_fp_scan(self):
        self._fp_prompt.setText("请按压手指到指纹采集器")
        self._fp_status.setText("正在采集...")
        self._fp_retry_btn.setVisible(False)
        QApplication.processEvents()

        from services.fingerprint_service import fingerprint_service, ZKFP_ERR_OK
        from utils.config_manager import UserManager
        users = UserManager.load_users()
        ret = fingerprint_service.ensure_device_ready(users)
        if ret != ZKFP_ERR_OK:
            self._fp_status.setText("指纹设备未就绪")
            self._fp_retry_btn.setVisible(True)
            return

        self._fp_timer = QTimer(self)
        self._fp_timer.setSingleShot(True)
        self._fp_timer.timeout.connect(self._do_fp_capture)
        self._fp_timeout_count = 0
        self._fp_timer.start(300)

    def _do_fp_capture(self):
        from services.fingerprint_service import fingerprint_service, ZKFP_ERR_OK
        ret, template, image = fingerprint_service.acquire_fingerprint()
        if ret == ZKFP_ERR_OK and template:
            self._on_fp_captured(template)
        else:
            self._fp_timeout_count += 1
            if self._fp_timeout_count > 50:
                self._fp_status.setText("采集超时，请重试")
                self._fp_retry_btn.setVisible(True)
                return
            self._fp_timer.start(300)

    def _on_fp_captured(self, template: bytes):
        from services.fingerprint_service import fingerprint_service, ZKFP_ERR_OK
        from utils.config_manager import UserManager
        import base64

        self._fp_prompt.setText("验证中...")
        QApplication.processEvents()

        user = UserManager.find_by_username(self.username)
        if not user:
            self._fp_status.setText("用户不存在")
            self._fp_retry_btn.setVisible(True)
            return

        stored_b64 = user.get("fingerprint_template", "")
        if not stored_b64:
            self._fp_status.setText("未绑定指纹")
            self._fp_retry_btn.setVisible(True)
            return

        try:
            stored_tpl = base64.b64decode(stored_b64)
            score = fingerprint_service.db_match(template, stored_tpl)
            if score > 0:
                self._authenticated = True
                fingerprint_service.release_device()
                self.accept()
            else:
                self._fp_prompt.setText("指纹不匹配")
                self._fp_status.setText("请重试")
                self._fp_retry_btn.setVisible(True)
        except Exception:
            self._fp_status.setText("验证失败")
            self._fp_retry_btn.setVisible(True)

    def _verify_password(self):
        from utils.config_manager import UserManager
        password = self.input_pass.text().strip()
        if not password:
            self._pwd_status.setText("请输入密码")
            return
        user = UserManager.verify_login(self.username, password)
        if user:
            self._authenticated = True
            self.accept()
        else:
            self._pwd_status.setText("密码错误，请重试")

    def _switch_to_password(self):
        from services.fingerprint_service import fingerprint_service
        self._stop_fp_scan()
        fingerprint_service.release_device()
        self._stack.setCurrentIndex(1)

    def closeEvent(self, event):
        from services.fingerprint_service import fingerprint_service
        self._stop_fp_scan()
        fingerprint_service.release_device()
        super().closeEvent(event)

    def is_authenticated(self):
        return self._authenticated


class ElidedTextDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        if opt.text:
            fm = painter.fontMetrics()
            opt.text = fm.elidedText(opt.text, Qt.ElideRight, opt.rect.width() - 8)
        QApplication.style().drawControl(QStyle.CE_ItemViewItem, opt, painter)

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return base.expandedTo(QSize(100, base.height()))


class MainWindow(QMainWindow):
    def __init__(self, db_manager: DBManager, username: str, role: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.username = username
        self.role = role
        user_data = UserManager.find_by_username(username)
        self._can_review = user_data.get("can_review", role != ROLE_OPERATOR) if user_data else (role != ROLE_OPERATOR)
        self.query_service = QueryService(db_manager)
        self.review_service = ReviewService(db_manager)
        self.config = ConfigManager.load()
        history_months = int(self.config.get("history_query_months", 6))
        self.db_manager.set_history_query_months(history_months)
        qm = self.config.get("query_mode", "default")
        qd = int(self.config.get("quick_days", 0))
        qs = self.config.get("query_start_time", "")
        qe = self.config.get("query_end_time", "")
        if qm == "quick":
            now = datetime.now()
            if qd == 0:
                start = datetime(now.year, now.month, now.day, 0, 0, 0)
            elif qd == -1:
                start = datetime(now.year, now.month, 1, 0, 0, 0)
            else:
                d = now - timedelta(days=qd)
                start = datetime(d.year, d.month, d.day, 0, 0, 0)
            self.db_manager.set_query_time_range(qm, start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S"), qd)
        else:
            self.db_manager.set_query_time_range(qm, qs, qe, 0)

        self.current_defect: DefectDetailInfo = None
        self.current_item: DefectListItem = None
        self.image_paths: list = []
        self.current_image_idx: int = 0
        self.defect_items: list = []
        self.inspection_details = []
        self.station_details = []
        self._history_results = []
        self.image_sources = []
        self._raw_image = None
        self._roi_items = []
        self._nine_grid_items = []
        self._review_group = None

        self._product_regions: list[Region] = []
        self._current_source_name: str = ""
        self._all_query_results: list = []
        self._all_image_paths: list = []
        self._all_image_sources: list = []
        self._region_matcher = RegionNameMatcher()
        self._mode_settings = RejudgeSettings()
        self._mode_manager = ModeSwitchManager(self)

        self._timeout_minutes = int(self.config.get("session_timeout_minutes", 30))
        self._reauth_seconds = int(self.config.get("session_reauthenticate_seconds", 60))
        self._session_active = True
        self._reauth_timer = QTimer(self)
        self._reauth_timer.timeout.connect(self._on_session_timeout)

        self._logout_timer = QTimer(self)
        self._logout_timer.setSingleShot(True)
        self._logout_timer.timeout.connect(self._force_logout)

        self.setWindowTitle("检测结果复判系统")
        self.setMinimumSize(sp(1280), sp(800))
        self.resize(sp(1500), sp(900))
        self._style_sheet = self._build_style()
        self.setStyleSheet(self._style_sheet)
        self._setup_ui()
        self._scale_buttons()
        self._apply_role_permissions()

        mode_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "review_mode.json")
        if os.path.exists(mode_file):
            self._mode_settings = RejudgeSettings.load(mode_file)
            self._mode_manager.switch_mode(self._mode_settings.mode)

        self._layout_mgr = ProductLayoutManager.instance()
        self._layout_mgr.layoutApplied.connect(self._on_layout_applied)
        self._migrate_legacy_regions()

        role_display = role_display_name(role)
        self._show_status(f"当前用户: {username} ({role_display}) | 欢迎使用")
        self._reset_session_timer()

    def _migrate_legacy_regions(self):
        legacy_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "region.json")
        if os.path.exists(legacy_path):
            try:
                LegacyRegionPersistence.migrate_to_layouts(legacy_path)
                os.rename(legacy_path, legacy_path + ".bak")
                self._show_status("已迁移旧版 region.json 到 layouts/ 目录")
            except Exception as e:
                print(f"迁移失败: {e}")
        self._load_product_regions()

    def _on_layout_applied(self, layout):
        if layout:
            self._product_regions = layout.regions
            self._region_matcher.build_index(layout.regions)
            self._last_canvas_w = layout.canvas_width
            self._last_canvas_h = layout.canvas_height
            self.schematic.set_layout(layout)
            self.config["last_product_name"] = layout.product_name
            ConfigManager.save(self.config)
            self._show_status(f"布局已更新: {layout.product_name}")

    def _reset_session_timer(self):
        self._session_active = True
        self._reauth_timer.start(self._timeout_minutes * 60 * 1000)

    def _on_session_timeout(self):
        self._session_active = False
        dlg = ReAuthDialog(self.username, self.role, self)
        self._reauth_timer.stop()

        if self._logout_timer.isActive():
            self._logout_timer.stop()

        self._logout_timer.start(self._reauth_seconds * 1000)

        if dlg.exec_() == QDialog.Accepted and dlg.is_authenticated():
            self._logout_timer.stop()
            self._session_active = True
            LogManager.log_login(self.username, "reauth", True)
            self._show_status("身份验证成功，会话已续期")
            self._reauth_timer.start(self._timeout_minutes * 60 * 1000)
        else:
            pass

    def _force_logout(self):
        LogManager.log_logout(self.username)
        QMessageBox.information(self, "会话超时", "未在有效时间内完成验证，系统将自动退出")
        self.close()

    def _apply_role_permissions(self):
        can_review_by_role = self._can_review or self.role == ROLE_ADMIN

        if self._review_group:
            self._review_group.setVisible(can_review_by_role)

        self.btn_region_editor.setVisible(self.role == ROLE_ADMIN)
        self.btn_dashboard.setVisible(True)

        if self.role == ROLE_ADMIN:
            self.btn_ok.setVisible(True)
            self.btn_ng.setVisible(True)
        elif can_review_by_role:
            self.btn_ok.setVisible(True)
            self.btn_ng.setVisible(True)
        else:
            self.btn_ok.setVisible(False)
            self.btn_ng.setVisible(False)
            self.label_review_status.setText("只读模式 - 仅可查看数据")
            self.label_review_status.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 600; padding: 6px;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._scale_buttons()

    def _scale_buttons(self):
        if not hasattr(self, 'btn_ok'):
            return
        scale = max(sf(), self.width() / sp(1500))
        w = min(sp(96), int(sp(72) * scale))
        h = min(sp(42), int(sp(32) * scale))
        fs = min(sp(15), int(sp(13) * scale))
        self.btn_ok.setFixedSize(w, h)
        self.btn_ng.setFixedSize(w, h)
        f = self.btn_ok.font()
        f.setPointSize(fs)
        self.btn_ok.setFont(f)
        self.btn_ng.setFont(f)

    def _build_style(self):
        return scale_css("""
        QMainWindow { background-color: #F0F2F5; }
        QGroupBox {
            font-size: 13px; font-weight: 600; color: #4F6CF7;
            border: 1px solid #E2E8F0; border-radius: 8px;
            margin-top: 10px; padding: 14px 12px 10px;
            background-color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin; left: 12px; padding: 0 6px;
        }
        QLabel { color: #1E293B; font-size: 13px; }
        QLineEdit {
            padding: 9px 12px; border: 1px solid #E2E8F0;
            border-radius: 6px; background-color: #F8FAFC;
            color: #1E293B; font-size: 13px;
        }
        QLineEdit:focus { border-color: #4F6CF7; background-color: #ffffff; }
        QPushButton {
            padding: 8px 16px; border: none; border-radius: 6px;
            font-size: 13px; font-weight: 600;
        }
        QPushButton#btnSearch {
            background-color: #4F6CF7; color: white; min-width: 80px;
        }
        QPushButton#btnSearch:hover { background-color: #3B5DE7; }
        QPushButton#btnOk {
            background-color: #10B981; color: white;
            font-size: 13px; padding: 6px 10px;
        }
        QPushButton#btnOk:hover { background-color: #047857; }
        QPushButton#btnNg {
            background-color: #EF4444; color: white;
            font-size: 13px; padding: 6px 10px;
        }
        QPushButton#btnNg:hover { background-color: #7F1D1D; }
        QPushButton#btnPrev, QPushButton#btnNext {
            background-color: #EDF2F7; color: #4A5568; min-width: 50px;
        }
        QPushButton#btnPrev:hover, QPushButton#btnNext:hover { background-color: #E2E8F0; }
        QPushButton#btnSettings {
            background-color: #EDF2F7; color: #4A5568;
        }
        QPushButton#btnSettings:hover { background-color: #E2E8F0; }
        QListWidget {
            background-color: #ffffff; color: #1E293B;
            border: 1px solid #E2E8F0; border-radius: 6px;
            font-size: 13px; padding: 4px;
        }
        QListWidget::item {
            padding: 6px 10px; border-radius: 4px; margin: 1px 2px;
        }
        QListWidget::item:selected {
            background-color: #EEF0FF; color: #4F6CF7;
        }
        QListWidget::item:hover {
            background-color: #F8FAFC;
        }
        QScrollArea { border: none; background-color: #F8FAFC; }
        QFrame#resultFrame {
            border-radius: 10px; padding: 16px;
        }
        """)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(8)

        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(8)

        left_col = QVBoxLayout()
        left_col.setSpacing(2)
        left_col.addWidget(self._build_sn_group())
        left_col.addWidget(self._build_image_area(), 1)

        left_w = QWidget()
        left_w.setLayout(left_col)

        right_col = self._build_side_area()

        body.addWidget(left_w, 7)
        body.addWidget(right_col, 3)
        root.addLayout(body, 1)

    def _build_header(self):
        bar = QWidget()
        bar.setStyleSheet("background-color: #ffffff; border-radius: 8px; border-bottom: 1px solid #E2E8F0;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 6, 16, 6)

        title = QLabel("检测结果复判系统")
        title.setStyleSheet("color: #1E293B; font-size: 17px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(title)

        layout.addStretch()

        role_display = role_display_name(self.role)
        self.label_header_user = QLabel(f"用户: {self.username} ({role_display})")
        self.label_header_user.setStyleSheet("color: #64748B; font-size: 12px;")
        layout.addWidget(self.label_header_user)

        btn_switch = QPushButton("切换")
        btn_switch.setObjectName("btnSettings")
        btn_switch.clicked.connect(self._switch_user)
        layout.addWidget(btn_switch)

        self.btn_region_editor = QPushButton("产品示意图编辑")
        self.btn_region_editor.setObjectName("btnSettings")
        self.btn_region_editor.clicked.connect(self._open_region_editor)
        layout.addWidget(self.btn_region_editor)

        btn_settings = QPushButton("设置")
        btn_settings.setObjectName("btnSettings")
        btn_settings.clicked.connect(self._open_settings)
        layout.addWidget(btn_settings)

        self.btn_dashboard = QPushButton("质量看板")
        self.btn_dashboard.setObjectName("btnSettings")
        self.btn_dashboard.clicked.connect(self._open_dashboard)
        layout.addWidget(self.btn_dashboard)

        return bar

    def _build_image_area(self):
        panel = QWidget()
        outer = QHBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        left = QWidget()
        layout = QVBoxLayout(left)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        zoom_row = QHBoxLayout()
        zoom_row.setSpacing(4)
        zoom_btn_style = "QPushButton{background:#EDF2F7;color:#4A5568;padding:4px 10px;font-size:12px;border-radius:4px;}" \
                         "QPushButton:hover{background:#E2E8F0;}"

        zoom_row.addWidget(QLabel("框倍率:"))
        self.spin_scale = QDoubleSpinBox()
        self.spin_scale.setRange(0.5, 5.0)
        self.spin_scale.setSingleStep(0.1)
        self.spin_scale.setValue(float(self.config.get("defect_box_scale", 1.2)))
        self.spin_scale.valueChanged.connect(self._on_scale_changed)
        self.spin_scale.setFixedWidth(60)
        zoom_row.addWidget(self.spin_scale)

        self.btn_zoom_in = QPushButton("放大")
        self.btn_zoom_in.setStyleSheet(zoom_btn_style)
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        zoom_row.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("缩小")
        self.btn_zoom_out.setStyleSheet(zoom_btn_style)
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        zoom_row.addWidget(self.btn_zoom_out)

        self.btn_zoom_fit = QPushButton("适应窗口")
        self.btn_zoom_fit.setStyleSheet(zoom_btn_style)
        self.btn_zoom_fit.clicked.connect(self._zoom_fit)
        zoom_row.addWidget(self.btn_zoom_fit)

        self.btn_zoom_actual = QPushButton("实际大小")
        self.btn_zoom_actual.setStyleSheet(zoom_btn_style)
        self.btn_zoom_actual.clicked.connect(self._zoom_actual)
        zoom_row.addWidget(self.btn_zoom_actual)

        zoom_row.addStretch()
        layout.addLayout(zoom_row)

        self.image_viewer = pg.GraphicsLayoutWidget(self)
        self.image_viewer.setBackground((45, 45, 45))
        self.image_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.view = self.image_viewer.addViewBox()
        self.view.setAspectLocked(True)
        self.view.invertY(True)
        self.view.setMenuEnabled(False)
        self.view.setMouseEnabled(True, True)
        self.view.setRange(xRange=(0, 1), yRange=(0, 1), padding=0)

        self.image_item = pg.ImageItem()
        self.view.addItem(self.image_item)

        self.placeholder_text = pg.TextItem("请输入SN查询", color=(200, 200, 200), anchor=(0.5, 0.5))
        self.placeholder_text.setPos(0.5, 0.5)
        self.view.addItem(self.placeholder_text)

        self._crosshair_visible = False

        self.proxy = pg.SignalProxy(
            self.image_viewer.scene().sigMouseMoved,
            rateLimit=30,
            slot=self._mouse_moved
        )
        self.image_viewer.scene().sigMouseClicked.connect(self._on_viewer_clicked)

        layout.addWidget(self.image_viewer, 1)

        self.label_image_path = QLabel("")
        self.label_image_path.setStyleSheet(
            "color: #94A3B8; font-size: 12px; padding: 2px 8px;"
            "background-color: #F1F5F9; border-radius: 4px;"
        )
        self.label_image_path.setFixedHeight(24)
        layout.addWidget(self.label_image_path)

        outer.addWidget(left, 1)

        self.thumb_panel = ThumbnailPanel(self)
        self.thumb_panel.currentIndexChanged.connect(self._on_thumb_selected)
        outer.addWidget(self.thumb_panel)

        return panel

    def _build_side_area(self):
        panel = QWidget()
        panel.setMinimumWidth(380)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        result_grp = self._build_result_group()
        layout.addWidget(result_grp)

        detail_grp = self._build_detail_group()
        layout.addWidget(detail_grp)

        defect_grp = self._build_defect_group()
        layout.addWidget(defect_grp, 1)

        self._review_group = self._build_review_group()
        self._review_group.setVisible(self.role == ROLE_ADMIN or self.role == ROLE_INSPECTOR)
        layout.addWidget(self._review_group)

        return panel

    def _build_sn_group(self):
        grp = QGroupBox("SN 查询")
        grp.setStyleSheet("QGroupBox{font-size:12px;font-weight:600;color:#4F6CF7;padding-top:8px;margin-top:4px;}"
                          "QGroupBox::title{subcontrol-origin:margin;left:8px;padding:0 4px;}")
        layout = QVBoxLayout(grp)
        layout.setSpacing(2)
        layout.setContentsMargins(8, 14, 8, 6)

        row = QHBoxLayout()
        self.input_sn = QLineEdit()
        self.input_sn.setPlaceholderText("请输入产品序列号")
        self.input_sn.returnPressed.connect(self._on_search)
        row.addWidget(self.input_sn, 1)
        btn = QPushButton("查询")
        btn.setObjectName("btnSearch")
        btn.clicked.connect(self._on_search)
        row.addWidget(btn)
        layout.addLayout(row)

        info_grid = QGridLayout()
        info_grid.setSpacing(2)
        info_grid.setHorizontalSpacing(4)

        def add_pair(row, col, label):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #64748B; font-size: 11px;")
            info_grid.addWidget(lbl, row, col * 2)
            w = QLabel("--")
            w.setStyleSheet("color: #1E293B; font-weight: 600; font-size: 11px;")
            info_grid.addWidget(w, row, col * 2 + 1)
            col_lbl = col * 2
            col_val = col * 2 + 1
            info_grid.setColumnStretch(col_lbl, 0)
            info_grid.setColumnStretch(col_val, 1)
            return w

        self.label_sn = add_pair(0, 0, "SN:")
        self.label_model = add_pair(0, 1, "型号:")
        self.label_workorder = add_pair(0, 2, "工单:")

        self.label_line = add_pair(1, 0, "线体:")
        self.label_machine = add_pair(1, 1, "设备ID:")
        self.label_fix = add_pair(1, 2, "治具号:")

        self.label_hole = add_pair(2, 0, "穴位号:")
        self.label_pack = add_pair(2, 1, "Pack码:")
        self.label_create_time = add_pair(2, 2, "检测时间:")

        self.label_user = add_pair(3, 0, "操作员:")
        self.label_review_user = add_pair(3, 1, "复判人员:")

        layout.addLayout(info_grid)

        self._history_list = QListWidget()
        self._history_list.setMaximumHeight(100)
        self._history_list.setStyleSheet(
            "font-size: 11px; color: #475569; border: 1px solid #E2E8F0; border-radius: 4px;"
        )
        self._history_list.itemClicked.connect(self._on_history_clicked)
        self._history_list.setVisible(False)
        layout.addWidget(self._history_list)

        return grp

    def _build_result_group(self):
        grp = QGroupBox("检测结果", self)
        layout = QVBoxLayout(grp)
        layout.setAlignment(Qt.AlignCenter)

        self.result_display = QLabel("等待查询...")
        self.result_display.setFixedSize(220, 80)
        self.result_display.setAlignment(Qt.AlignCenter)
        self._set_result("WAIT")
        layout.addWidget(self.result_display)
        return grp

    def _set_result(self, status: str):
        styles = {
            "WAIT":    {"text": "等待查询...", "bg": "#F8FAFC", "fg": "#94A3B8", "size": 22},
            "OK":      {"text": "OK",           "bg": "#ECFDF5", "fg": "#059669", "size": 40},
            "NG":      {"text": "NG",           "bg": "#FEF2F2", "fg": "#DC2626", "size": 40},
            "PARTIAL": {"text": "检测未完全",   "bg": "#FFFBEB", "fg": "#D97706", "size": 20},
        }
        s = styles.get(status, styles["WAIT"])
        self.result_display.setText(s["text"])
        self.result_display.setStyleSheet(f"""
            QLabel {{
                background-color: {s["bg"]};
                color: {s["fg"]};
                border-radius: 14px;
                border: 1px solid rgba(0,0,0,0.06);
                font-size: {s["size"]}px;
                font-weight: 800;
            }}
        """)

    def _build_detail_group(self):
        grp = QGroupBox("缺陷详情")
        layout = QVBoxLayout(grp)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 14, 8, 6)

        TITLE_STYLE = "color: #64748B; font-size: 11px;"
        VALUE_STYLE = "color: #1E293B; font-size: 12px; font-weight: 600;"

        info_grid = QGridLayout()
        info_grid.setSpacing(2)

        def add_info(row, col, title, label_attr):
            lbl = QLabel(title)
            lbl.setStyleSheet(TITLE_STYLE)
            info_grid.addWidget(lbl, row, col * 2)
            w = QLabel("--")
            w.setStyleSheet(VALUE_STYLE)
            info_grid.addWidget(w, row, col * 2 + 1)
            setattr(self, label_attr, w)
            return w

        add_info(0, 0, "名称:", "label_defect_name")
        add_info(0, 1, "面积:", "label_defect_area")
        add_info(0, 2, "等级:", "label_defect_level")

        add_info(1, 0, "区域:", "label_defect_region")
        add_info(1, 1, "九宫格:", "label_defect_nine")
        self.label_target_title = QLabel("标准值:")
        self.label_target_title.setStyleSheet(TITLE_STYLE)
        self.label_defect_target = QLabel("--")
        self.label_defect_target.setStyleSheet(VALUE_STYLE)
        info_grid.addWidget(self.label_target_title, 1, 4)
        info_grid.addWidget(self.label_defect_target, 1, 5)
        self.label_value_title = QLabel("实测值:")
        self.label_value_title.setStyleSheet(TITLE_STYLE)
        self.label_defect_value = QLabel("--")
        self.label_defect_value.setStyleSheet(VALUE_STYLE)
        info_grid.addWidget(self.label_value_title, 1, 6)
        info_grid.addWidget(self.label_defect_value, 1, 7)

        layout.addLayout(info_grid)

        self.schematic = SchematicWrapper(self)
        layout.addWidget(self.schematic, 1)

        grp.setMinimumHeight(360)
        return grp

    def _build_defect_group(self):
        grp = QGroupBox("缺陷列表")
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(6, 10, 6, 6)

        self.defect_list = QListWidget()
        self.defect_list.setFlow(QListView.LeftToRight)
        self.defect_list.setWrapping(True)
        self.defect_list.setUniformItemSizes(True)
        self.defect_list.setSpacing(4)
        self.defect_list.setMovement(QListWidget.Static)
        self.defect_list.setViewMode(QListView.ListMode)
        self.defect_list.setItemDelegate(ElidedTextDelegate(self.defect_list))
        self.defect_list.currentRowChanged.connect(self._on_defect_selected)
        layout.addWidget(self.defect_list)

        return grp

    def _build_review_group(self):
        grp = QGroupBox("复判操作")
        layout = QVBoxLayout(grp)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(12)

        self.btn_ok = QPushButton("判定 OK")
        self.btn_ok.setObjectName("btnOk")
        self.btn_ok.clicked.connect(lambda: self._on_review("OK"))
        self.btn_ok.setEnabled(False)
        self.btn_ok.setMinimumSize(72, 32)
        top.addWidget(self.btn_ok)

        self.btn_ng = QPushButton("判定 NG")
        self.btn_ng.setObjectName("btnNg")
        self.btn_ng.clicked.connect(lambda: self._on_review("NG"))
        self.btn_ng.setEnabled(False)
        self.btn_ng.setMinimumSize(72, 32)
        top.addWidget(self.btn_ng)

        top.addSpacing(4)
        self.label_review_status = QLabel("")
        self.label_review_status.setStyleSheet("color: #64748B; font-size: 13px; font-weight: 600;")
        top.addWidget(self.label_review_status)
        top.addStretch()

        layout.addLayout(top)

        self.label_review_remark = QLabel("")
        self.label_review_remark.setStyleSheet("color: #6366F1; font-size: 12px; background-color: #EEF2FF; padding: 8px 12px; border-radius: 4px;")
        self.label_review_remark.setWordWrap(True)
        self.label_review_remark.setMinimumHeight(50)
        layout.addWidget(self.label_review_remark, 1)

        return grp

    def _on_search(self):
        sn = self.input_sn.text().strip()
        if not sn:
            QMessageBox.warning(self, "提示", "请输入SN")
            return

        self._clear_display()

        import time as _time
        _t0 = _time.perf_counter()
        _step_t0 = _t0

        def _progress(step, detail):
            nonlocal _step_t0
            now = _time.perf_counter()
            step_cost = now - _step_t0
            _step_t0 = now
            total = now - _t0
            self._show_status(f"[{total:.1f}s] {step}: {detail} ({step_cost:.1f}s)")
            QApplication.processEvents()

        _progress("开始", f"SN={sn}")
        try:
            all_results = self.query_service.query_all_sources(sn, progress_callback=_progress)
        except Exception as e:
            self._show_status(f"查询失败: {e}")
            QMessageBox.critical(self, "错误", f"查询失败: {e}")
            return

        if not all_results:
            self._show_status(f"未找到SN [{sn}] 的检测记录")
            QMessageBox.information(self, "查询结果", f"未找到SN [{sn}] 的检测记录")
            return

        self._all_query_results = all_results

        def _load_single_result(result):
            self._current_source_name = result.source_name
            self.inspection_details = result.inspection_details
            self.station_details = result.station_details
            self.defect_items = result.defect_items
            for item in self.defect_items:
                item.source_name = result.source_name
            sr = result.station_result

            self.label_sn.setText(sr.Sn)
            self.label_model.setText(sr.ProductType or "--")
            self.label_workorder.setText(sr.WorkOrder or "--")
            self.label_line.setText(sr.Line or "--")
            self.label_machine.setText(sr.MachineId or "--")
            self.label_fix.setText(sr.FixNo or "--")
            self.label_hole.setText(sr.HoleNo or "--")
            self.label_pack.setText(sr.PackCode or "--")
            self.label_create_time.setText(str(sr.CreateTime or "") or "--")
            self.label_user.setText(sr.User or "--")
            self.label_review_user.setText(sr.ReviewUser or "--")

            result_str = {0: "待检", 1: "OK", 2: "NG"}.get(sr.FinalResult, "UNKNOWN")
            if sr.FinalResult == FINAL_RESULT_OK:
                self._set_result("OK")
                self.defect_list.clear()
                if self._can_review or self.role == ROLE_ADMIN:
                    self.btn_ok.setEnabled(True)
                    self.btn_ng.setEnabled(True)
                self._update_review_status(sr)
            elif sr.FinalResult == FINAL_RESULT_NG:
                self._set_result("NG")
                if self._can_review or self.role == ROLE_ADMIN:
                    self.btn_ok.setEnabled(True)
                    self.btn_ng.setEnabled(True)
                self._update_review_status(sr)
            else:
                self._set_result("PARTIAL")
                self.result_display.setToolTip("当前产品还未完成所有工站的检测，暂无总结果")
                if self._can_review or self.role == ROLE_ADMIN:
                    self.btn_ok.setEnabled(True)
                    self.btn_ng.setEnabled(True)

            self._load_image_list()

            if not self._product_regions:
                self._load_product_regions()

            _total_cost = _time.perf_counter() - _t0
            status = f"[{result.source_name}] 查询完成: SN={sn}, 结果={result_str}, 缺陷={len(self.defect_items)}个, 图片={len(self.image_paths)}张, 耗时={_total_cost:.1f}s"
            LogManager.log_operation(self.username, "查询SN", f"SN={sn}, 来源={result.source_name}, 结果={result_str}")
            self._show_status(status)

        _load_single_result(all_results[0])

        if self._mode_manager.current and self._mode_manager.current.mode_name() == "region_first":
            self.schematic.set_highlight_region("")
            self.schematic.clear_selected_region()
            self._update_ng_regions(show_all=True)
        else:
            self._update_ng_regions()

        if len(all_results) > 1:
            labels = ", ".join(f"[{r.source_name}] {r.station_result.FinalResult if r.station_result else '--'}" for r in all_results)
            self._show_status(f"多源查询: SN={sn} | 当前: [{all_results[0].source_name}] | 共{len(all_results)}个来源: {labels}")

        self._history_results = self.query_service.query_results_history(sn)
        self._populate_history_list(self._history_results, all_results[0].sr_id if all_results[0].station_result else 0)

    def _populate_history_list(self, history: list, current_id: int):
        self._history_list.clear()
        if len(history) <= 1:
            self._history_list.setVisible(False)
            return
        for h in history:
            src = h.get("source_name", "")
            src_tag = f"[{src}] " if src else ""
            text = f"{src_tag}[{h['Result']}]  {h['CreateTime'][:19] if h['CreateTime'] else '--'}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, h["Id"])
            item.setData(Qt.UserRole + 1, src)
            if h["Id"] == current_id:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#4F6CF7"))
            self._history_list.addItem(item)
        self._history_list.setVisible(True)

    def _on_history_clicked(self, item):
        result_id = item.data(Qt.UserRole)
        source_name = item.data(Qt.UserRole + 1) or ""
        if not result_id:
            return
        self._show_status(f"正在加载历史记录 ID={result_id} 来源=[{source_name}]...")
        try:
            self.station_details = self.db_manager.query_station_details(result_id, source_name)
            insp_list = self.db_manager.query_inspection_details(result_id, source_name)
            if insp_list:
                self.inspection_details = insp_list
                self.defect_items = self.query_service._build_defect_list(insp_list) if insp_list else []
                for di in self.defect_items:
                    di.source_name = source_name
            self._current_source_name = source_name
        except Exception as e:
            self._show_status(f"加载历史失败: {e}")
            return

        sr = self.db_manager.get_connection(source_name).query_station_result_by_id(result_id) if source_name else None
        if not sr:
            sr = self.db_manager.get_first_connected().query_station_result_by_id(result_id) if self.db_manager.get_first_connected() else None
        if sr:
            self.label_sn.setText(sr.Sn)
            self.label_model.setText(sr.ProductType or "--")
            self.label_workorder.setText(sr.WorkOrder or "--")
            self.label_line.setText(sr.Line or "--")
            self.label_machine.setText(sr.MachineId or "--")
            self.label_fix.setText(sr.FixNo or "--")
            self.label_hole.setText(sr.HoleNo or "--")
            self.label_pack.setText(sr.PackCode or "--")
            self.label_create_time.setText(str(sr.CreateTime or "") or "--")
            self.label_user.setText(sr.User or "--")
            self.label_review_user.setText(sr.ReviewUser or "--")

            result_str = RESULT_LABELS.get(sr.FinalResult, "--")
            if sr.FinalResult == FINAL_RESULT_OK:
                self._set_result("OK")
                self.defect_list.clear()
            elif sr.FinalResult == FINAL_RESULT_NG:
                self._set_result("NG")
            else:
                self._set_result("PARTIAL")

            can_review = self._can_review or self.role == ROLE_ADMIN
            self.btn_ok.setEnabled(can_review)
            self.btn_ng.setEnabled(can_review)
            self._update_review_status(sr)

        self._load_image_list()
        if self._mode_manager.current and self._mode_manager.current.mode_name() == "region_first":
            self.schematic.set_highlight_region("")
            self.schematic.clear_selected_region()
            self._update_ng_regions(show_all=True)
        else:
            self._update_ng_regions()

        count = len(self.defect_items)
        self._populate_defect_list(subset=None, auto_select=True)
        self._show_status(f"历史加载完成: ID={result_id}, 缺陷={count}个, 图片={len(self.image_paths)}张")

    def _populate_defect_list(self, subset=None, auto_select=True):
        if subset is None:
            subset = self.defect_items
        self.defect_list.blockSignals(True)
        self.defect_list.clear()
        for item in subset:
            li = QListWidgetItem(item.display_name)
            li.setData(Qt.UserRole, self.defect_items.index(item))
            self.defect_list.addItem(li)
        self.defect_list.blockSignals(False)
        if subset and auto_select:
            self.defect_list.setCurrentRow(0)

    def _on_defect_selected(self, row: int):
        if row < 0 or row >= self.defect_list.count():
            return
        li = self.defect_list.item(row)
        full_idx = li.data(Qt.UserRole)
        if full_idx is None or full_idx >= len(self.defect_items):
            return
        item = self.defect_items[full_idx]

        self._show_defect_detail(item)

        target_idx = 0
        for i, sources in enumerate(self.image_sources):
            if item.insp_index in sources:
                target_idx = i
                break

        if target_idx != self.current_image_idx:
            self.current_image_idx = target_idx
            self._sync_defect_list_to_current_image()
            for r in range(self.defect_list.count()):
                li = self.defect_list.item(r)
                if li and li.data(Qt.UserRole) == full_idx:
                    self.defect_list.blockSignals(True)
                    self.defect_list.setCurrentRow(r)
                    self.defect_list.blockSignals(False)
                    break
            self._show_defect_detail(item)
        self.thumb_panel.set_current_index(self.current_image_idx)
        self._refresh_image()

    def _show_defect_detail(self, item):
        self.current_item = item
        if not self.inspection_details:
            return

        is_meas = item.source_type == "measurement"

        dd = self.query_service.get_defect_detail(item, self.inspection_details)
        if dd:
            self.current_defect = dd
            self.label_defect_name.setText(dd.DefectName or "--")
            self.label_defect_area.setText(f"{dd.AreaSize:.0f}" if dd.AreaSize else "--")
            self.label_defect_level.setText(dd.Level or "--")
            self.label_defect_region.setText(dd.ProductArea or "--")
            nine = str(dd.NineGridArea) if dd.NineGridArea != "0" else "--"
            self.label_defect_nine.setText(nine)

            # Highlight region on product schematic by matching ProductArea to region name
            if self._product_regions:
                pa = (dd.ProductArea or "").strip()
                matched = ""
                for r in self._product_regions:
                    if r.name and pa and r.name == pa:
                        matched = r.id
                        break
                if matched:
                    self.schematic.set_highlight_region(matched)
            show_all_ng = self._mode_manager.current and self._mode_manager.current.mode_name() == "region_first"
            self._update_ng_regions(show_all=show_all_ng)
        else:
            self.current_defect = None
            self.label_defect_name.setText(item.display_name)
            self.label_defect_area.setText("--")
            self.label_defect_level.setText("--")
            self.label_defect_region.setText("--")
            self.label_defect_nine.setText("--")
            self.schematic.set_highlight_region("")
            show_all_ng = self._mode_manager.current and self._mode_manager.current.mode_name() == "region_first"
            self._update_ng_regions(show_all=show_all_ng)
        self.label_target_title.setVisible(is_meas)
        self.label_defect_target.setVisible(is_meas)
        self.label_value_title.setVisible(is_meas)
        self.label_defect_value.setVisible(is_meas)

        if is_meas and item.insp_index < len(self.inspection_details):
            insp = self.inspection_details[item.insp_index]
            if item.source_index < len(insp.Measurements):
                m = insp.Measurements[item.source_index]
                self.label_defect_target.setText(m.MeasureTarget or "--")
                self.label_defect_value.setText(m.MeasureValue or "--")

        show_box = self.config.get("show_defect_box", True)
        self._clear_rois()
        if show_box:
            self._draw_defect_bounding_box()
            self._draw_nine_grid_overlay()

    def _load_image_list(self):
        self.image_paths = []
        self.image_sources = []
        self._all_image_paths = []
        self._all_image_sources = []
        seen_paths = set()
        for idx, insp in enumerate(self.inspection_details):
            path = insp.SingleImagePath
            if not path:
                continue
            key = os.path.normpath(path).lower()
            if key not in seen_paths:
                seen_paths.add(key)
                self._all_image_paths.append(path)
                self._all_image_sources.append({idx})
        if not self._all_image_paths:
            for item in self.defect_items:
                dd = self.query_service.get_defect_detail(item, self.inspection_details)
                if dd and dd.DefectImagePath:
                    url = dd.DefectImagePath
                    key = os.path.normpath(url).lower()
                    if key not in seen_paths:
                        seen_paths.add(key)
                        self._all_image_paths.append(url)
                        self._all_image_sources.append({item.insp_index})
        if not self._all_image_paths:
            for sd in self.station_details:
                urls = sd.AllImageUrls if hasattr(sd, 'AllImageUrls') else []
                if isinstance(urls, list):
                    for url in urls:
                        if url:
                            key = os.path.normpath(str(url)).lower()
                            if key not in seen_paths:
                                seen_paths.add(key)
                                self._all_image_paths.append(str(url))
                                self._all_image_sources.append(set(range(len(self.inspection_details))))
        if self.inspection_details and not self._all_image_paths:
            d = self.inspection_details[0]
            self._show_status(f"无图片: StationNo={d.StationNo}, Result={d.Result}")
        self._apply_image_filter()

    def _apply_image_filter(self):
        failed_only = not self.config.get("show_ok_images", False)
        if failed_only:
            failed_indices = {i for i, d in enumerate(self.inspection_details)
                              if d.Result == FINAL_RESULT_NG}
            self.image_paths = []
            self.image_sources = []
            seen = {}
            for i, url in enumerate(self._all_image_paths):
                sources = self._all_image_sources[i]
                if sources & failed_indices:
                    key = os.path.normpath(url).lower()
                    if key not in seen:
                        seen[key] = len(self.image_paths)
                        self.image_paths.append(url)
                        self.image_sources.append(sources & failed_indices)
                    else:
                        self.image_sources[seen[key]] |= (sources & failed_indices)
        else:
            self.image_paths = list(self._all_image_paths)
            self.image_sources = [set(s) for s in self._all_image_sources]
        self.current_image_idx = 0 if self.image_paths else 0
        LogManager.add_log(LogManager.SYSTEM_LOG, self.username,
            f"ApplyImageFilter: failed_only=True, all={len(self._all_image_paths)}, filtered={len(self.image_paths)}")
        self._rebuild_thumbnails()
        self._sync_defect_list_to_current_image()
        self._refresh_image()

    def _sync_defect_list_to_current_image(self):
        if self.image_sources and 0 <= self.current_image_idx < len(self.image_sources):
            insp_indices = self.image_sources[self.current_image_idx]
            subset = [item for item in self.defect_items if item.insp_index in insp_indices]
        else:
            subset = self.defect_items
        self.current_defect = None
        self.current_item = None
        self._populate_defect_list(subset, auto_select=False)
        if subset:
            self.defect_list.blockSignals(True)
            self.defect_list.setCurrentRow(0)
            self.defect_list.blockSignals(False)
            self._show_defect_detail(subset[0])

    def _show_placeholder(self, text: str):
        self.placeholder_text.setText(text)
        self.placeholder_text.setVisible(True)

    def _refresh_image(self):
        if self.current_image_idx >= len(self.image_paths):
            self.image_item.clear()
            self._show_placeholder("无图片")
            return
        path = self.image_paths[self.current_image_idx]
        if not os.path.exists(path):
            self.image_item.clear()
            self._show_placeholder(f"文件不存在:\n{path}")
            self.label_image_path.setText(path)
            return
        try:
            img = ImageUtils.load_image(path)
            self._display_image(img)
            self.label_image_path.setText(path)
        except Exception as e:
            self.image_item.clear()
            self._show_placeholder(f"加载失败: {e}")
            self.label_image_path.setText(path)

    def _display_image(self, img):
        self._raw_image = img
        self.placeholder_text.setVisible(False)
        if len(img.shape) == 3:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        else:
            rgb = img
        self.image_item.setImage(rgb, autoLevels=True)
        h, w = img.shape[:2]
        self.image_item.setRect(QRectF(0, 0, w, h))
        self.view.setRange(xRange=(0, w), yRange=(0, h), padding=0)
        self._draw_defect_bounding_box()
        self._draw_nine_grid_overlay()
        QApplication.instance().processEvents()

    def _clear_rois(self):
        for item in self._roi_items:
            self.view.removeItem(item)
        self._roi_items.clear()
        for item in self._nine_grid_items:
            self.view.removeItem(item)
        self._nine_grid_items.clear()

    def _draw_defect_bounding_box(self):
        scale = self.spin_scale.value()
        if not self.current_defect:
            return
        box = self.current_defect.BoundingRect
        if not box or box.Width == 0 or box.Height == 0:
            return
        cx = box.X + box.Width / 2.0
        cy = box.Y + box.Height / 2.0
        scaled_w = box.Width * scale
        scaled_h = box.Height * scale
        x = cx - scaled_w / 2.0
        y = cy - scaled_h / 2.0
        color = self.config.get("defect_box_color", "#00FF00")
        lw = int(self.config.get("defect_line_width", 2))
        roi = pg.RectROI(
            [x, y], [scaled_w, scaled_h],
            movable=False, resizable=False,
            pen=pg.mkPen(color, width=lw),
        )
        self.view.addItem(roi)
        self._roi_items.append(roi)

    def _draw_nine_grid_overlay(self):
        if not self.current_defect:
            return
        iw = self.current_defect.ImageWidth
        ih = self.current_defect.ImageHeight
        if iw <= 0 or ih <= 0:
            if self.current_item and self.current_item.insp_index < len(self.inspection_details):
                insp = self.inspection_details[self.current_item.insp_index]
                iw = insp.ImageWidth
                ih = insp.ImageHeight
        if iw <= 0 or ih <= 0:
            return
        nine = self.current_defect.NineGridArea
        if nine == "0" or not nine:
            return
        cell_w = iw / 3.0
        cell_h = ih / 3.0
        grid_color = self.config.get("nine_grid_line_color", "#64C8FF")
        hl_color = self.config.get("nine_grid_highlight_color", "#64C8FF")
        grid_width = int(self.config.get("nine_grid_line_width", 1))
        hl_width = int(self.config.get("nine_grid_highlight_width", 2))
        line_pen = pg.mkPen(grid_color, width=grid_width, style=Qt.DashLine)
        for i in range(1, 3):
            v = pg.InfiniteLine(pos=i * cell_w, angle=90, pen=line_pen)
            self.view.addItem(v)
            self._nine_grid_items.append(v)
            h = pg.InfiniteLine(pos=i * cell_h, angle=0, pen=line_pen)
            self.view.addItem(h)
            self._nine_grid_items.append(h)
        area_num = int(nine)
        if 1 <= area_num <= 9:
            col = (area_num - 1) % 3
            row = (area_num - 1) // 3
            hl = pg.RectROI(
                [col * cell_w, row * cell_h], [cell_w, cell_h],
                movable=False, resizable=False,
                pen=pg.mkPen(hl_color, width=hl_width),
            )
            self.view.addItem(hl)
            self._nine_grid_items.append(hl)

    def _rebuild_thumbnails(self):
        infos = []
        for i, path in enumerate(self.image_paths):
            if not os.path.exists(path):
                continue
            result_str = ""
            if i < len(self.image_sources):
                src = self.image_sources[i]
                has_ng = any(s < len(self.inspection_details) and self.inspection_details[s].Result == FINAL_RESULT_NG for s in src)
                result_str = "NG" if has_ng else "OK"
            infos.append(ThumbInfo(image_path=path, thumb_path=path, result=result_str, defect_count=0))
        if infos:
            self.thumb_panel.set_items(infos)
            self.thumb_panel.set_current_index(self.current_image_idx)
        else:
            self.thumb_panel.set_items([])

    def _update_ng_regions(self, show_all=False):
        ng_ids = set()
        if self._product_regions and self.defect_items and self.inspection_details:
            if show_all:
                for item in self.defect_items:
                    dd = self.query_service.get_defect_detail(item, self.inspection_details)
                    if dd:
                        pa = (dd.ProductArea or "").strip()
                        if pa:
                            for r in self._product_regions:
                                if r.name and pa == r.name:
                                    ng_ids.add(r.id)
            else:
                current_indices = set()
                if self.image_sources and 0 <= self.current_image_idx < len(self.image_sources):
                    current_indices = self.image_sources[self.current_image_idx]
                for item in self.defect_items:
                    if current_indices and item.insp_index not in current_indices:
                        continue
                    dd = self.query_service.get_defect_detail(item, self.inspection_details)
                    if dd:
                        pa = (dd.ProductArea or "").strip()
                        if pa:
                            for r in self._product_regions:
                                if r.name and pa == r.name:
                                    ng_ids.add(r.id)
        self.schematic.set_ng_regions(ng_ids)

    def _on_thumb_selected(self, idx: int):
        if idx == self.current_image_idx:
            return
        self.current_image_idx = idx
        self._sync_defect_list_to_current_image()
        self._refresh_image()

    def _on_review(self, result: str):
        sn = self.label_sn.text()
        if not sn or sn == "--":
            QMessageBox.warning(self, "提示", "请先查询产品")
            return

        if result == "OK":
            config = ConfigManager.load()
            measurement_enabled = config.get("review_constraint_measurement_enabled", True)
            appearance_names = config.get("review_constraint_appearance_names", [])

            if measurement_enabled:
                has_size_ng = any(item.source_type == "measurement" for item in self.defect_items)
                if has_size_ng:
                    QMessageBox.warning(self, "改判失败", "该产品存在尺寸NG，不可改判为OK")
                    return

            if appearance_names:
                def _match_appearance(item):
                    if item.source_type == "appearance":
                        detail = self.query_service.get_defect_detail(item, self.inspection_details)
                        if detail and detail.DefectName in appearance_names:
                            return True
                    return False
                has_constrained_appearance = any(_match_appearance(item) for item in self.defect_items)
                if has_constrained_appearance:
                    names_str = "、".join(appearance_names)
                    QMessageBox.warning(self, "改判失败", f"该产品存在受约束的外观缺陷({names_str})，不可改判为OK")
                    return

        try:
            src = self._current_source_name
            if result == "OK":
                msg = self.review_service.review_ok(sn, self.username, src)
            else:
                msg = self.review_service.review_ng(sn, self.username, src)

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            remark = f"复判人员: {self.username} | 复判结果: {result} | 复判时间: {now}"

            self.label_review_status.setText(f"复判结果: {result}")
            self.label_review_status.setStyleSheet(
                f"color: {'#059669' if result == 'OK' else '#DC2626'}; "
                f"font-size: 16px; font-weight: 700; padding: 6px;"
            )
            self.label_review_remark.setText(remark)
            self._show_status(msg)
            LogManager.log_operation(self.username, f"复判{result}", f"SN={sn}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"复判失败: {e}")
            self._show_status(f"复判失败: {e}")

    def _update_review_status(self, sr):
        REVIEW_LABELS = {0: "", 1: "OK", 2: "NG"}
        review_label = REVIEW_LABELS.get(sr.ReviewResult, "")
        if sr.ReviewResult:
            self.label_review_status.setText(f"复判结果: {review_label}")
            color = "#059669" if sr.ReviewResult == REVIEW_OK else "#DC2626"
            self.label_review_status.setStyleSheet(
                f"color: {color}; font-size: 16px; font-weight: 700; padding: 6px;"
            )
            if sr.ReviewRemark:
                self.label_review_remark.setText(sr.ReviewRemark)
            else:
                self.label_review_remark.setText(
                    f"人员={sr.ReviewUser or '--'} | 结果={review_label} | 时间={str(sr.ReviewTime or '') or '--'}"
                )
        else:
            self.label_review_status.setText("待复判")
            self.label_review_status.setStyleSheet("color: #D97706; font-size: 14px; font-weight: 600; padding: 6px;")
            self.label_review_remark.setText("")

    def _clear_display(self):
        self.current_defect = None
        self.current_item = None
        self.defect_items = []
        self.inspection_details = []
        self.station_details = []
        self._history_results = []
        self._history_list.setVisible(False)
        self._history_list.clear()
        self.image_paths = []
        self.image_sources = []
        self._all_image_paths = []
        self._all_image_sources = []
        self._current_source_name = ""
        self._all_query_results = []
        self.current_image_idx = 0
        self._clear_rois()
        self.image_item.clear()
        self._raw_image = None
        self.placeholder_text.setVisible(True)
        self.placeholder_text.setText("--")

        self.label_sn.setText("--")
        self.label_model.setText("--")
        self.label_workorder.setText("--")
        self.label_line.setText("--")
        self.label_machine.setText("--")
        self.label_fix.setText("--")
        self.label_hole.setText("--")
        self.label_pack.setText("--")
        self.label_create_time.setText("--")
        self.label_user.setText("--")
        self.label_review_user.setText("--")
        self.label_defect_name.setText("--")
        self.label_defect_area.setText("--")
        self.label_defect_level.setText("--")
        self.label_defect_region.setText("--")
        self.label_defect_nine.setText("--")
        self.label_defect_target.setText("--")
        self.label_defect_value.setText("--")
        self.schematic.set_highlight_region("")
        self.schematic.clear_selected_region()
        self.schematic.set_ng_regions(set())
        self.result_display.setText("等待查询...")
        self._set_result("WAIT")
        self.defect_list.clear()
        self._show_placeholder("请输入SN查询")
        self.thumb_panel.set_items([])
        self.label_image_path.setText("")
        self.btn_ok.setEnabled(False)
        self.btn_ng.setEnabled(False)
        self.label_review_status.setText("")
        self.label_review_remark.setText("")

    def _show_status(self, msg: str):
        self.statusBar().showMessage(msg)

    def _on_scale_changed(self, value: float):
        if self._raw_image is not None:
            self._display_image(self._raw_image)

    def _zoom_in(self):
        scale = self.spin_scale.value()
        self.spin_scale.setValue(min(5.0, scale + 0.2))

    def _zoom_out(self):
        scale = self.spin_scale.value()
        self.spin_scale.setValue(max(0.5, scale - 0.2))

    def _zoom_fit(self):
        self.view.autoRange()

    def _zoom_actual(self):
        self.spin_scale.setValue(1.0)

    def _on_viewer_clicked(self, event):
        pass

    def _mouse_moved(self, pos):
        if self._crosshair_visible and self._raw_image is not None:
            view_pos = self.view.mapSceneToView(pos)
            x, y = int(view_pos.x()), int(view_pos.y())
            h, w = self._raw_image.shape[:2]
            if 0 <= x < w and 0 <= y < h:
                self.vLine.setPos(x)
                self.hLine.setPos(y)
                self._show_status(f"坐标: ({x}, {y})")

    def _open_settings(self):
        self.config["defect_box_scale"] = self.spin_scale.value()
        ConfigManager.save(self.config)
        from ui.dialogs.settings_dialog import SettingsWindow
        win = SettingsWindow(self.db_manager, self.role, self)
        if win.exec_():
            self.config = ConfigManager.load()
            saved_scale = float(self.config.get("defect_box_scale", 1.2))
            self.spin_scale.setValue(saved_scale)
            if self.image_paths:
                self._apply_image_filter()
        user_data = UserManager.find_by_username(self.username)
        if user_data:
            new_name = user_data["username"]
            if new_name != self.username:
                self.username = new_name
            self.role = user_data.get("role", self.role)
            self._can_review = user_data.get("can_review", self.role != ROLE_OPERATOR)
            role_display = role_display_name(self.role)
            self.label_header_user.setText(f"用户: {self.username} ({role_display})")

    def _switch_user(self):
        self._reauth_timer.stop()
        if self._logout_timer.isActive():
            self._logout_timer.stop()
        LogManager.log_logout(self.username)
        from auth.login_window import LoginWindow
        dlg = LoginWindow(self.db_manager, self)

        def on_switched(_, username, role):
            self.username = username
            self.role = role
            user_data = UserManager.find_by_username(username)
            self._can_review = user_data.get("can_review", role != ROLE_OPERATOR) if user_data else (role != ROLE_OPERATOR)
            role_display = role_display_name(role)
            self.label_header_user.setText(f"用户: {username} ({role_display})")
            self._apply_role_permissions()
            self._clear_display()
            self._reset_session_timer()
            self._show_status(f"已切换用户: {username} ({role_display})")

        dlg.login_success.connect(on_switched)
        dlg.exec_()

    def _open_region_editor(self):
        last_product = self.config.get("last_product_name", "")
        editor = RegionEditorWindow(
            self, QSizeF(self.schematic.width(), self.schematic.height()),
            initial_product=last_product,
        )
        editor.sig_region_saved.connect(self._on_region_saved)
        editor.exec_()
        name = editor.get_product_name()
        self._on_region_saved(name)
        if name:
            self.config["last_product_name"] = name

    def _open_dashboard(self):
        try:
            from dashboard.window import DashboardWindow
            dlg = DashboardWindow(self.db_manager, self)
            dlg.exec_()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "错误", f"无法打开质量看板:\n\n{str(e)}\n\n请重启应用后重试。")

    def _on_region_saved(self, product_name: str):
        if not product_name:
            return
        layout = LayoutPersistence.load_layout(product_name)
        if layout:
            self._product_regions = layout.regions
            self._region_matcher.build_index(layout.regions)
            self._last_canvas_w = layout.canvas_width
            self._last_canvas_h = layout.canvas_height
            self.schematic.set_regions(layout.regions, layout.canvas_width, layout.canvas_height, layout.product_name)
            self.config["last_product_name"] = product_name
            ConfigManager.save(self.config)

    _last_canvas_w = 1000
    _last_canvas_h = 1000

    def _load_product_regions(self):
        product_name = self.config.get("last_product_name", "")
        if not product_name:
            return False
        layout = LayoutPersistence.load_layout(product_name)
        if layout and layout.regions:
            self._product_regions = layout.regions
            self._region_matcher.build_index(layout.regions)
            self._last_canvas_w = layout.canvas_width
            self._last_canvas_h = layout.canvas_height
            self.schematic.set_regions(layout.regions, layout.canvas_width, layout.canvas_height, layout.product_name)
            return True
        return False

    def closeEvent(self, event):
        self._reauth_timer.stop()
        if self._logout_timer.isActive():
            self._logout_timer.stop()
        LogManager.log_logout(self.username)
        super().closeEvent(event)
