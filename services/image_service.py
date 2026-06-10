from datetime import datetime, timedelta
from typing import List, Optional
from database.manager import DBManager
from analytics.image_analyzer import ImageAnalyzer


class ImageService:
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager

    def _get_conn(self):
        return self.db_manager.get_first_connected()

    def _range(self, days: int) -> tuple:
        end = datetime.now()
        if days == 0:
            start = datetime(end.year, end.month, end.day)
        elif days == -1:
            start = datetime(end.year, end.month, 1)
        else:
            start = end - timedelta(days=days)
        return start, end

    def get_by_defect(self, defect_name: str, days: int = 0, limit: int = 20) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range(days)
        analyzer = ImageAnalyzer(conn)
        return analyzer.query_by_filter("Defect", defect_name, start, end, limit)

    def get_by_area(self, area: str, days: int = 0, limit: int = 20) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range(days)
        analyzer = ImageAnalyzer(conn)
        return analyzer.query_by_filter("Area", area, start, end, limit)

    def get_by_defect_custom_date(self, defect_name: str, start_date: str, end_date: str, limit: int = 20) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        analyzer = ImageAnalyzer(conn)
        return analyzer.query_by_filter("Defect", defect_name, start, end, limit)

    def get_by_area_custom_date(self, area: str, start_date: str, end_date: str, limit: int = 20) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        analyzer = ImageAnalyzer(conn)
        return analyzer.query_by_filter("Area", area, start, end, limit)

    def get_by_date_range(self, start_date: str, end_date: str, limit: int = 20) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        analyzer = ImageAnalyzer(conn)
        return analyzer.query_by_filter("Defect", "", start, end, limit)
