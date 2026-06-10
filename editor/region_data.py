import json
import uuid
import os
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QColor


class ShapeType(Enum):
    RECTANGLE = "rectangle"
    CIRCLE = "circle"


@dataclass
class Region:
    id: str = ""
    name: str = ""
    shape_type: ShapeType = ShapeType.RECTANGLE
    x: float = 0
    y: float = 0
    width: float = 100
    height: float = 100
    border_radius: float = 0
    color: str = "#FF6B6B"
    z_order: int = 0
    visible: bool = True
    points: list = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "shape_type": self.shape_type.value,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "border_radius": self.border_radius,
            "color": self.color,
            "z_order": self.z_order,
            "visible": self.visible,
        }
        if self.points:
            d["points"] = [[p.x(), p.y()] for p in self.points]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Region":
        pts = None
        raw = data.get("points")
        if raw:
            from PyQt5.QtCore import QPointF
            pts = [QPointF(float(x), float(y)) for x, y in raw]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            shape_type=ShapeType(data.get("shape_type", "rectangle")),
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            width=float(data.get("width", 100)),
            height=float(data.get("height", 100)),
            border_radius=float(data.get("border_radius", 0)),
            color=data.get("color", "#FF6B6B"),
            z_order=int(data.get("z_order", 0)),
            visible=data.get("visible", True),
            points=pts,
        )


SCHEMA_FILE = "region.json"


class RegionPersistence:

    @staticmethod
    def _default_path() -> str:
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), SCHEMA_FILE)

    @staticmethod
    def load_all_schemas(file_path: str = "") -> list:
        if not file_path:
            file_path = RegionPersistence._default_path()
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
        schemas = data.get("schemas")
        if schemas is not None:
            return schemas
        regions_raw = data.get("regions")
        if regions_raw is not None:
            return [{"product_name": data.get("product_name", ""), "regions": regions_raw}]
        return []

    @staticmethod
    def save_all_schemas(schemas: list, file_path: str = "") -> bool:
        if not file_path:
            file_path = RegionPersistence._default_path()
        try:
            data = {
                "version": "2.0",
                "schemas": schemas,
                "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            }
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False

    @staticmethod
    def get_product_names(file_path: str = "") -> list:
        schemas = RegionPersistence.load_all_schemas(file_path)
        return [s.get("product_name", "") for s in schemas if s.get("product_name", "").strip()]

    @staticmethod
    def load_product(product_name: str, file_path: str = "") -> Tuple[List[Region], Optional[QSize]]:
        schemas = RegionPersistence.load_all_schemas(file_path)
        for s in schemas:
            if s.get("product_name") == product_name:
                regions = [Region.from_dict(rd) for rd in s.get("regions", [])]
                ps = s.get("product_size")
                size = QSize(int(ps["width"]), int(ps["height"])) if ps and ps.get("width") else None
                return regions, size
        return [], None

    @staticmethod
    def save_product(product_name: str, regions: List[Region], product_size: QSize = None, file_path: str = "") -> bool:
        schemas = RegionPersistence.load_all_schemas(file_path)
        entry = {
            "product_name": product_name,
            "regions": [r.to_dict() for r in regions],
        }
        if product_size:
            entry["product_size"] = {"width": product_size.width(), "height": product_size.height()}
        for i, s in enumerate(schemas):
            if s.get("product_name") == product_name:
                schemas[i] = entry
                break
        else:
            schemas.append(entry)
        return RegionPersistence.save_all_schemas(schemas, file_path)

    @staticmethod
    def delete_product(product_name: str, file_path: str = "") -> bool:
        schemas = RegionPersistence.load_all_schemas(file_path)
        schemas = [s for s in schemas if s.get("product_name") != product_name]
        return RegionPersistence.save_all_schemas(schemas, file_path)


class RegionHierarchyManager:
    def __init__(self, regions: List[Region]):
        self.regions = regions

    def get_max_z_order(self) -> int:
        if not self.regions:
            return 0
        return max(r.z_order for r in self.regions)

    def get_min_z_order(self) -> int:
        if not self.regions:
            return 0
        return min(r.z_order for r in self.regions)

    def bring_to_front(self, region: Region):
        max_z = self.get_max_z_order()
        region.z_order = max_z + 1

    def send_to_back(self, region: Region):
        min_z = self.get_min_z_order()
        region.z_order = min_z - 1

    def bring_forward(self, region: Region):
        region.z_order += 1

    def send_backward(self, region: Region):
        region.z_order -= 1
