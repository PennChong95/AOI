import sys
import os

os.environ["PYQTGRAPH_QT_LIB"] = "PyQt5"

import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView  #noqa: ensure loaded before QApplication
except ImportError:
    pass

from utils.icon_data import get_icon
from utils.ui_utils import init_scale_factor, sf, sp
from database.manager import DBManager
from utils.config_manager import ConfigManager, LogManager
from auth.login_window import LoginWindow
from review.main_window import MainWindow


def main():
    LogManager.setup_logging()
    pg.setConfigOptions(imageAxisOrder='row-major')

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    init_scale_factor()
    base_size = max(8, sp(10))
    font = QFont("Segoe UI", base_size)
    font.setFamilies(["Inter", "Segoe UI", "PingFang SC", "Microsoft YaHei UI", "sans-serif"])
    app.setFont(font)
    app.setApplicationName("AOI复判系统")
    app.setApplicationVersion("4.1")
    app.setWindowIcon(get_icon())

    config = ConfigManager.load()
    db_configs = ConfigManager.get_databases(config)

    db_manager = DBManager(db_configs)
    db_ok = True
    err_msgs = []
    try:
        ok, errors = db_manager.connect_all()
        db_ok = ok
        err_msgs = errors
    except Exception as exc:
        LogManager.log_exception("数据库连接初始化异常", exc)

    if not db_ok:
        detail = "\n".join(err_msgs) if err_msgs else str(err_msgs)
        ret = QMessageBox.question(
            None, "数据库连接失败",
            f"部分数据库无法连接:\n{detail}\n\n是否前往设置页面重新配置？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if ret == QMessageBox.Yes:
            from ui.dialogs.settings_dialog import SettingsWindow
            settings = SettingsWindow(db_manager, parent=None)
            settings.exec_()
            config = ConfigManager.load()
            db_configs = ConfigManager.get_databases(config)
            try:
                db_manager = DBManager(db_configs)
                db_manager.connect_all()
                db_ok = True
            except Exception as exc:
                LogManager.log_exception("设置后数据库重连失败", exc)
                QMessageBox.critical(None, "错误", "仍然无法连接数据库，程序将退出。")
                sys.exit(1)
        else:
            sys.exit(1)

    login = LoginWindow(db_manager)
    user_info = {}

    def on_login_success(_db, username, role):
        user_info["username"] = username
        user_info["role"] = role

    login.login_success.connect(on_login_success)

    if login.exec_() != LoginWindow.Accepted:
        db_manager.disconnect_all()
        sys.exit(0)

    window = MainWindow(db_manager, user_info.get("username", ""), user_info.get("role", ""))
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
