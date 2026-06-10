from datetime import datetime
from typing import List, Optional
import logging
from database.manager import DBConnection
from analytics.cache import cached


logger = logging.getLogger(__name__)


class YieldAnalyzer:
    def __init__(self, conn: DBConnection):
        self.conn = conn

    @cached(key_fn=lambda self, start, end: f"yield_kpi:{start}:{end}")
    def kpi(self, start: datetime, end: datetime) -> dict:
        metrics = self._aggregate_kpi(start, end)
        total = metrics["total"]
        ok = metrics["ok"]
        ng = metrics["ng"]
        review_ok = metrics["review_ok"]
        review_ng = metrics["review_ng"]
        effective_ok = metrics["effective_ok"]
        return {
            "total": total,
            "ok": ok,
            "ng": ng,
            "yield_rate": round(ok / total * 100, 1) if total else 0,
            "review_ok": review_ok,
            "review_ng": review_ng,
            "post_review_yield_rate": round(effective_ok / total * 100, 1) if total else 0,
        }

    def _aggregate_kpi(self, start: datetime, end: datetime) -> dict:
        tables = self._get_tables(start, end)
        result = {"total": 0, "ok": 0, "ng": 0, "review_ok": 0, "review_ng": 0, "effective_ok": 0}
        for table in tables:
            sql = f"""
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(CASE WHEN FinalResult = 1 THEN 1 ELSE 0 END), 0) AS ok,
                       COALESCE(SUM(CASE WHEN FinalResult = 2 THEN 1 ELSE 0 END), 0) AS ng,
                       COALESCE(SUM(CASE WHEN ReviewResult = 1 THEN 1 ELSE 0 END), 0) AS review_ok,
                       COALESCE(SUM(CASE WHEN ReviewResult = 2 THEN 1 ELSE 0 END), 0) AS review_ng,
                       COALESCE(SUM(CASE
                           WHEN ReviewResult = 1 THEN 1
                           WHEN ReviewResult = 2 THEN 0
                           WHEN FinalResult  = 1 THEN 1
                           ELSE 0
                       END), 0) AS effective_ok
                FROM `{table}`
                WHERE CreateTime BETWEEN %s AND %s
            """
            row = self._fetch_one(sql, (start, end))
            if row:
                for key in result:
                    result[key] += int(row.get(key) or 0)
        return result

    @cached(key_fn=lambda self, start, end, granularity: f"yield_trend:{start}:{end}:{granularity}")
    def trend(self, start: datetime, end: datetime, granularity: str = "day") -> List[dict]:
        tables = self._get_tables(start, end)
        if not tables:
            return []
        if granularity == "hour":
            fmt = "%Y-%m-%d %H:00:00"
        elif granularity == "minute":
            fmt = "%Y-%m-%d %H:%i"
        elif granularity == "day":
            fmt = "%Y-%m-%d"
        elif granularity == "week":
            fmt = "%Y-%u"
        else:
            fmt = "%Y-%m"

        results = []
        fmt_escaped = fmt.replace('%', '%%')
        for table in tables:
            sql = f"""
                SELECT DATE_FORMAT(CreateTime, '{fmt_escaped}') AS period,
                       COUNT(*) AS total,
                       SUM(CASE WHEN FinalResult = 1 THEN 1 ELSE 0 END) AS ok,
                       SUM(CASE WHEN FinalResult = 2 THEN 1 ELSE 0 END) AS ng,
                       SUM(CASE
                           WHEN ReviewResult = 1 THEN 1
                           WHEN ReviewResult = 2 THEN 0
                           WHEN FinalResult  = 1 THEN 1
                           ELSE 0
                       END) AS effective_ok
                FROM `{table}`
                WHERE CreateTime BETWEEN %s AND %s
                GROUP BY period ORDER BY period
            """
            rows = self._fetch_all(sql, (start, end))
            results.extend(rows)
        return self._merge_results(results)

    def _count_effective(self, start: datetime, end: datetime) -> dict:
        """有效结果计数：ReviewResult优先，否则FinalResult"""
        tables = self._get_tables(start, end)
        total = 0
        ok = 0
        for table in tables:
            sql = f"""
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(CASE
                           WHEN ReviewResult = 1 THEN 1
                           WHEN ReviewResult = 2 THEN 0
                           WHEN FinalResult  = 1 THEN 1
                           ELSE 0
                       END), 0) AS ok
                FROM `{table}`
                WHERE CreateTime BETWEEN %s AND %s
            """
            row = self._fetch_one(sql, (start, end))
            if row:
                total += int(row["total"])
                ok += int(row["ok"])
        return {"total": total, "ok": ok}

    def _count(self, prefix: str, start: datetime, end: datetime,
               final_result: int = None, review_result: int = None) -> int:
        tables = self._get_tables(start, end)
        total = 0
        for table in tables:
            where = "WHERE CreateTime BETWEEN %s AND %s"
            params = [start, end]
            if final_result is not None:
                where += " AND FinalResult = %s"
                params.append(final_result)
            if review_result is not None:
                where += " AND ReviewResult = %s"
                params.append(review_result)
            sql = f"SELECT COUNT(*) AS cnt FROM `{table}` {where}"
            row = self._fetch_one(sql, tuple(params))
            if row:
                total += int(row["cnt"])
        return total

    def _get_tables(self, start: datetime, end: datetime) -> list:
        yield_analysis = self.conn.router
        yield_analysis.set_time_range(start, end)
        return yield_analysis._build_table_list("t_station_result")

    def _fetch_one(self, sql: str, params: tuple) -> Optional[dict]:
        try:
            with self.conn.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()
        except Exception as exc:
            logger.warning("yield fetch_one failed: error=%s", exc)
            return None

    def _fetch_all(self, sql: str, params: tuple) -> List[dict]:
        try:
            with self.conn.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as exc:
            logger.warning("yield fetch_all failed: error=%s", exc)
            return []

    def _merge_results(self, results: List[dict]) -> List[dict]:
        merged = {}
        for r in results:
            period = r["period"]
            if period in merged:
                merged[period]["total"] += r["total"]
                merged[period]["ok"] += r["ok"]
                merged[period]["ng"] += r["ng"]
                merged[period]["effective_ok"] = merged[period].get("effective_ok", 0) + (r.get("effective_ok") or 0)
            else:
                merged[period] = dict(r)
        sorted_periods = sorted(merged.keys())
        out = []
        for p in sorted_periods:
            d = merged[p]
            d["yield_rate"] = round(d["ok"] / d["total"] * 100, 1) if d["total"] else 0
            d["post_review_yield_rate"] = round(d.get("effective_ok", 0) / d["total"] * 100, 1) if d["total"] else 0
            out.append(d)
        return out
