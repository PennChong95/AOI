import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from database.manager import DBConnection
from analytics.cache import cached


class TrendAnalyzer:
    def __init__(self, conn: DBConnection):
        self.conn = conn

    @cached(key_fn=lambda self, start, end: f"defect_trend:{start}:{end}")
    def defect_trend(self, start: datetime, end: datetime, top_n: int = 5) -> Dict[str, List]:
        tables = self._get_inspection_tables(start, end)
        daily = defaultdict(lambda: defaultdict(int))
        for table in tables:
            rows = self._fetch_all(
                f"SELECT Time, Measurements, Defects FROM `{table}` WHERE Time BETWEEN %s AND %s",
                (start, end),
            )
            for row in rows:
                day = row["Time"].strftime("%Y-%m-%d") if hasattr(row["Time"], "strftime") else str(row["Time"])[:10]
                self._count_by_day(row.get("Measurements"), daily, day)
                self._count_by_day(row.get("Defects"), daily, day)

        # Get top N defect names overall
        total = defaultdict(int)
        for day_counts in daily.values():
            for name, count in day_counts.items():
                total[name] += count
        top_names = sorted(total, key=total.get, reverse=True)[:top_n]
        if not top_names:
            return {"dates": [], "series": []}

        dates = sorted(daily.keys())
        series = []
        for name in top_names:
            data = [daily[d].get(name, 0) for d in dates]
            series.append({"name": name, "data": data})

        return {"dates": dates, "series": series}

    def _count_by_day(self, json_str: Optional[str], daily: defaultdict, day: str):
        if not json_str:
            return
        try:
            data = json.loads(json_str) if isinstance(json_str, str) else json_str
        except (json.JSONDecodeError, TypeError):
            return
        if isinstance(data, dict):
            datas = data.get("Datas") or data.get("defectDatas") or []
            for d in datas if isinstance(datas, list) else []:
                name = d.get("DefectName") or d.get("defectName") or ""
                if name:
                    daily[day][name] += 1
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    datas = item.get("Datas") or item.get("defectDatas") or []
                    for d in datas if isinstance(datas, list) else []:
                        name = d.get("DefectName") or d.get("defectName") or ""
                        if name:
                            daily[day][name] += 1

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