from typing import Optional, List, Tuple
from database.manager import DBManager
from database.models import (
    StationResult, InspectionDetailEntity,
    Measurement, ApprDefect, DefectDetailInfo,
    FINAL_RESULT_OK, FINAL_RESULT_NG,
)


class QueryResult:
    def __init__(self):
        self.station_result: Optional[StationResult] = None
        self.station_details: List = []
        self.inspection_details: List[InspectionDetailEntity] = []
        self.defect_items: List["DefectListItem"] = []
        self.sr_id: int = 0
        self.source_name: str = ""

    @property
    def final_result(self) -> int:
        if self.station_result:
            return self.station_result.FinalResult
        return 0

    @property
    def has_defects(self) -> bool:
        return len(self.defect_items) > 0


class DefectListItem:
    def __init__(self, display_name: str, source_type: str, source_index: int, detail_index: int = 0, insp_index: int = 0, source_name: str = ""):
        self.display_name = display_name
        self.source_type = source_type
        self.source_index = source_index
        self.detail_index = detail_index
        self.insp_index = insp_index
        self.source_name = source_name

    def __str__(self):
        return self.display_name


RESULT_LABELS = {0: "待检", 1: "OK", 2: "NG"}


class QueryService:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager

    def query_all_sources(self, sn: str, progress_callback=None) -> List[QueryResult]:
        results = []
        if progress_callback:
            progress_callback("查询工单", f"SN={sn}")
        sr_list = self.db.query_station_result(sn)
        for sr, source_name in sr_list:
            if not sr:
                continue
            result = QueryResult()
            result.station_result = sr
            result.sr_id = sr.Id
            result.source_name = source_name
            if progress_callback:
                progress_callback("获取详情", f"来源={source_name}")
            try:
                repo = self.db.get_repository(source_name)
                sd_list, insp_list = repo.find_details_batch(sr.Id)
                result.station_details = sd_list
                if insp_list:
                    result.inspection_details = insp_list
                    if progress_callback:
                        progress_callback("构建缺陷列表", f"{len(insp_list)} 条检测记录")
                    result.defect_items = self._build_defect_list(insp_list)
                    if progress_callback:
                        progress_callback("完成", f"{len(result.defect_items)} 个缺陷")
            except Exception:
                pass
            results.append(result)
        return results

    def query_by_sn(self, sn: str) -> QueryResult:
        results = self.query_all_sources(sn)
        if results:
            return results[0]
        raise ValueError(f"未找到SN [{sn}] 的检测记录")

    def get_result_source(self, sn: str, sr_id: int) -> str:
        sr_list = self.db.query_station_result(sn)
        for sr, source_name in sr_list:
            if sr and sr.Id == sr_id:
                return source_name
        return ""

    def _build_defect_list(self, insp_list: List[InspectionDetailEntity]) -> List[DefectListItem]:
        items = []
        for insp_idx, insp in enumerate(insp_list):
            for i, m in enumerate(insp.Measurements):
                if m.Status and m.Status.lower() in ("ok", "pass", "passed"):
                    continue
                if m.DefectDatas:
                    for j, dd in enumerate(m.DefectDatas):
                        items.append(DefectListItem(
                            display_name=dd.DefectName or m.Reference or f"尺寸{i+1}",
                            source_type="measurement",
                            source_index=i,
                            detail_index=j,
                            insp_index=insp_idx,
                        ))
                else:
                    items.append(DefectListItem(
                        display_name=m.Reference or f"尺寸{i+1}",
                        source_type="measurement",
                        source_index=i,
                        detail_index=0,
                        insp_index=insp_idx,
                    ))
            for i, a in enumerate(insp.Defects):
                if a.Datas:
                    for j, dd in enumerate(a.Datas):
                        items.append(DefectListItem(
                            display_name=dd.DefectName or a.DefectName,
                            source_type="appearance",
                            source_index=i,
                            detail_index=j,
                            insp_index=insp_idx,
                        ))
                else:
                    items.append(DefectListItem(
                        display_name=a.DefectName or f"外观{i+1}",
                        source_type="appearance",
                        source_index=i,
                        detail_index=0,
                        insp_index=insp_idx,
                    ))
        return items

    def get_defect_detail(self, item: DefectListItem, insp_list: List[InspectionDetailEntity]) -> Optional[DefectDetailInfo]:
        if item.insp_index >= len(insp_list):
            return None
        insp = insp_list[item.insp_index]
        if item.source_type == "measurement":
            if item.source_index < len(insp.Measurements):
                m = insp.Measurements[item.source_index]
                if item.detail_index < len(m.DefectDatas):
                    dd = m.DefectDatas[item.detail_index]
                    if not dd.DefectName:
                        dd.DefectName = m.Reference
                    return dd
        else:
            if item.source_index < len(insp.Defects):
                a = insp.Defects[item.source_index]
                if item.detail_index < len(a.Datas):
                    dd = a.Datas[item.detail_index]
                    if not dd.DefectName:
                        dd.DefectName = a.DefectName
                    if not dd.Level:
                        dd.Level = a.Level
                    return dd
        return None

    def query_results_history(self, sn: str) -> List[dict]:
        raw_list = self.db.query_station_results_all(sn)
        return [
            {"Id": r.Id, "CreateTime": str(r.CreateTime or ""),
             "Result": RESULT_LABELS.get(r.FinalResult, "--"),
             "source_name": src}
            for r, src in raw_list
        ]

    def query_history_by_source(self, sn: str, source_name: str) -> List[dict]:
        conn = self.db.get_connection(source_name)
        if not conn or not conn.is_connected():
            return []
        raw_list = conn.query_station_results_all(sn)
        return [
            {"Id": r.Id, "CreateTime": str(r.CreateTime or ""),
             "Result": RESULT_LABELS.get(r.FinalResult, "--"),
             "source_name": source_name}
            for r in raw_list
        ]
