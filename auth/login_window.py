from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QApplication, QWidget, QStackedWidget, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QRectF
from PyQt5.QtGui import QFont, QPainter, QPen, QColor
from utils.config_manager import (
    UserManager, LogManager,
    ConfigManager, ROLE_ADMIN,
    can_login_with_password,
)
from utils.ui_utils import scale_css, sf, sp
from services.fingerprint_service import fingerprint_service, ZKFP_ERR_OK, ZKFP_ERR_NO_DEVICE


LOGIN_MODE_CONFIG = "login_mode"
LOGIN_MODE_FINGERPRINT = ConfigManager.LOGIN_MODE_FINGERPRINT
LOGIN_MODE_PASSWORD = ConfigManager.LOGIN_MODE_PASSWORD


class FingerprintIcon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 100)
        self._anim_offset = 0

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2 - 4
        pen = QPen(QColor("#4F6CF7"), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawEllipse(QRectF(cx - 22, cy - 26, 44, 52))
        for r in range(5, 22, 4):
            p.drawArc(int(cx - r), int(cy - r - 6), int(r * 2), int(r * 2 + 12), 30 * 16, 120 * 16)
            p.drawArc(int(cx - r), int(cy - r - 6), int(r * 2), int(r * 2 + 12), -150 * 16, 120 * 16)
        pen.setWidth(1)
        p.setPen(pen)
        p.drawArc(int(cx - 8), int(cy + 12), 16, 12, 0, 180 * 16)
        p.end()


class LoginWindow(QDialog):
    login_success = pyqtSignal(object, str, str)

    PAGE_FINGERPRINT = 0
    PAGE_PASSWORD = 1

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user = None
        self._fp_initialized = False
        self._login_mode = ConfigManager.load().get(LOGIN_MODE_CONFIG, LOGIN_MODE_FINGERPRINT)
        self.setWindowTitle("检测结果复判系统 - 登录")
        self.setStyleSheet(self._style())

        if self._login_mode == LOGIN_MODE_PASSWORD:
            self.setFixedSize(sp(400), sp(300))
            self._build_password_ui()
        else:
            self.setFixedSize(sp(420), sp(420))
            self._setup_fp_ui()
            self._init_fingerprint()

    def _style(self):
        return scale_css("""
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
        QPushButton#btnLogin {
            background-color: #4F6CF7; color: white;
        }
        QPushButton#btnLogin:hover { background-color: #3B5DE7; }
        QPushButton#btnBack {
            background-color: #EDF2F7; color: #4A5568;
        }
        QPushButton#btnBack:hover { background-color: #E2E8F0; }
        QPushButton#btnPwdSwitch {
            background-color: #EDF2F7; color: #4A5568;
            font-size: 13px; min-height: 20px;
        }
        QPushButton#btnPwdSwitch:hover { background-color: #E2E8F0; }
        QFrame#fpFrame {
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 16px;
            padding: 16px;
        }
        """)

    # ── Fingerprint mode UI ──

    def _setup_fp_ui(self):
        self._stack = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)
        self._stack.addWidget(self._build_fingerprint_page())
        self._stack.addWidget(self._build_password_page())

    def _build_fingerprint_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(40, 24, 40, 24)

        title = QLabel("检测结果复判系统")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #4F6CF7; font-size: 22px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(title)

        layout.addSpacing(8)

        fp_frame = QFrame()
        fp_frame.setObjectName("fpFrame")
        fp_layout = QVBoxLayout(fp_frame)
        fp_layout.setAlignment(Qt.AlignCenter)
        fp_layout.setSpacing(6)

        self._fp_icon = FingerprintIcon()
        fp_layout.addWidget(self._fp_icon, 0, Qt.AlignCenter)

        self._fp_prompt = QLabel("请按压手指到指纹采集器")
        self._fp_prompt.setAlignment(Qt.AlignCenter)
        self._fp_prompt.setStyleSheet("color: #4F6CF7; font-size: 14px; font-weight: 600;")
        fp_layout.addWidget(self._fp_prompt)

        self._fp_status = QLabel("等待指纹...")
        self._fp_status.setAlignment(Qt.AlignCenter)
        self._fp_status.setStyleSheet("color: #94A3B8; font-size: 12px;")
        fp_layout.addWidget(self._fp_status)

        layout.addWidget(fp_frame)

        layout.addSpacing(4)

        or_label = QLabel("或")
        or_label.setAlignment(Qt.AlignCenter)
        or_label.setStyleSheet("color: #94A3B8; font-size: 12px; margin: 2px 0px;")
        layout.addWidget(or_label)

        btn_pwd = QPushButton("使用系统管理员密码登录")
        btn_pwd.setObjectName("btnPwdSwitch")
        btn_pwd.clicked.connect(self._switch_to_password)
        layout.addWidget(btn_pwd)

        layout.addStretch()

        version_label = QLabel("v4.1")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        layout.addWidget(version_label)

        return page

    def _build_password_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 30, 40, 30)

        title = QLabel("管理员密码登录")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #4F6CF7; font-size: 20px; font-weight: 700; margin-bottom: 8px;")
        layout.addWidget(title)

        subtitle = QLabel("仅限管理员账户使用")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #64748B; font-size: 12px; margin-bottom: 4px;")
        layout.addWidget(subtitle)

        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("管理员用户名")
        layout.addWidget(self.input_user)

        self.input_pass = QLineEdit()
        self.input_pass.setPlaceholderText("管理员密码")
        self.input_pass.setEchoMode(QLineEdit.Password)
        self.input_pass.returnPressed.connect(self._password_login)
        layout.addWidget(self.input_pass)

        btn_login = QPushButton("登 录")
        btn_login.setObjectName("btnLogin")
        btn_login.clicked.connect(self._password_login)
        layout.addWidget(btn_login)

        btn_back = QPushButton("返回")
        btn_back.setObjectName("btnBack")
        btn_back.clicked.connect(self._switch_to_fingerprint)
        layout.addWidget(btn_back)

        layout.addStretch()
        return page

    def _init_fingerprint(self):
        users = UserManager.load_users()
        ret = fingerprint_service.ensure_device_ready(users)
        if ret == ZKFP_ERR_OK:
            self._fp_initialized = True
            LogManager.log_fingerprint_init(True, "device ready")
            self._start_fingerprint_scan()
        else:
            self._fp_initialized = False
            if ret == ZKFP_ERR_NO_DEVICE:
                self._fp_status.setText("未检测到指纹设备")
            else:
                self._fp_status.setText(f"指纹设备初始化失败({ret})")
            self._fp_prompt.setText("指纹登录不可用")
            self._fp_prompt.setStyleSheet("color: #EF4444; font-size: 14px; font-weight: 600;")
            LogManager.log_fingerprint_init(False, f"ensure_device_ready returned {ret}")

    def _switch_to_fingerprint(self):
        self._stack.setCurrentIndex(self.PAGE_FINGERPRINT)
        users = UserManager.load_users()
        fingerprint_service.ensure_device_ready(users)
        if fingerprint_service.is_available:
            self._fp_initialized = True
            self._start_fingerprint_scan()
        else:
            self._fp_initialized = False
            self._fp_status.setText("指纹设备不可用")

    def _switch_to_password(self):
        self._stop_fp_scan()
        fingerprint_service.release_device()
        self.input_user.clear()
        self.input_pass.clear()
        self._stack.setCurrentIndex(self.PAGE_PASSWORD)
        self.input_user.setFocus()

    def _start_fingerprint_scan(self):
        self._fp_prompt.setText("请按压手指到指纹采集器")
        self._fp_prompt.setStyleSheet("color: #4F6CF7; font-size: 14px; font-weight: 600;")
        self._fp_status.setText("等待指纹...")
        self._fp_status.setStyleSheet("color: #94A3B8; font-size: 12px;")
        QApplication.processEvents()

        self._fp_timer = QTimer(self)
        self._fp_timer.setSingleShot(True)
        self._fp_timer.timeout.connect(self._do_fingerprint_capture)
        self._fp_timeout_count = 0
        self._fp_timer.start(300)

    def _stop_fp_scan(self):
        if hasattr(self, '_fp_timer') and self._fp_timer:
            self._fp_timer.stop()

    def _do_fingerprint_capture(self):
        if not self._fp_initialized:
            self._fp_status.setText("指纹设备未就绪")
            return

        ret, template, image = fingerprint_service.acquire_fingerprint()
        if ret == ZKFP_ERR_OK and template:
            self._on_fingerprint_captured(template)
        else:
            self._fp_timeout_count += 1
            if self._fp_timeout_count > 100:
                self._fp_status.setText("等待指纹按压...")
                self._fp_timeout_count = 0
            self._fp_timer.start(300)

    def _on_fingerprint_captured(self, template: bytes):
        self._fp_prompt.setText("验证中...")
        self._fp_status.setText("正在验证指纹...")
        QApplication.processEvents()

        import base64
        users = UserManager.load_users()
        matched_user = None
        matched_score = 0

        for u in users:
            stored_b64 = u.get("fingerprint_template", "")
            if not stored_b64:
                continue
            try:
                stored_tpl = base64.b64decode(stored_b64)
                score = fingerprint_service.db_match(template, stored_tpl)
                if score > matched_score:
                    matched_score = score
                    matched_user = u
            except Exception:
                continue

        if matched_user and matched_score > 0:
            self.current_user = matched_user
            username = matched_user["username"]
            role = matched_user.get("role", ROLE_ADMIN)
            LogManager.log_login(username, "fingerprint", True)
            LogManager.log_fingerprint_identify(username, True, f"score={matched_score}")
            self.login_success.emit(self.db_manager, username, role)
            self.accept()
        else:
            self._fp_prompt.setText("指纹验证失败")
            self._fp_status.setText("未匹配到用户，请重试")
            self._fp_prompt.setStyleSheet("color: #EF4444; font-size: 14px; font-weight: 600;")
            LogManager.log_fingerprint_identify("unknown", False, "no matching template")
            QApplication.processEvents()
            import time
            time.sleep(1.5)
            self._start_fingerprint_scan()

    # ── Password mode UI ──

    def _build_password_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 30, 40, 30)

        title = QLabel("检测结果复判系统")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #4F6CF7; font-size: 22px; font-weight: 700; letter-spacing: 1px;")
        layout.addWidget(title)

        layout.addSpacing(12)

        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("用户名")
        layout.addWidget(self.input_user)

        self.input_pass = QLineEdit()
        self.input_pass.setPlaceholderText("密码")
        self.input_pass.setEchoMode(QLineEdit.Password)
        self.input_pass.returnPressed.connect(self._password_login)
        layout.addWidget(self.input_pass)

        btn_login = QPushButton("登 录")
        btn_login.setObjectName("btnLogin")
        btn_login.clicked.connect(self._password_login)
        layout.addWidget(btn_login)

        layout.addStretch()

        version_label = QLabel("v4.1")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        layout.addWidget(version_label)

    # ── Shared login logic ──

    def _password_login(self):
        username = self.input_user.text().strip()
        password = self.input_pass.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return

        try:
            users = UserManager.load_users()
            user = None
            for u in users:
                if u["username"] == username:
                    user = u
                    break

            if not user:
                LogManager.log_login(username, "password", False)
                QMessageBox.warning(self, "登录失败", "用户名或密码错误")
                return

            if self._login_mode == LOGIN_MODE_PASSWORD:
                stored_pwd = user.get("password", "")
                if not stored_pwd:
                    LogManager.log_login(username, "password", False)
                    QMessageBox.warning(
                        self, "登录失败",
                        "当前系统为密码登录模式，\n该账号未设置登录密码，\n请联系管理员。",
                    )
                    return

                if user.get("password") != password:
                    LogManager.log_login(username, "password", False)
                    QMessageBox.warning(self, "登录失败", "用户名或密码错误")
                    return
            else:
                if not can_login_with_password(user.get("role", "")):
                    QMessageBox.warning(self, "登录失败", "该账户不允许使用密码登录")
                    return
                if user.get("password") != password:
                    LogManager.log_login(username, "password", False)
                    QMessageBox.warning(self, "登录失败", "用户名或密码错误")
                    return

            self.current_user = user
            role = user.get("role", ROLE_ADMIN)
            LogManager.log_login(username, "password", True)
            self.login_success.emit(self.db_manager, username, role)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"登录失败: {e}")

    def reject(self):
        LogManager.log_logout(self.current_user["username"] if self.current_user else "unknown")
        super().reject()

    def closeEvent(self, event):
        if self._login_mode == LOGIN_MODE_FINGERPRINT:
            self._stop_fp_scan()
            fingerprint_service.release_device()
        super().closeEvent(event)
