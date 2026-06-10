from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QDoubleSpinBox,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateTimeEdit, QTabWidget, QWidget, QApplication,
    QCheckBox, QScrollArea, QStyledItemDelegate, QStyleOptionViewItem,
    QInputDialog,
)
import os
from PyQt5.QtCore import Qt, QDateTime, QThread, QTimer
from PyQt5.QtGui import QFont, QColor
from database.manager import DBManager
from utils.config_manager import (
    ConfigManager, UserManager, role_display_name,
    ROLE_ADMIN, ROLE_INSPECTOR, ROLE_OPERATOR, ALL_ROLES,
    LogManager,
)
from utils.ui_utils import scale_css, sf, sp
from services.fingerprint_service import fingerprint_service
from modes.settings import RejudgeSettings, InteractionMode

ROLE_COMBO_ITEMS = [(role_display_name(r), r) for r in ALL_ROLES]


class PasswordItem(QTableWidgetItem):
    def __init__(self, password=""):
        super().__init__()
        self._password = password

    def data(self, role):
        if role == Qt.DisplayRole:
            return "••••••"
        if role == Qt.EditRole:
            return self._password
        return super().data(role)

    def setData(self, role, value):
        if role == Qt.EditRole:
            self._password = str(value) if value else ""
            return
        super().setData(role, value)

    def set_password(self, password: str):
        self._password = password


