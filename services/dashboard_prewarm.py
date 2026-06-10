import logging
from PyQt5.QtCore import QThread, pyqtSignal

from database.manager import DBManager
from services.dashboard_service import DashboardService
from utils.config_manager import ConfigManager


logger = logging.getLogger(__name__)


class DashboardPrewarmThread(QThread):
    finished_with_status = pyqtSignal(bool, str)

    def __init__(self, db_configs: list = None, parent=None):
        super().__init__(parent)
        self._db_configs = db_configs

    def run(self):
        db_manager = None
        try:
            configs = self._db_configs
            if configs is None:
                configs = ConfigManager.get_databases(ConfigManager.load())
            db_manager = DBManager(configs)
            ok, errors = db_manager.connect_all()
            if not ok:
                message = "; ".join(errors) if errors else "no connected dashboard data source"
                logger.warning("dashboard prewarm skipped: %s", message)
                self.finished_with_status.emit(False, message)
                return
            DashboardService(db_manager).prewarm_common_ranges()
            self.finished_with_status.emit(True, "dashboard cache prewarmed")
        except Exception as exc:
            logger.exception("dashboard cache prewarm failed")
            self.finished_with_status.emit(False, str(exc))
        finally:
            if db_manager is not None:
                db_manager.disconnect_all()
