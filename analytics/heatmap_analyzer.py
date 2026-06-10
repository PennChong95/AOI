import json
from datetime import datetime
from typing import Dict, List, Optional
from collections import Counter
from database.manager import DBConnection
from analytics.cache import cached


class HeatmapAnalyzer:
    def __init__(self, conn: DBConnection):
        self.conn = conn

    @cached(key_fn=lambda self, start, end: f"heatmap:{start}:{end}")
    def analyze(self, start: datetime, end: datetime) -> Dict[str, int]:
        tables = self._get_inspection_tables(start, end)
        counter = Counter()
        for table in tables:
            rows = self._fetch_all(
                f"SELECT Measurements, Defects FROM `{table}` WHERE Time BETWEEN %s AND %s",
                (start, end),
            )
            for row in rows:
                self._count_areas(row.get("Measurements"), counter)
                self._count_areas(row.get("Defects"), counter)
        return dict(counter)

    def _count_areas(self, json_str: Optional[str], counter: Counter):
        if not json_str:
            return
        try:
            data = json.loads(json_str) if isinstance(json_str, str) else json_str
        except (json.JSONDecodeError, TypeError):
            return
        if isinstance(data, dict):
            datas = data.get("Datas") or data.get("defectDatas") or []
            for d in datas if isinstance(datas, list) else []:
                area = d.get("ProductArea") or d.get("productArea") or ""
                if area:
                    counter[area] += 1
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    datas = item.get("Datas") or item.get("defectDatas") or []
                    for d in datas if isinstance(datas, list) else []:
                        area = d.get("ProductArea") or d.get("productArea") or ""
                        if area:
                            counter[area] += 1

    def _get_inspection_tables(self, start: datetime, end: datetime) -> list:
        router = self.conn.router
        router.set_time_range(start, end)
        return router._build_table_list("t_inspection_detail")

    def _fetch_all(self, sql: str, params: tuple) -> List[dict]:
        try:
            with self.conn.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception:
            return []