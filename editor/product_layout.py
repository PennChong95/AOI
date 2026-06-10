import json
import uuid
import os
import shutil
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from PyQt5.QtCore import QSize, QRectF
from PyQt5.QtGui import QColor


class ShapeType(Enum):
    RECTANGLE = "rect"
    CIRCLE = "circle"
    POLYGON = "polygon"
    CURVE = "curve"


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
    color: str = "#00A0FF"
    z_order: int = 0
    visible: bool = True
    points: List[tuple] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "type": self.shape_type.value,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "border_radius": round(self.border_radius, 2),
            "color": self.color,
            "z_order": self.z_order,
            "visible": self.visible,
        }
        if self.points:
            d["points"] = [[round(p[0], 2), round(p[1], 2)] for p in self.points]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Region":
        raw_type = data.get("type") or data.get("shape_type", "rect")
        pts_raw = data.get("points")
        pts = None
        if pts_raw:
            pts = [(float(x), float(y)) for x, y in pts_raw]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            shape_type=ShapeType(raw_type),
            x=float(data.get("x", 0)),
            y=float(data.get("y", 0)),
            width=float(data.get("width", 100)),
            height=float(data.get("height", 100)),
            border_radius=float(data.get("border_radius", 0)),
            color=data.get("color", "#00A0FF"),
            z_order=int(data.get("z_order", 0)),
            visible=data.get("visible", True),
            points=pts,
        )


@dataclass
class ProductLayoutModel:
    product_name: str = ""
    layout_version: str = "1.0"
    canvas_width: int = 1920
    canvas_height: int = 1080
    background_image: str = ""
    regions: List[Region] = field(default_factory=list)
    ui_config: dict = field(default_factory=lambda: {
        "grid_enabled": True,
        "grid_size": 50,
        "snap_enabled": False,
    })
    navigation_config: dict = field(default_factory=lambda: {
        "click_to_defect": True,
        "auto_zoom_roi": False,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_name": self.product_name,
            "layout_version": self.layout_version,
            "canvas": {
                "width": self.canvas_width,
                "height": self.canvas_height,
            },
            "background_image": self.background_image,
            "regions": [r.to_dict() for r in self.regions],
            "ui_config": self.ui_config,
            "navigation_config": self.navigation_config,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductLayoutModel":
        canvas = data.get("canvas", {})
        regions_raw = data.get("regions", [])
        return cls(
            product_name=data.get("product_name", ""),
            layout_version=data.get("layout_version", "1.0"),
            canvas_width=int(canvas.get("width", 1920)),
            canvas_height=int(canvas.get("height", 1080)),
            background_image=data.get("background_image", ""),
            regions=[Region.from_dict(r) for r in regions_raw],
            ui_config=data.get("ui_config", {}),
            navigation_config=data.get("navigation_config", {}),
        )

    def get_canvas_rect(self) -> QRectF:
        return QRectF(0, 0, self.canvas_width, self.canvas_height)


LAYOUT_DIR = "layouts"
LAYOUT_FILENAME = "layout.region.json"


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _layouts_dir() -> str:
    return os.path.join(_project_root(), LAYOUT_DIR)


def product_dir(product_name: str) -> str:
    safe = product_name.strip().replace(" ", "_").replace("/", "_")
    return os.path.join(_layouts_dir(), safe)


def product_layout_path(product_name: str) -> str:
    return os.path.join(product_dir(product_name), LAYOUT_FILENAME)


class LayoutPersistence:

    @staticmethod
    def list_products() -> List[str]:
        layouts_dir = _layouts_dir()
        if not os.path.isdir(layouts_dir):
            return []
        names = []
        for entry in os.listdir(layouts_dir):
            sub = os.path.join(layouts_dir, entry)
            layout_file = os.path.join(sub, LAYOUT_FILENAME)
            if os.path.isdir(sub) and os.path.isfile(layout_file):
                try:
                    with open(layout_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    pn = data.get("product_name", "").strip()
                    if pn:
                        names.append(pn)
                except Exception:
                    if entry and entry.strip():
                        names.append(entry.strip())
        return names

    @staticmethod
    def load_layout(product_name: str) -> Optional[ProductLayoutModel]:
        path = product_layout_path(product_name)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ProductLayoutModel.from_dict(data)
        except Exception:
            return None

    @staticmethod
    def save_layout(layout: ProductLayoutModel) -> bool:
        if not layout.product_name:
            return False
        pdir = product_dir(layout.product_name)
        try:
            os.makedirs(pdir, exist_ok=True)
            path = product_layout_path(layout.product_name)
            data = layout.to_dict()
            data["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存布局失败: {e}")
            return False

    @staticmethod
    def delete_layout(product_name: str) -> bool:
        pdir = product_dir(product_name)
        if os.path.isdir(pdir):
            try:
                shutil.rmtree(pdir)
                return True
            except Exception:
                return False
        return False


class LegacyRegionPersistence:
    SCHEMA_FILE = "region.json"

    @staticmethod
    def _default_path() -> str:
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), LegacyRegionPersistence.SCHEMA_FILE)

    @staticmethod
    def load_all_schemas(file_path: str = "") -> list:
        if not file_path:
            file_path = LegacyRegionPersistence._default_path()
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
    def get_product_names(file_path: str = "") -> list:
        schemas = LegacyRegionPersistence.load_all_schemas(file_path)
        return [s.get("product_name", "") for s in schemas if s.get("product_name", "").strip()]

    @staticmethod
    def migrate_to_layouts(file_path: str = ""):
        schemas = LegacyRegionPersistence.load_all_schemas(file_path)
        for s in schemas:
            pn = s.get("product_name", "").strip()
            if not pn:
                continue
            regions = [Region.from_dict(rd) for rd in s.get("regions", [])]
            ps = s.get("product_size", {})
            cw = int(ps.get("width", 1000)) if ps else 1000
            ch = int(ps.get("height", 800)) if ps else 800
            layout = ProductLayoutModel(
                product_name=pn,
                canvas_width=cw,
                canvas_height=ch,
                regions=regions,
            )
            LayoutPersistence.save_layout(layout)
            print(f"已迁移: {pn}")


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
        self._set_z(region, self.get_max_z_order() + 1)

    def send_to_back(self, region: Region):
        self._set_z(region, self.get_min_z_order() - 1)

    def bring_forward(self, region: Region):
        self._set_z(region, region.z_order + 1)

    def send_backward(self, region: Region):
        self._set_z(region, region.z_order - 1)

    def _set_z(self, region: Region, z: int):
        region.z_order = z
        self.regions.sort(key=lambda r: r.z_order)
