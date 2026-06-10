from datetime import datetime
from typing import List
from database.manager import DBConnection
from analytics.cache import cached


class StationAnalyzer:
    def __init__(self, conn: DBConnection):
        self.conn = conn

    @cached(key_fn=lambda self, start, end: f"station_ng:{start}:{end}")
    def station_ng_rates(self, start: datetime, end: datetime) -> List[dict]:
        tables = self._get_tables(start, end)
        station_stats = {}
        for table in tables:
            rows = self._fetch_all(
                f"""SELECT StationName, StationResult, COUNT(*) AS cnt
                    FROM `{table}`
                    WHERE StartTime BETWEEN %s AND %s
                    GROUP BY StationName, StationResult""",
                (start, end),
            )
            for row in rows:
                name = row["StationName"] or "未知"
                if name not in station_stats:
                    station_stats[name] = {"total": 0, "ng": 0}
                station_stats[name]["total"] += row["cnt"]
                if row["StationResult"] in ("NG", "Failed", "2"):
                    station_stats[name]["ng"] += row["cnt"]
        result = []
        for name, stats in station_stats.items():
            ng_rate = round(stats["ng"] / stats["total"] * 100, 1) if stats["total"] else 0
            result.append({
                "name": name,
                "total": stats["total"],
                "ng": stats["ng"],
                "ng_rate": ng_rate,
            })
        result.sort(key=lambda x: x["ng_rate"], reverse=True)
        return result

    def _get_tables(self, start: datetime, end: datetime) -> list:
        router = self.conn.router
        router.set_time_range(start, end)
        return router._build_table_list("t_station_detail")

    def _fetch_all(self, sql: str, params: tuple) -> List[dict]:
        try:
            with self.conn.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception:
            return []