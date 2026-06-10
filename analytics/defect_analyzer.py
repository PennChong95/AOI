import json
import logging
from datetime import datetime
from typing import List, Optional, Dict
from collections import Counter
from database.manager import DBConnection
from analytics.cache import cached


logger = logging.getLogger(__name__)


class DefectAnalyzer:
    def __init__(self, conn: DBConnection):
        self.conn = conn

    @cached(key_fn=lambda self, start, end, top_n=10: f"defect_top:{start}:{end}:{top_n}")
    def top_defects(self, start: datetime, end: datetime, top_n: int = 10) -> List[dict]:
        tables = self._get_inspection_tables(start, end)
        counter = Counter()
        for table in tables:
            rows = self._fetch_all(
                f"SELECT Measurements, Defects FROM `{table}` WHERE Time BETWEEN %s AND %s",
                (start, end),
            )
            for row in rows:
                self._count_defects(row.get("Measurements"), counter)
                self._count_defects(row.get("Defects"), counter)
        total = sum(counter.values())
        top = counter.most_common(top_n)
        others = total - sum(count for _, count in top)
        result = []
        for name, count in top:
            result.append({"name": name, "count": count, "pct": round(count / total * 100, 1) if total else 0})
        if others > 0 and top_n > 0:
            result.append({"name": "其他", "count": others, "pct": round(others / total * 100, 1) if total else 0})
        return result

    def _count_defects(self, json_str: Optional[str], counter: Counter):
        if not json_str:
            return
        try:
            data = json.loads(json_str) if isinstance(json_str, str) else json_str
        except (json.JSONDecodeError, TypeError):
            return
        if isinstance(data, dict):
            datas = data.get("Datas") or data.get("DefectDatas") or data.get("defectDatas") or []
            for d in datas if isinstance(datas, list) else []:
                name = d.get("DefectName") or d.get("defectName") or ""
                if name:
                    counter[name] += 1
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    datas = item.get("Datas") or item.get("DefectDatas") or item.get("defectDatas") or []
                    for d in datas if isinstance(datas, list) else []:
                        name = d.get("DefectName") or d.get("defectName") or ""
                        if name:
                            counter[name] += 1

    def defect_distribution(self, start: datetime, end: datetime, top_n: int = 10) -> List[dict]:
        """
        获取缺陷分布（饼图用）
        
        Returns:
            [{"name": str, "count": int, "pct": float}, ...]
        """
        return self.top_defects(start, end, top_n)

    def recent_records(self, start: datetime, end: datetime, limit: int = 20, result_filter: str = "ng") -> List[dict]:
        """
        获取最近检测记录
        
        Args:
            start: 开始时间
            end: 结束时间
            limit: 记录数量
            result_filter: "ng" | "ok" | "all"
            
        Returns:
            [{"time": str, "sn": str, "product": str, "defect": str, "station": str, "result": str}, ...]
        """
        tables = self._get_inspection_tables(start, end)
        records = []
        
        for table in tables:
            # 构建查询条件
            where_clause = "WHERE Time BETWEEN %s AND %s"
            params = [start, end]
            
            if result_filter == "ng":
                where_clause += " AND Result = 2"
            elif result_filter == "ok":
                where_clause += " AND Result = 1"
            
            where_clause += " ORDER BY Time DESC LIMIT %s"
            params.append(limit)
            
            rows = self._fetch_all(
                f"SELECT Sn, StationNo, Result, Measurements, Defects, Time FROM `{table}` {where_clause}",
                tuple(params),
            )
            
            for row in rows:
                # 解析缺陷信息
                defect_names = []
                for json_str in [row.get("Measurements"), row.get("Defects")]:
                    if json_str:
                        try:
                            data = json.loads(json_str) if isinstance(json_str, str) else json_str
                            if isinstance(data, dict):
                                datas = data.get("Datas") or data.get("DefectDatas") or data.get("defectDatas") or []
                                for d in datas if isinstance(datas, list) else []:
                                    name = d.get("DefectName") or d.get("defectName") or ""
                                    if name and name not in defect_names:
                                        defect_names.append(name)
                            elif isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        datas = item.get("Datas") or item.get("DefectDatas") or item.get("defectDatas") or []
                                        for d in datas if isinstance(datas, list) else []:
                                            name = d.get("DefectName") or d.get("defectName") or ""
                                            if name and name not in defect_names:
                                                defect_names.append(name)
                        except (json.JSONDecodeError, TypeError) as exc:
                            logger.debug("recent record defect json parse failed: error=%s", exc)
                
                result_val = row.get("Result", 0)
                records.append({
                    "time": row.get("Time", ""),
                    "sn": row.get("Sn", ""),
                    "product": "",  # 需要从station_result表获取
                    "defect": ", ".join(defect_names) if defect_names else "-",
                    "station": row.get("StationNo", ""),
                    "result": "NG" if result_val == 2 else "OK" if result_val == 1 else "未知",
                })
        
        # 按时间排序并限制数量
        records.sort(key=lambda x: x["time"], reverse=True)
        return records[:limit]

    def _get_inspection_tables(self, start: datetime, end: datetime) -> list:
        router = self.conn.router
        router.set_time_range(start, end)
        return router._build_table_list("t_inspection_detail")

    def _fetch_all(self, sql: str, params: tuple) -> List[dict]:
        try:
            with self.conn.connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as exc:
            logger.warning("defect query failed: error=%s", exc)
            return []
