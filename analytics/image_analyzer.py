import json
from datetime import datetime
from typing import List, Optional
from analytics.cache import cached


class ImageAnalyzer:
    def __init__(self, conn):
        self.conn = conn

    @cached(key_fn=lambda self, filter_type, filter_value, start, end, limit=20:
            f"image:{filter_type}:{filter_value}:{start}:{end}:{limit}")
    def query_by_filter(self, filter_type: str, filter_value, start: datetime, end: datetime, limit: int = 20) -> List[dict]:
        tables = self._get_tables(start, end)
        results = []

        for table in tables:
            rows = self._fetch_all(
                f"SELECT Id, Sn, StationNo, SingleImagePath, ImageWidth, ImageHeight, "
                f"Measurements, Defects, Result, Time "
                f"FROM `{table}` "
                f"WHERE Time BETWEEN %s AND %s AND Result = 2 "
                f"ORDER BY Time DESC LIMIT %s",
                (start, end, limit),
            )
            for row in rows:
                matched_items = self._match_defects(row, filter_type, filter_value)
                for item in matched_items:
                    results.append(item)
                    if len(results) >= limit:
                        return results[:limit]

        return results[:limit]

    def _match_defects(self, row: dict, filter_type: str, filter_value) -> List[dict]:
        matched = []
        for json_field in ["Measurements", "Defects"]:
            raw = row.get(json_field)
            if not raw:
                continue
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                continue
            datas = []
            if isinstance(data, dict):
                datas = data.get("Datas") or data.get("defectDatas") or []
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        datas.extend(item.get("Datas") or item.get("defectDatas") or [])

            for d in datas:
                if not isinstance(d, dict):
                    continue
                if filter_type == "Defect":
                    name = d.get("DefectName") or d.get("defectName") or ""
                    if name != filter_value:
                        continue
                elif filter_type == "Area":
                    area = d.get("ProductArea") or d.get("productArea") or ""
                    if area != filter_value:
                        continue

                box = d.get("BoundingRect") or d.get("boundingRect") or {}
                matched.append({
                    "image_id": str(row.get("Id")),
                    "sn": row.get("Sn") or "",
                    "station": row.get("StationNo") or "",
                    "image_path": d.get("DefectImagePath") or row.get("SingleImagePath") or "",
                    "image_width": row.get("ImageWidth") or 0,
                    "image_height": row.get("ImageHeight") or 0,
                    "defect_name": d.get("DefectName") or d.get("defectName") or "",
                    "defect_area": d.get("ProductArea") or d.get("productArea") or "",
                    "defect_box": (
                        box.get("X", 0),
                        box.get("Y", 0),
                        box.get("X", 0) + box.get("Width", 0),
                        box.get("Y", 0) + box.get("Height", 0),
                    ),
                    "time": str(row.get("Time") or ""),
                    "result": row.get("Result", 0),
                })
        return matched

    def _get_tables(self, start: datetime, end: datetime) -> list:
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
