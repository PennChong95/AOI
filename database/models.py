from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PointInt:
    X: int = 0
    Y: int = 0


@dataclass
class RectangleInt:
    X: int = 0
    Y: int = 0
    Width: int = 0
    Height: int = 0


@dataclass
class DefectDetailInfo:
    DefectName: str = ""
    DefectType: str = ""
    Level: str = ""
    ImageWidth: int = 0
    ImageHeight: int = 0
    AreaSize: float = 0.0
    CenterPoint: PointInt = field(default_factory=PointInt)
    BoundingRect: RectangleInt = field(default_factory=RectangleInt)
    ContourPoints: List[PointInt] = field(default_factory=list)
    NineGridArea: str = "0"
    ProductArea: str = ""
    AlgorithmVersion: str = ""
    DefectImagePath: str = ""


@dataclass
class ErrorInfo:
    errorCode: str = ""
    actionCode: str = ""


@dataclass
class Measurement:
    Reference: str = ""
    Type: str = "1"
    Status: str = "Pending"
    MeasureTarget: str = ""
    MeasureValue: str = ""
    MeasureUcl: str = ""
    MeausreLcl: str = ""
    MeasureTolP: str = ""
    MeasureTolN: str = ""
    Units: str = "mm"
    Errors: List[ErrorInfo] = field(default_factory=list)
    DefectDatas: List[DefectDetailInfo] = field(default_factory=list)


@dataclass
class ApprDefect:
    DefectName: str = ""
    DefectType: str = ""
    Level: str = ""
    Count: int = 0
    Datas: List[DefectDetailInfo] = field(default_factory=list)


def point_int_from_dict(d: dict) -> PointInt:
    return PointInt(X=d.get("X", 0), Y=d.get("Y", 0))


def rect_int_from_dict(d: dict) -> RectangleInt:
    return RectangleInt(
        X=d.get("X", 0), Y=d.get("Y", 0),
        Width=d.get("Width", 0), Height=d.get("Height", 0)
    )


def defect_detail_from_dict(d: dict) -> DefectDetailInfo:
    pts = [point_int_from_dict(p) for p in d.get("ContourPoints", []) or []]
    return DefectDetailInfo(
        DefectName=d.get("DefectName", ""),
        DefectType=d.get("DefectType", ""),
        Level=d.get("Level", ""),
        ImageWidth=d.get("ImageWidth", 0),
        ImageHeight=d.get("ImageHeight", 0),
        AreaSize=float(d.get("AreaSize", 0)),
        CenterPoint=point_int_from_dict(d.get("CenterPoint", {}) or {}),
        BoundingRect=rect_int_from_dict(d.get("BoundingRect", {}) or {}),
        ContourPoints=pts,
        NineGridArea=str(d.get("NineGridArea", "0")),
        ProductArea=d.get("ProductArea", ""),
        AlgorithmVersion=d.get("AlgorithmVersion", ""),
        DefectImagePath=d.get("DefectImagePath", ""),
    )


def measurement_from_dict(d: dict) -> Measurement:
    errs = [ErrorInfo(**e) for e in d.get("Errors", []) or []]
    defs = [defect_detail_from_dict(dd) for dd in d.get("DefectDatas", []) or []]
    return Measurement(
        Reference=d.get("Reference", ""),
        Type=d.get("Type", "1"),
        Status=d.get("Status", "Pending"),
        MeasureTarget=d.get("MeasureTarget", ""),
        MeasureValue=d.get("MeasureValue", ""),
        MeasureUcl=d.get("MeasureUcl", ""),
        MeausreLcl=d.get("MeausreLcl", ""),
        MeasureTolP=d.get("MeasureTolP", ""),
        MeasureTolN=d.get("MeasureTolN", ""),
        Units=d.get("Units", "mm"),
        Errors=errs,
        DefectDatas=defs,
    )


def appr_defect_from_dict(d: dict) -> ApprDefect:
    defs = [defect_detail_from_dict(dd) for dd in d.get("Datas", []) or []]
    return ApprDefect(
        DefectName=d.get("DefectName", ""),
        DefectType=d.get("DefectType", ""),
        Level=d.get("Level", ""),
        Count=int(d.get("Count", 0)),
        Datas=defs,
    )


def parse_json_field(val):
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, bytes):
        val = val.decode("utf-8")
    if isinstance(val, str) and val:
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return []
    return []


FINAL_RESULT_PENDING = 0
FINAL_RESULT_OK = 1
FINAL_RESULT_NG = 2

REVIEW_PENDING = 0
REVIEW_OK = 1
REVIEW_NG = 2


@dataclass
class StationResult:
    Id: int = 0
    User: str = ""
    Sn: str = ""
    ProductType: str = ""
    WorkOrder: str = ""
    Line: str = ""
    MachineId: str = ""
    PackCode: str = ""
    FixNo: str = ""
    HoleNo: str = ""
    FinalResult: int = FINAL_RESULT_PENDING
    ReviewResult: int = REVIEW_PENDING
    ReviewRemark: str = ""
    ReviewUser: str = ""
    ReviewTime: str = ""
    CreateTime: str = ""
    UpdateTime: str = ""


@dataclass
class StationDetail:
    Id: int = 0
    StationResultId: int = 0
    Sn: str = ""
    StationNo: str = ""
    StationName: str = ""
    StationType: str = ""
    StationResult: int = FINAL_RESULT_PENDING
    StartTime: str = ""
    EndTime: str = ""
    AllImageUrls: List[str] = field(default_factory=list)


@dataclass
class InspectionDetailEntity:
    Id: int = 0
    StationResultId: int = 0
    StationDetailId: int = 0
    Sn: str = ""
    StationNo: str = ""
    Result: int = FINAL_RESULT_PENDING
    SingleImagePath: str = ""
    ImageWidth: int = 0
    ImageHeight: int = 0
    Measurements: List[Measurement] = field(default_factory=list)
    Defects: List[ApprDefect] = field(default_factory=list)
    Time: str = ""


import json
