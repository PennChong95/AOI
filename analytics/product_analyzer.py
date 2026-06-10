from datetime import datetime
from typing import List
from database.manager import DBConnection
from analytics.cache import cached


class ProductAnalyzer:
    def __init__(self, conn: DBConnection):
        self.conn = conn

    @cached(key_fn=lambda self, start, end: f"product_rank:{start}:{end}")
    def product_ranking(self, start: datetime, end: datetime, top_n: int = 20) -> List[dict]:
        tables = self._get_tables(start, end)
        product_stats = {}
        for table in tables:
            rows = self._fetch_all(
                f"""SELECT ProductType,
                           COUNT(*) AS total,
                           SUM(CASE WHEN FinalResult = 1 THEN 1 ELSE 0 END) AS ok,
                           SUM(CASE WHEN FinalResult = 2 THEN 1 ELSE 0 END) AS ng
                    FROM `{table}`
                    WHERE CreateTime BETWEEN %s AND %s
                      AND ProductType IS NOT NULL AND ProductType != ''
                    GROUP BY ProductType
                    ORDER BY total DESC""",
                (start, end),
            )
            for row in rows:
                pt = row["ProductType"]
                if pt not in product_stats:
                    product_stats[pt] = {"total": 0, "ok": 0, "ng": 0}
                product_stats[pt]["total"] += row["total"]
                product_stats[pt]["ok"] += row["ok"]
                product_stats[pt]["ng"] += row["ng"]
        result = []
        for name, stats in product_stats.items():
            yield_rate = round(stats["ok"] / stats["total"] * 100, 1) if stats["total"] else 0
            result.append({
                "name": name,
                "total": stats["total"],
                "ok": stats["ok"],
                "ng": stats["ng"],
                "yield_rate": yield_rate,
            })
        result.sort(key=lambda x: x["total"], reverse=True)
        return result[:top_n]

    def _get_tables(self, start: datetime, end: datetime) -> list:
        router = self.conn.router
        router.set_time_range(start, end)
        return router._build_table_list("t_station_result")

    def _fetch_all(self, sql: str, params: tuple) -> List[dict]:
        try:
            with self.conn.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception:
            return []