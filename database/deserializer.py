from functools import lru_cache
from typing import List, Optional
from database.models import (
    InspectionDetailEntity, StationDetail, Measurement, ApprDefect,
    DefectDetailInfo, PointInt, RectangleInt,
    measurement_from_dict, appr_defect_from_dict, defect_detail_from_dict,
    parse_json_field, FINAL_RESULT_PENDING,
)


class Deserializer:
    def parse_station_details(self, rows: List[dict]) -> List[StationDetail]:
        result = []
        for r in rows:
            all_urls = parse_json_field(r.get("AllImageUrls"))
            sd = StationDetail(**r)
            sd.AllImageUrls = all_urls if isinstance(all_urls, list) else []
            result.append(sd)
        return result

    def parse_inspection_details(self, rows: List[dict]) -> List[InspectionDetailEntity]:
        result = []
        for row in rows:
            ms = self._parse_measurements(row.get("Measurements"))
            defs = self._parse_defects(row.get("Defects"))
            result.append(InspectionDetailEntity(
                Id=row.get("Id", 0),
                StationResultId=row.get("StationResultId", 0),
                StationDetailId=row.get("StationDetailId", 0),
                Sn=row.get("Sn", ""),
                StationNo=row.get("StationNo", ""),
                Result=row.get("Result", FINAL_RESULT_PENDING),
                SingleImagePath=row.get("SingleImagePath", ""),
                ImageWidth=row.get("ImageWidth", 0),
                ImageHeight=row.get("ImageHeight", 0),
                Measurements=ms,
                Defects=defs,
                Time=str(row.get("Time", "") or ""),
            ))
        return result

    def _parse_measurements(self, raw) -> List[Measurement]:
        return [measurement_from_dict(m) for m in parse_json_field(raw)]

    def _parse_defects(self, raw) -> List[ApprDefect]:
        return [appr_defect_from_dict(d) for d in parse_json_field(raw)]