class SettingsWindow(QDialog):
    def __init__(self, db_manager: DBManager, current_role: str = ROLE_ADMIN, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_role = current_role
        self.config = ConfigManager.load()
        self.setWindowTitle("系统设置")
        self.setMinimumSize(sp(640), sp(680))
        self.resize(sp(700), sp(720))
        self.setStyleSheet(self._style())
        self._setup_ui()
        self._load_config()

    def _style(self):
        return scale_css("""
        QDialog { background-color: #ffffff; }
        QGroupBox {
            font-size: 13px;
            font-weight: 600;
            color: #4F6CF7;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            margin-top: 12px;
            padding: 16px 12px 12px;
            background-color: #FAFBFC;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
        }
        QLabel { color: #1E293B; font-size: 13px; }
        QLineEdit, QSpinBox, QDoubleSpinBox, QDateTimeEdit {
            padding: 8px 12px;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            background-color: #F8FAFC;
            color: #1E293B;
            font-size: 13px;
        }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus {
            border-color: #4F6CF7;
            background-color: #ffffff;
        }
        QPushButton {
            padding: 8px 18px;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton#btnSave { background-color: #4F6CF7; color: white; }
        QPushButton#btnSave:hover { background-color: #3B5DE7; }
        QPushButton#btnTest { background-color: #EDF2F7; color: #4A5568; }
        QPushButton#btnTest:hover { background-color: #E2E8F0; }
        QPushButton#btnAdd { background-color: #10B981; color: white; }
        QPushButton#btnAdd:hover { background-color: #059669; }
        QPushButton#btnDel { background-color: #EF4444; color: white; }
        QPushButton#btnDel:hover { background-color: #DC2626; }
        QPushButton#btnFp {
            background-color: #4F6CF7; color: white;
        }
        QPushButton#btnFp:hover { background-color: #3B5DE7; }
        QTableWidget {
            background-color: #ffffff;
            color: #1E293B;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            gridline-color: #F1F5F9;
            font-size: 13px;
        }
        QTableWidget::item { padding: 6px 8px; }
        QTableWidget::item:selected { background-color: #EEF0FF; color: #4F6CF7; }
        QHeaderView::section {
            background-color: #F8FAFC;
            color: #64748B;
            padding: 8px;
            border: none;
            border-bottom: 1px solid #E2E8F0;
            font-weight: 600;
        }
        QTabWidget::pane {
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            background-color: #ffffff;
        }
        QTabBar::tab {
            background-color: #F8FAFC;
            color: #64748B;
            padding: 10px 22px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            font-size: 13px;
        }
        QTabBar::tab:selected {
            background-color: #ffffff;
            color: #4F6CF7;
            font-weight: 600;
        }
        QTabBar::tab:hover {
            background-color: #EDF2F7;
        }
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("系统设置")
        title.setStyleSheet("color: #1E293B; font-size: 18px; font-weight: 700; margin-bottom: 6px;")
        layout.addWidget(title)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._build_time_tab(), "查询配置")

        if self.current_role == ROLE_ADMIN:
            tabs.addTab(self._build_db_tab(), "数据库")
        tabs.addTab(self._build_display_tab(), "显示参数")

        if self.current_role == ROLE_ADMIN:
            self._user_tab = self._build_user_tab()
            tabs.addTab(self._user_tab, "用户管理")
        if self.current_role == ROLE_ADMIN:
            self._login_mode_tab = self._build_login_mode_tab()
            tabs.addTab(self._login_mode_tab, "登录模式")

        self._constraint_tab = self._build_constraint_tab()
        tabs.addTab(self._constraint_tab, "判定约束")

        self._review_mode_tab = self._build_review_mode_tab()
        tabs.addTab(self._review_mode_tab, "复判模式")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.setObjectName("btnTest")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _build_db_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)

        title = QLabel("多数据库配置（启用的数据库会依次查询，双击单元格可编辑）")
        title.setStyleSheet("color: #4F6CF7; font-size: 13px; font-weight: 600;")
        layout.addWidget(title)

        self._db_table = QTableWidget()
        self._db_table.setColumnCount(7)
        self._db_table.setHorizontalHeaderLabels(["启用", "名称", "主机", "端口", "用户", "密码", "数据库名"])
        self._db_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._db_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._db_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self._db_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._db_table.setSelectionMode(QTableWidget.SingleSelection)
        self._db_table.setStyleSheet("QTableWidget::item { padding: 4px 8px; }")
        self._db_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._db_table.cellDoubleClicked.connect(self._on_db_cell_clicked)
        layout.addWidget(self._db_table, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        for txt, tip, color, cb in [
            ("新增", "添加新的数据库配置", "#10B981", self._db_add),
            ("删除选中", "删除选中的数据库配置", "#EF4444", self._db_delete),
            ("测试选中", "测试选中数据库的连接", "#4F6CF7", self._db_test),
        ]:
            btn = QPushButton(txt)
            btn.setToolTip(tip)
            btn.setStyleSheet(f"QPushButton{{background:{color};color:white;padding:6px 14px;border-radius:4px;font-weight:600;}}")
            btn.clicked.connect(cb)
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        btn_save = QPushButton("保存所有数据库配置")
        btn_save.setStyleSheet("QPushButton{background:#4F6CF7;color:white;padding:8px 20px;border-radius:6px;font-weight:700;}")
        btn_save.clicked.connect(self._db_save_all)
        layout.addWidget(btn_save)
        return w

    def _build_display_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)

        gb = QGroupBox("缺陷显示")
        form = QFormLayout(gb)
        form.setSpacing(8)

        self.spin_scale = QDoubleSpinBox()
        self.spin_scale.setRange(0.5, 5.0)
        self.spin_scale.setSingleStep(0.1)
        self.spin_scale.setValue(1.2)
        form.addRow("缺陷框倍率:", self.spin_scale)

        self.spin_line_width = QSpinBox()
        self.spin_line_width.setRange(1, 10)
        self.spin_line_width.setValue(2)
        form.addRow("缺陷线宽:", self.spin_line_width)

        color_row = QHBoxLayout()
        self.btn_box_color = QPushButton()
        self.btn_box_color.setFixedSize(40, 28)
        self.btn_box_color.setStyleSheet("background-color: #00FF00; border: 1px solid #CBD5E1; border-radius: 4px;")
        self.btn_box_color.clicked.connect(self._pick_box_color)
        self.label_box_color = QLabel("#00FF00")
        self.label_box_color.setStyleSheet("color: #64748B; font-size: 12px;")
        color_row.addWidget(self.btn_box_color)
        color_row.addWidget(self.label_box_color)
        color_row.addStretch()
        form.addRow("缺陷框颜色:", color_row)

        layout.addWidget(gb)

        gb2 = QGroupBox("图像九宫格网格线")
        form2 = QFormLayout(gb2)
        form2.setSpacing(8)

        grid_row = QHBoxLayout()
        grid_row.setSpacing(6)
        grid_row.addWidget(QLabel("线宽:"))
        self.spin_grid_width = QSpinBox()
        self.spin_grid_width.setRange(1, 10)
        self.spin_grid_width.setValue(1)
        self.spin_grid_width.setFixedWidth(50)
        grid_row.addWidget(self.spin_grid_width)
        grid_row.addWidget(QLabel("颜色:"))
        self.btn_grid_color = QPushButton()
        self.btn_grid_color.setFixedSize(28, 22)
        self.btn_grid_color.setStyleSheet("background-color: #64C8FF; border: 1px solid #CBD5E1; border-radius: 4px;")
        self.btn_grid_color.clicked.connect(lambda: self._pick_color("nine_grid_line_color", self.btn_grid_color, self.label_grid_color))
        grid_row.addWidget(self.btn_grid_color)
        self.label_grid_color = QLabel("#64C8FF")
        self.label_grid_color.setStyleSheet("color: #64748B; font-size: 11px;")
        grid_row.addWidget(self.label_grid_color)
        grid_row.addStretch()
        form2.addRow("网格线:", grid_row)

        hl_row = QHBoxLayout()
        hl_row.setSpacing(6)
        hl_row.addWidget(QLabel("线宽:"))
        self.spin_hl_width = QSpinBox()
        self.spin_hl_width.setRange(1, 10)
        self.spin_hl_width.setValue(2)
        self.spin_hl_width.setFixedWidth(50)
        hl_row.addWidget(self.spin_hl_width)
        hl_row.addWidget(QLabel("颜色:"))
        self.btn_hl_color = QPushButton()
        self.btn_hl_color.setFixedSize(28, 22)
        self.btn_hl_color.setStyleSheet("background-color: #64C8FF; border: 1px solid #CBD5E1; border-radius: 4px;")
        self.btn_hl_color.clicked.connect(lambda: self._pick_color("nine_grid_highlight_color", self.btn_hl_color, self.label_hl_color))
        hl_row.addWidget(self.btn_hl_color)
        self.label_hl_color = QLabel("#64C8FF")
        self.label_hl_color.setStyleSheet("color: #64748B; font-size: 11px;")
        hl_row.addWidget(self.label_hl_color)
        hl_row.addStretch()
        form2.addRow("高亮线:", hl_row)

        layout.addWidget(gb2)

        self.chk_show_box = QCheckBox("显示缺陷框")
        layout.addWidget(self.chk_show_box)

        self.chk_show_ok = QCheckBox("显示OK图")
        layout.addWidget(self.chk_show_ok)

        layout.addStretch()

        btn_save_display = QPushButton("保存设置")
        btn_save_display.setObjectName("btnSave")
        btn_save_display.clicked.connect(self._save_display_config)
        layout.addWidget(btn_save_display)

        scroll.setWidget(w)
        return scroll

    def _build_time_tab(self):
        from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QRadioButton, QButtonGroup
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        gb = QGroupBox("模式选择")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(10)

        self._mode_group = QButtonGroup(self)

        self._radio_default = QRadioButton("默认模式")
        self._radio_default.setStyleSheet("font-size: 13px; color: #1E293B;")
        self._mode_group.addButton(self._radio_default, 0)
        gb_layout.addWidget(self._radio_default)

        self._radio_quick = QRadioButton("快捷模式")
        self._radio_quick.setStyleSheet("font-size: 13px; color: #1E293B;")
        self._mode_group.addButton(self._radio_quick, 1)
        gb_layout.addWidget(self._radio_quick)

        self._quick_btns = []
        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        quick_row.setContentsMargins(24, 0, 0, 0)

        def mk_quick(text, days):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setStyleSheet("QPushButton{background:#EEF2FF;color:#4F6CF7;padding:6px 14px;border-radius:6px;font-weight:600;}"
                            "QPushButton:hover{background:#E0E7FF;}"
                            "QPushButton:checked{background:#4F6CF7;color:white;}")
            b.days = days
            b.clicked.connect(lambda checked, d=days: self._quick_time(d))
            self._quick_btns.append(b)
            quick_row.addWidget(b)
            return b

        mk_quick("今天", 0)
        mk_quick("昨天", 1)
        mk_quick("近7天", 7)
        mk_quick("近30天", 30)
        mk_quick("本月", -1)
        quick_row.addStretch()
        gb_layout.addLayout(quick_row)

        self._radio_custom = QRadioButton("自定义模式")
        self._radio_custom.setStyleSheet("font-size: 13px; color: #1E293B;")
        self._mode_group.addButton(self._radio_custom, 2)
        gb_layout.addWidget(self._radio_custom)

        custom_row = QHBoxLayout()
        custom_row.setContentsMargins(24, 0, 0, 0)
        custom_row.setSpacing(8)

        self.dt_start = QDateTimeEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDateTime(QDateTime.currentDateTime().addDays(-7))
        self.dt_start.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_start.setStyleSheet("QDateTimeEdit{padding:8px 12px;border:1px solid #E2E8F0;border-radius:6px;background:#F8FAFC;color:#1E293B;}")
        custom_row.addWidget(QLabel("起始:"))
        custom_row.addWidget(self.dt_start)

        self.dt_end = QDateTimeEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDateTime(QDateTime.currentDateTime())
        self.dt_end.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dt_end.setStyleSheet("QDateTimeEdit{padding:8px 12px;border:1px solid #E2E8F0;border-radius:6px;background:#F8FAFC;color:#1E293B;}")
        custom_row.addWidget(QLabel("结束:"))
        custom_row.addWidget(self.dt_end)

        btn_save_time = QPushButton("保存时间范围")
        btn_save_time.setStyleSheet("QPushButton{background:#4F6CF7;color:white;padding:7px 16px;border-radius:6px;font-weight:600;}"
                                    "QPushButton:hover{background:#3B5DE7;}")
        btn_save_time.clicked.connect(self._save_time_config)
        custom_row.addWidget(btn_save_time)
        custom_row.addStretch()
        gb_layout.addLayout(custom_row)

        layout.addWidget(gb)
        layout.addStretch()

        self._mode_group.buttonClicked.connect(self._on_mode_changed)
        self.dt_start.dateTimeChanged.connect(self._on_custom_time_changed)
        self.dt_end.dateTimeChanged.connect(self._on_custom_time_changed)

        return w

    def _on_mode_changed(self, btn):
        idx = self._mode_group.id(btn)
        is_quick = idx == 1
        is_custom = idx == 2
        for b in self._quick_btns:
            b.setEnabled(is_quick)
            if not is_quick:
                b.setChecked(False)
        self.dt_start.setEnabled(is_custom)
        self.dt_end.setEnabled(is_custom)

        if idx == 0:
            self.config["query_mode"] = "default"
            self.config["query_start_time"] = ""
            self.config["query_end_time"] = ""
            ConfigManager.save(self.config)
            self._push_time_to_dbmanager()
        elif idx == 1:
            self.config["query_mode"] = "quick"
            self._quick_time(self.config.get("quick_days", 0))
        elif idx == 2:
            self.config["query_mode"] = "custom"

    def _on_custom_time_changed(self):
        if self._radio_custom.isChecked():
            self._save_time_config()

    def _push_time_to_dbmanager(self):
        mw = self.parent()
        if mw and hasattr(mw, 'db_manager'):
            mode = self.config.get("query_mode", "default")
            qs = self.config.get("query_start_time", "")
            qe = self.config.get("query_end_time", "")
            qd = int(self.config.get("quick_days", 0))
            mw.db_manager.set_query_time_range(mode, qs, qe, qd)

    def _quick_time(self, days):
        now = QDateTime.currentDateTime()
        if days == 0:
            start = QDateTime(now.date().year(), now.date().month(), now.date().day(), 0, 0, 0)
        elif days == -1:
            start = QDateTime(now.date().year(), now.date().month(), 1, 0, 0, 0)
        else:
            start = now.addDays(-days)
            start = QDateTime(start.date().year(), start.date().month(), start.date().day(), 0, 0, 0)
        self.config["query_mode"] = "quick"
        self.config["quick_days"] = days
        self.config["query_start_time"] = start.toString("yyyy-MM-dd HH:mm:ss")
        self.config["query_end_time"] = now.toString("yyyy-MM-dd HH:mm:ss")
        ConfigManager.save(self.config)
        self._push_time_to_dbmanager()
        self._radio_default.setChecked(False)
        self._radio_custom.setChecked(False)
        self._radio_quick.setChecked(True)
        for btn in self._quick_btns:
            btn.setChecked(btn.days == days)
        self.dt_start.setEnabled(False)
        self.dt_end.setEnabled(False)

    def _save_time_config(self):
        self.config["query_mode"] = "custom"
        self.config["query_start_time"] = self.dt_start.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        self.config["query_end_time"] = self.dt_end.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        ConfigManager.save(self.config)
        self._push_time_to_dbmanager()
        self._radio_default.setChecked(False)
        self._radio_quick.setChecked(False)
        for b in self._quick_btns:
            b.setChecked(False)
        self._radio_custom.setChecked(True)
        QMessageBox.information(self, "成功", "时间范围已保存")

    def _build_user_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(10)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(["ID", "用户名", "角色", "指纹", "密码", "复判授权"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.cellDoubleClicked.connect(self._edit_user)
        layout.addWidget(self.user_table)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_add = QPushButton("新增用户")
        btn_add.setObjectName("btnAdd")
        btn_add.clicked.connect(self._add_user)
        btn_row.addWidget(btn_add)
        btn_edit = QPushButton("编辑用户")
        btn_edit.setObjectName("btnSave")
        btn_edit.clicked.connect(self._edit_user)
        btn_row.addWidget(btn_edit)
        btn_del = QPushButton("删除用户")
        btn_del.setObjectName("btnDel")
        btn_del.clicked.connect(self._delete_user)
        btn_row.addWidget(btn_del)
        btn_fp = QPushButton("指纹注册")
        btn_fp.setObjectName("btnFp")
        btn_fp.clicked.connect(self._enroll_fingerprint)
        btn_row.addWidget(btn_fp)
        btn_refresh = QPushButton("刷新")
        btn_refresh.setObjectName("btnTest")
        btn_refresh.clicked.connect(self._refresh_users)
        btn_row.addWidget(btn_refresh)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._refresh_users()
        return w

    def _load_config(self):
        dbs = ConfigManager.get_databases(self.config)
        self._populate_db_table(dbs)
        if hasattr(self, 'spin_scale'):
            self.spin_scale.setValue(float(self.config.get("defect_box_scale", 1.2)))
            self.spin_line_width.setValue(int(self.config.get("defect_line_width", 2)))
        c = self.config.get("defect_box_color", "#00FF00")
        self._update_color_display(self.btn_box_color, self.label_box_color, c)
        if hasattr(self, 'spin_grid_width'):
            self.spin_grid_width.setValue(int(self.config.get("nine_grid_line_width", 1)))
            self.spin_hl_width.setValue(int(self.config.get("nine_grid_highlight_width", 2)))
            gc = self.config.get("nine_grid_line_color", "#64C8FF")
            self._update_color_display(self.btn_grid_color, self.label_grid_color, gc)
            hc = self.config.get("nine_grid_highlight_color", "#64C8FF")
            self._update_color_display(self.btn_hl_color, self.label_hl_color, hc)
        self.chk_show_box.setChecked(self.config.get("show_defect_box", True))
        self.chk_show_ok.setChecked(self.config.get("show_ok_images", False))

        if hasattr(self, '_mode_group'):
            mode = self.config.get("query_mode", "default")
            qd = int(self.config.get("quick_days", 0))
            if mode == "default":
                self._radio_default.setChecked(True)
                self._on_mode_changed(self._radio_default)
            elif mode == "quick":
                now = QDateTime.currentDateTime()
                if qd == 0:
                    start = QDateTime(now.date().year(), now.date().month(), now.date().day(), 0, 0, 0)
                elif qd == -1:
                    start = QDateTime(now.date().year(), now.date().month(), 1, 0, 0, 0)
                else:
                    d = now.addDays(-qd)
                    start = QDateTime(d.date().year(), d.date().month(), d.date().day(), 0, 0, 0)
                self.config["query_start_time"] = start.toString("yyyy-MM-dd HH:mm:ss")
                self.config["query_end_time"] = now.toString("yyyy-MM-dd HH:mm:ss")
                self._radio_quick.setChecked(True)
                for btn in self._quick_btns:
                    btn.setChecked(btn.days == qd)
                self.dt_start.setEnabled(False)
                self.dt_end.setEnabled(False)
                self._push_time_to_dbmanager()
            elif mode == "custom":
                start_str = self.config.get("query_start_time", "")
                end_str = self.config.get("query_end_time", "")
                if start_str:
                    self.dt_start.setDateTime(QDateTime.fromString(start_str, "yyyy-MM-dd HH:mm:ss"))
                if end_str:
                    self.dt_end.setDateTime(QDateTime.fromString(end_str, "yyyy-MM-dd HH:mm:ss"))
                self._radio_custom.setChecked(True)
                for b in self._quick_btns:
                    b.setEnabled(False)

    def _populate_db_table(self, dbs: list):
        self._db_table.blockSignals(True)
        self._db_table.setRowCount(len(dbs))
        for i, db in enumerate(dbs):
            ck = QTableWidgetItem()
            ck.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            ck.setCheckState(Qt.Checked if db.get("enabled", True) else Qt.Unchecked)
            self._db_table.setItem(i, 0, ck)
            name_item = QTableWidgetItem(db.get("name", ""))
            self._db_table.setItem(i, 1, name_item)
            self._db_table.setItem(i, 2, QTableWidgetItem(db.get("host", "")))
            self._db_table.setItem(i, 3, QTableWidgetItem(str(db.get("port", 3306))))
            self._db_table.setItem(i, 4, QTableWidgetItem(db.get("user", "")))
            pwd_item = PasswordItem(db.get("password", ""))
            self._db_table.setItem(i, 5, pwd_item)
            self._db_table.setItem(i, 6, QTableWidgetItem(db.get("database", "")))
        self._db_table.blockSignals(False)
        self._db_table.blockSignals(False)

    def _collect_db_list(self) -> list:
        dbs = []
        for i in range(self._db_table.rowCount()):
            enabled = self._db_table.item(i, 0).checkState() == Qt.Checked
            pwd_item = self._db_table.item(i, 5)
            password = pwd_item._password if isinstance(pwd_item, PasswordItem) else pwd_item.text()
            dbs.append({
                "name": self._db_table.item(i, 1).text().strip(),
                "host": self._db_table.item(i, 2).text().strip(),
                "port": int(self._db_table.item(i, 3).text().strip() or "3306"),
                "user": self._db_table.item(i, 4).text().strip(),
                "password": password,
                "database": self._db_table.item(i, 6).text().strip(),
                "enabled": enabled,
            })
        return dbs

    def _on_db_cell_clicked(self, row: int, col: int):
        if col == 0:
            return
        labels = ["", "名称", "主机", "端口", "用户", "密码", "数据库名"]
        label = labels[col]
        if col == 1:
            old = self._db_table.item(row, col).text()
            new, ok = QInputDialog.getText(self, f"修改{label}", f"{label}：", text=old)
            if ok and new.strip():
                self._db_table.item(row, col).setText(new.strip())
        elif col == 3:
            old = int(self._db_table.item(row, col).text().strip() or "3306")
            new, ok = QInputDialog.getInt(self, f"修改{label}", f"{label}：", value=old, min=1, max=65535)
            if ok:
                self._db_table.item(row, col).setText(str(new))
        elif col == 5:
            pwd_item = self._db_table.item(row, col)
            old = pwd_item.data(Qt.EditRole) if isinstance(pwd_item, PasswordItem) else ""
            new, ok = QInputDialog.getText(self, f"修改{label}", f"{label}：", text=old, echo=QLineEdit.Password)
            if ok:
                pwd_item.set_password(new)
        else:
            old = self._db_table.item(row, col).text()
            new, ok = QInputDialog.getText(self, f"修改{label}", f"{label}：", text=old)
            if ok:
                self._db_table.item(row, col).setText(new)

    def _db_add(self):
        row = self._db_table.rowCount()
        self._db_table.insertRow(row)
        ck = QTableWidgetItem()
        ck.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        ck.setCheckState(Qt.Checked)
        self._db_table.setItem(row, 0, ck)
        self._db_table.setItem(row, 1, QTableWidgetItem(f"数据库{row+1}"))
        self._db_table.setItem(row, 2, QTableWidgetItem("127.0.0.1"))
        self._db_table.setItem(row, 3, QTableWidgetItem("3306"))
        self._db_table.setItem(row, 4, QTableWidgetItem("root"))
        self._db_table.setItem(row, 5, PasswordItem(""))
        self._db_table.setItem(row, 6, QTableWidgetItem("aoi"))

    def _db_delete(self):
        row = self._db_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中要删除的行")
            return
        self._db_table.removeRow(row)

    def _db_test(self):
        row = self._db_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中要测试的行")
            return
        host = self._db_table.item(row, 2).text().strip()
        port = int(self._db_table.item(row, 3).text().strip() or "3306")
        user = self._db_table.item(row, 4).text().strip()
        pwd_item = self._db_table.item(row, 5)
        pwd = pwd_item._password if isinstance(pwd_item, PasswordItem) else ""
        dbname = self._db_table.item(row, 6).text().strip()
        name = self._db_table.item(row, 1).text().strip()
        try:
            from database.manager import DBConnection
            conn = DBConnection(name, host=host, port=port, user=user, password=pwd, database=dbname)
            conn.connect()
            conn.disconnect()
            QMessageBox.information(self, "成功", f"[{name}] 数据库连接成功！")
        except Exception as e:
            QMessageBox.critical(self, "失败", f"[{name}] 连接失败:\n{e}")

    def _db_save_all(self):
        dbs = self._collect_db_list()
        self.config["databases"] = dbs
        ConfigManager.save(self.config)
        QMessageBox.information(self, "成功", "数据库配置已保存，请重启应用生效")

    def _save_display_config(self):
        self.config["defect_box_scale"] = self.spin_scale.value()
        self.config["defect_line_width"] = self.spin_line_width.value()
        self.config["defect_box_color"] = self.label_box_color.text()
        if hasattr(self, 'spin_grid_width'):
            self.config["nine_grid_line_width"] = self.spin_grid_width.value()
            self.config["nine_grid_highlight_width"] = self.spin_hl_width.value()
            self.config["nine_grid_line_color"] = self.label_grid_color.text()
            self.config["nine_grid_highlight_color"] = self.label_hl_color.text()
        self.config["show_defect_box"] = self.chk_show_box.isChecked()
        self.config["show_ok_images"] = self.chk_show_ok.isChecked()
        ConfigManager.save(self.config)
        QMessageBox.information(self, "成功", "显示设置已保存")

    def _update_color_display(self, btn, label, hex_color):
        label.setText(hex_color)
        btn.setStyleSheet(
            f"background-color: {hex_color}; border: 1px solid #CBD5E1; border-radius: 4px;"
        )

    def _pick_box_color(self):
        self._pick_color("defect_box_color", self.btn_box_color, self.label_box_color)

    def _pick_color(self, config_key, btn, label):
        from PyQt5.QtWidgets import QColorDialog
        current = self.config.get(config_key, "#00FF00")
        c = QColorDialog.getColor(QColor(current), self, "选择颜色")
        if c.isValid():
            hex_color = c.name().upper()
            self._update_color_display(btn, label, hex_color)
            self.config[config_key] = hex_color
            ConfigManager.save(self.config)

    def _quick_time(self, days):
        now = QDateTime.currentDateTime()
        if days == 0:
            start = QDateTime(now.date().year(), now.date().month(), now.date().day(), 0, 0, 0)
        elif days == -1:
            start = QDateTime(now.date().year(), now.date().month(), 1, 0, 0, 0)
        else:
            start = now.addDays(-days)
            start = QDateTime(start.date().year(), start.date().month(), start.date().day(), 0, 0, 0)
        self.dt_start.setDateTime(start)
        self.dt_end.setDateTime(now)
        self.config["query_start_time"] = start.toString("yyyy-MM-dd HH:mm:ss")
        self.config["query_end_time"] = now.toString("yyyy-MM-dd HH:mm:ss")
        self._push_time_to_dbmanager()
        for btn in self._quick_btns:
            btn.setChecked(btn.days == days)

    def _save_time_config(self):
        self.config["query_start_time"] = self.dt_start.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        self.config["query_end_time"] = self.dt_end.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        ConfigManager.save(self.config)
        self._push_time_to_dbmanager()
        QMessageBox.information(self, "成功", "时间范围已保存")

    def _refresh_users(self):
        try:
            users = UserManager.load_users()
            self.user_table.setRowCount(len(users))
            for i, u in enumerate(users):
                self.user_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                self.user_table.setItem(i, 1, QTableWidgetItem(u["username"]))
                role_display = role_display_name(u.get("role", ROLE_OPERATOR))
                self.user_table.setItem(i, 2, QTableWidgetItem(role_display))

                has_fp = bool(u.get("fingerprint_template", ""))
                fp_text = "已绑定" if has_fp else "未绑定"
                fp_item = QTableWidgetItem(fp_text)
                fp_item.setForeground(QColor("#10B981") if has_fp else QColor("#EF4444"))
                self.user_table.setItem(i, 3, fp_item)

                has_pwd = bool(u.get("password", ""))
                self.user_table.setItem(i, 4, QTableWidgetItem("已设置" if has_pwd else "未设置"))

                can_review = u.get("can_review", u.get("role") != ROLE_OPERATOR)
                review_item = QTableWidgetItem("允许" if can_review else "禁止")
                review_item.setForeground(QColor("#10B981") if can_review else QColor("#EF4444"))
                self.user_table.setItem(i, 5, review_item)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载用户列表失败: {e}")

    def _add_user(self):
        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel, QCheckBox
        )
        dlg = QDialog(self)
        dlg.setWindowTitle("添加用户")
        dlg.setStyleSheet(self._style())
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("用户名:"))
        uname = QLineEdit()
        layout.addWidget(uname)
        layout.addWidget(QLabel("密码(留空则只能指纹登录):"))
        upass = QLineEdit()
        upass.setEchoMode(QLineEdit.Password)
        layout.addWidget(upass)
        layout.addWidget(QLabel("角色:"))
        role_cb = QComboBox()
        for display, role in ROLE_COMBO_ITEMS:
            role_cb.addItem(display, role)
        layout.addWidget(role_cb)
        chk_review = QCheckBox("允许复判操作")
        chk_review.setChecked(False)
        layout.addWidget(chk_review)

        def _on_role_changed(idx):
            role = role_cb.itemData(idx)
            chk_review.setChecked(role != ROLE_OPERATOR)
        role_cb.currentIndexChanged.connect(_on_role_changed)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if dlg.exec_() == QDialog.Accepted:
            u, p = uname.text().strip(), upass.text().strip()
            r = role_cb.currentData()
            cr = chk_review.isChecked()
            if not u:
                QMessageBox.warning(self, "提示", "用户名不能为空")
                return
            try:
                UserManager.add_user(u, p, r, can_review=cr)
                self._refresh_users()
                LogManager.log_operation("admin", "新增用户", f"用户名={u}, 角色={r}, 复判授权={cr}")
                QMessageBox.information(self, "成功", f"用户 [{u}] 添加成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加失败: {e}")

    def _edit_user(self):
        row = self.user_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个用户")
            return
        username = self.user_table.item(row, 1).text()

        users = UserManager.load_users()
        cur_user = None
        for u in users:
            if u["username"] == username:
                cur_user = u
                break
        if not cur_user:
            return

        cur_role = cur_user.get("role", ROLE_OPERATOR)
        has_fp = bool(cur_user.get("fingerprint_template", ""))
        cur_can_review = cur_user.get("can_review", cur_role != ROLE_OPERATOR)

        from PyQt5.QtWidgets import (
            QDialog, QVBoxLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel, QCheckBox
        )
        dlg = QDialog(self)
        dlg.setWindowTitle(f"编辑用户 - {username}")
        dlg.setStyleSheet(self._style())
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("用户名:"))
        uname = QLineEdit(username)
        layout.addWidget(uname)
        layout.addWidget(QLabel("新密码(留空不修改):"))
        upass = QLineEdit()
        upass.setEchoMode(QLineEdit.Password)
        layout.addWidget(upass)
        layout.addWidget(QLabel("角色:"))
        role_cb = QComboBox()
        for display, role in ROLE_COMBO_ITEMS:
            role_cb.addItem(display, role)
            if role == cur_role:
                role_cb.setCurrentIndex(role_cb.count() - 1)
        layout.addWidget(role_cb)

        chk_review = QCheckBox("允许复判操作")
        chk_review.setChecked(cur_can_review)
        layout.addWidget(chk_review)

        fp_status = QLabel(f"指纹: {'已绑定' if has_fp else '未绑定'}")
        fp_status.setStyleSheet(f"color: {'#10B981' if has_fp else '#EF4444'}; font-weight: 600;")
        layout.addWidget(fp_status)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if dlg.exec_() == QDialog.Accepted:
            try:
                new_name = uname.text().strip()
                pwd = upass.text().strip()
                new_role = role_cb.currentData()
                cr = chk_review.isChecked()
                if not new_name:
                    QMessageBox.warning(self, "提示", "用户名不能为空")
                    return
                UserManager.update_user(username, password=pwd or None, role=new_role, can_review=cr, new_username=new_name)
                if has_fp and new_name != username:
                    fingerprint_service.delete_user_fingerprint(username)
                self._refresh_users()
                LogManager.log_operation("admin", "编辑用户", f"原用户名={username}, 新用户名={new_name}, 角色={new_role}, 复判授权={cr}")
                QMessageBox.information(self, "成功", f"用户已更新")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败: {e}")

    def _delete_user(self):
        row = self.user_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个用户")
            return
        username = self.user_table.item(row, 1).text()
        if username == "admin":
            QMessageBox.warning(self, "提示", "不能删除管理员账户")
            return
        ret = QMessageBox.question(self, "确认", f"确定删除用户 [{username}] 吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            try:
                if fingerprint_service.is_available:
                    fingerprint_service.delete_user_fingerprint(username)
                UserManager.delete_user(username)
                self._refresh_users()
                LogManager.log_operation("admin", "删除用户", f"用户名={username}")
                QMessageBox.information(self, "成功", f"用户 [{username}] 已删除")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {e}")

    def _enroll_fingerprint(self):
        row = self.user_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个用户")
            return
        username = self.user_table.item(row, 1).text()

        dlg = QDialog(self)
        dlg.setWindowTitle(f"指纹注册 - {username}")
        dlg.setFixedSize(380, 300)
        dlg.setStyleSheet(self._style())

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        prompt = QLabel("指纹注册\n请确保指纹采集器已连接\n\n采集3次同一手指指纹")
        prompt.setAlignment(Qt.AlignCenter)
        prompt.setStyleSheet("color: #4F6CF7; font-size: 14px; font-weight: 600; padding: 10px;")
        layout.addWidget(prompt)

        status = QLabel("点击下方按钮开始")
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet("color: #64748B; font-size: 13px;")
        layout.addWidget(status)

        count_label = QLabel("采集次数: 0/3")
        count_label.setAlignment(Qt.AlignCenter)
        count_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(count_label)

        btn_start = QPushButton("开始采集")
        btn_start.setObjectName("btnFp")
        btn_start.setMinimumHeight(40)
        layout.addWidget(btn_start)

        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("btnTest")
        layout.addWidget(btn_cancel)

        QApplication.processEvents()

        from services.fingerprint_service import (
            fingerprint_service, ZKFP_ERR_OK, ZKFP_ERR_CAPTURE,
            ZKFP_ERR_BUSY, ZKFP_ERR_NOT_OPENED, ZKFP_ERR_NOT_INIT,
            ZKFP_ERR_OPEN, ZKFP_ERR_FAIL, FingerprintEnroller,
        )

        timer = QTimer(dlg)
        enroller = FingerprintEnroller(fingerprint_service)
        capture_failures = 0
        enroll_success = False

        def stop_enroll():
            timer.stop()
            btn_start.setEnabled(True)
            btn_start.setText("重试")
            btn_cancel.setText("取消")
            btn_cancel.setEnabled(True)

        def on_capture():
            nonlocal capture_failures, enroll_success
            ret, template, count = enroller.capture_for_enroll()

            if ret == ZKFP_ERR_OK:
                capture_failures = 0
                count_label.setText(f"采集次数: {count}/3")
                status.setText(f"第 {count} 次采集成功")
                if enroller.is_complete():
                    timer.stop()
                    status.setText("正在合并指纹模板...")
                    QApplication.processEvents()

                    mret, merged = enroller.merge()
                    if mret != ZKFP_ERR_OK or not merged:
                        status.setText("注册失败：DBMerge 错误")
                        stop_enroll()
                        return

                    fid = fingerprint_service.next_fid
                    add_ret = fingerprint_service.db_add(fid, merged)
                    if add_ret != ZKFP_ERR_OK:
                        status.setText(f"注册失败：DBAdd 错误 {add_ret}")
                        stop_enroll()
                        return

                    fingerprint_service.fid_user_map[fid] = username
                    fingerprint_service.next_fid += 1

                    import base64
                    b64 = base64.b64encode(merged).decode("ascii")
                    UserManager.update_user(username, fingerprint_template=b64)
                    LogManager.log_operation("admin", "指纹注册", f"用户名={username}")

                    enroll_success = True
                    self._refresh_users()
                    QMessageBox.information(dlg, "成功", f"用户 [{username}] 指纹注册成功")
                    dlg.accept()
            elif ret == -100:
                status.setText("请按压同一手指")
            elif ret in {ZKFP_ERR_CAPTURE, -28}:
                capture_failures += 1
                if capture_failures < 15:
                    status.setText("请将手指按压在指纹采集器上")
                else:
                    status.setText("采集超时，请确认设备连接正常后重试")
                    stop_enroll()
            elif ret in {ZKFP_ERR_BUSY, ZKFP_ERR_NOT_OPENED, ZKFP_ERR_NOT_INIT, ZKFP_ERR_OPEN, ZKFP_ERR_FAIL}:
                status.setText(f"设备异常(错误码{ret})，请重试")
                stop_enroll()
            else:
                capture_failures += 1
                status.setText(f"采集中...({ret})")

        def do_enroll():
            if timer.isActive():
                return

            enroller.reset()
            capture_failures = 0
            btn_start.setEnabled(False)
            btn_cancel.setEnabled(True)
            btn_start.setText("采集中...")
            status.setText("正在初始化指纹设备...")
            count_label.setText("采集次数: 0/3")
            QApplication.processEvents()

            users = UserManager.load_users()
            ret = fingerprint_service.ensure_device_ready(users)
            if ret != ZKFP_ERR_OK:
                status.setText("指纹设备初始化失败")
                btn_start.setEnabled(True)
                btn_start.setText("重试")
                return
            status.setText("设备已就绪，请按压手指")

            timer.start(300)

        def cancel_enroll():
            timer.stop()
            if dlg.isVisible():
                dlg.reject()

        btn_start.clicked.connect(do_enroll)
        btn_cancel.clicked.connect(cancel_enroll)
        timer.timeout.connect(on_capture)

        dlg.exec_()
        timer.stop()
        fingerprint_service.release_device()

        if enroll_success:
            self._refresh_users()

    def _build_login_mode_tab(self):
        from PyQt5.QtWidgets import QButtonGroup, QRadioButton

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        gb = QGroupBox("登录模式选择")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(8)

        info = QLabel("切换后需重启应用生效")
        info.setStyleSheet("color: #EF4444; font-size: 12px; font-weight: 600;")
        gb_layout.addWidget(info)

        self._login_mode_group = QButtonGroup()
        self._rb_fp = QRadioButton("指纹登录模式")
        self._rb_pwd = QRadioButton("密码登录模式")
        self._login_mode_group.addButton(self._rb_fp, 0)
        self._login_mode_group.addButton(self._rb_pwd, 1)

        fp_desc = QLabel("用户无需设置密码，通过指纹采集器验证身份")
        fp_desc.setStyleSheet("color: #94A3B8; font-size: 11px; margin-left: 24px;")
        pwd_desc = QLabel("所有用户必须设置密码，通过用户名+密码登录")
        pwd_desc.setStyleSheet("color: #94A3B8; font-size: 11px; margin-left: 24px;")

        self._rb_fp.setChecked(True)
        gb_layout.addWidget(self._rb_fp)
        gb_layout.addWidget(fp_desc)
        gb_layout.addSpacing(4)
        gb_layout.addWidget(self._rb_pwd)
        gb_layout.addWidget(pwd_desc)
        layout.addWidget(gb)

        layout.addStretch()

        btn_save = QPushButton("保存")
        btn_save.setObjectName("btnSave")
        btn_save.clicked.connect(self._save_login_mode)
        layout.addWidget(btn_save)

        current_mode = self.config.get("login_mode", "fingerprint")
        if current_mode == "password":
            self._rb_pwd.setChecked(True)
        else:
            self._rb_fp.setChecked(True)

        return w

    def _build_constraint_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        gb1 = QGroupBox("尺寸判定约束")
        form1 = QFormLayout(gb1)
        form1.setSpacing(8)
        self._chk_constraint_measurement = QCheckBox("存在尺寸NG时禁止改判为OK")
        self._chk_constraint_measurement.setChecked(True)
        form1.addRow(self._chk_constraint_measurement)
        layout.addWidget(gb1)

        gb2 = QGroupBox("外观判定约束")
        gb2_layout = QVBoxLayout(gb2)
        gb2_layout.setSpacing(8)

        desc = QLabel("添加需要约束的外观缺陷名称，检测结果包含这些名称时禁止改判为OK")
        desc.setStyleSheet("color: #64748B; font-size: 12px;")
        desc.setWordWrap(True)
        gb2_layout.addWidget(desc)

        self._appearance_table = QTableWidget()
        self._appearance_table.setColumnCount(1)
        self._appearance_table.setHorizontalHeaderLabels(["外观缺陷名称"])
        self._appearance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._appearance_table.setSelectionBehavior(QTableWidget.SelectRows)
        gb2_layout.addWidget(self._appearance_table)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_add_app = QPushButton("添加")
        btn_add_app.setObjectName("btnAdd")
        btn_add_app.clicked.connect(self._add_appearance_constraint)
        btn_row.addWidget(btn_add_app)
        btn_del_app = QPushButton("删除选中")
        btn_del_app.setObjectName("btnDel")
        btn_del_app.clicked.connect(self._del_appearance_constraint)
        btn_row.addWidget(btn_del_app)
        btn_row.addStretch()
        gb2_layout.addLayout(btn_row)

        layout.addWidget(gb2)
        layout.addStretch()

        btn_save = QPushButton("保存")
        btn_save.setObjectName("btnSave")
        btn_save.clicked.connect(self._save_constraint_config)
        layout.addWidget(btn_save)

        self._load_constraint_config()
        return w

    def _load_constraint_config(self):
        self._chk_constraint_measurement.setChecked(
            self.config.get("review_constraint_measurement_enabled", True)
        )
        names = self.config.get("review_constraint_appearance_names", [])
        self._appearance_table.setRowCount(len(names))
        for i, name in enumerate(names):
            self._appearance_table.setItem(i, 0, QTableWidgetItem(name))

    def _add_appearance_constraint(self):
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "添加外观约束", "外观缺陷名称：")
        if ok and name.strip():
            row = self._appearance_table.rowCount()
            self._appearance_table.insertRow(row)
            self._appearance_table.setItem(row, 0, QTableWidgetItem(name.strip()))

    def _del_appearance_constraint(self):
        row = self._appearance_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中要删除的行")
            return
        self._appearance_table.removeRow(row)

    def _save_constraint_config(self):
        self.config["review_constraint_measurement_enabled"] = self._chk_constraint_measurement.isChecked()
        names = []
        for i in range(self._appearance_table.rowCount()):
            item = self._appearance_table.item(i, 0)
            if item and item.text().strip():
                names.append(item.text().strip())
        self.config["review_constraint_appearance_names"] = names
        ConfigManager.save(self.config)
        QMessageBox.information(self, "成功", "判定约束设置已保存")

    def _build_review_mode_tab(self):
        from PyQt5.QtWidgets import QButtonGroup, QRadioButton

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        gb = QGroupBox("复判交互模式")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(8)

        desc = QLabel("选择复判操作的交互模式，切换后立即生效")
        desc.setStyleSheet("color: #64748B; font-size: 12px;")
        gb_layout.addWidget(desc)

        self._review_mode_group = QButtonGroup()
        self._rb_image = QRadioButton("图片优先模式（推荐）")
        self._rb_region = QRadioButton("区域优先模式")

        self._rb_image.setChecked(True)
        gb_layout.addWidget(self._rb_image)
        img_desc = QLabel("按缺陷图片顺序逐张复判，操作简单，适合新手和少量缺陷")
        img_desc.setStyleSheet("color: #94A3B8; font-size: 11px; margin-left: 24px;")
        img_desc.setWordWrap(True)
        gb_layout.addWidget(img_desc)

        gb_layout.addSpacing(4)
        gb_layout.addWidget(self._rb_region)
        region_desc = QLabel("按产品区域分组复判，效率更高，适合熟练人员和大量缺陷")
        region_desc.setStyleSheet("color: #94A3B8; font-size: 11px; margin-left: 24px;")
        region_desc.setWordWrap(True)
        gb_layout.addWidget(region_desc)

        self._review_mode_group.addButton(self._rb_image, 0)
        self._review_mode_group.addButton(self._rb_region, 1)

        layout.addWidget(gb)

        gb2 = QGroupBox("选项")
        gb2_layout = QVBoxLayout(gb2)
        self._chk_remember = QCheckBox("记住上次使用的模式")
        self._chk_remember.setChecked(True)
        gb2_layout.addWidget(self._chk_remember)
        self._chk_auto_next = QCheckBox("判定后自动下一项")
        self._chk_auto_next.setChecked(True)
        gb2_layout.addWidget(self._chk_auto_next)
        self._chk_region_hl = QCheckBox("显示区域高亮")
        self._chk_region_hl.setChecked(True)
        gb2_layout.addWidget(self._chk_region_hl)
        layout.addWidget(gb2)

        # Load current settings
        mode_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "review_mode.json")
        settings = RejudgeSettings()
        if os.path.exists(mode_file):
            settings = RejudgeSettings.load(mode_file)
        if settings.mode == InteractionMode.REGION_FIRST:
            self._rb_region.setChecked(True)
        else:
            self._rb_image.setChecked(True)
        self._chk_remember.setChecked(settings.remember_last_mode)
        self._chk_auto_next.setChecked(settings.auto_next_after_judge)
        self._chk_region_hl.setChecked(settings.show_region_highlight)

        layout.addStretch()

        btn_save = QPushButton("保存")
        btn_save.setObjectName("btnSave")
        btn_save.clicked.connect(self._save_review_mode)
        layout.addWidget(btn_save)

        return w

    def _save_review_mode(self):
        selected = self._review_mode_group.checkedId()
        mode = InteractionMode.REGION_FIRST if selected == 1 else InteractionMode.IMAGE_FIRST
        settings = RejudgeSettings(
            mode=mode,
            remember_last_mode=self._chk_remember.isChecked(),
            show_region_highlight=self._chk_region_hl.isChecked(),
            auto_next_after_judge=self._chk_auto_next.isChecked(),
        )
        mode_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "review_mode.json")
        settings.save(mode_file)
        mw = self.parent()
        if mw and hasattr(mw, '_mode_manager') and mw._mode_manager:
            mw._mode_manager.switch_mode(mode)
        QMessageBox.information(self, "成功", "复判模式设置已保存，已立即切换")

    def _save_login_mode(self):
        selected = self._login_mode_group.checkedId()
        mode = "password" if selected == 1 else "fingerprint"
        self.config["login_mode"] = mode
        ConfigManager.save(self.config)
        QMessageBox.information(self, "成功", "登录模式已保存，重启应用后生效")
