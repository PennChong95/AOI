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

    def _range_custom(self, start_date: str, end_date: str) -> tuple:
        def parse(value: str, is_end: bool = False) -> datetime:
            value = (value or "").strip()
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    pass
            parsed = datetime.strptime(value, "%Y-%m-%d")
            if is_end:
                return parsed.replace(hour=23, minute=59, second=59)
            return parsed

        start = parse(start_date)
        end = parse(end_date, is_end=True)
        if end < start:
            start, end = end, start
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
        start, end = self._range_custom(start_date, end_date)
        analyzer = ImageAnalyzer(conn)
        return analyzer.query_by_filter("Defect", defect_name, start, end, limit)

    def get_by_area_custom_date(self, area: str, start_date: str, end_date: str, limit: int = 20) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range_custom(start_date, end_date)
        analyzer = ImageAnalyzer(conn)
        return analyzer.query_by_filter("Area", area, start, end, limit)

    def get_by_date_range(self, start_date: str, end_date: str, limit: int = 20) -> List[dict]:
        conn = self._get_conn()
        if not conn:
            return []
        start, end = self._range_custom(start_date, end_date)
        analyzer = ImageAnalyzer(conn)
        return analyzer.query_by_filter("Defect", "", start, end, limit)
