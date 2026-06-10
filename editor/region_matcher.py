from typing import List, Dict
from editor.product_layout import Region


class RegionNameMatcher:
    def __init__(self):
        self.name_index: Dict[str, str] = {}

    def build_index(self, regions: List[Region]):
        self.name_index.clear()
        for region in regions:
            keyword = self._extract_keyword(region.name)
            if keyword:
                self.name_index[keyword] = region.id

    def match_region(self, defect_label: str) -> str:
        for keyword, region_id in self.name_index.items():
            if keyword in defect_label:
                return region_id
        return ""

    def _extract_keyword(self, name: str) -> str:
        suffixes = ["区域", "孔位", "阵列", "位置"]
        result = name
        for s in suffixes:
            result = result.replace(s, "")
        return result.strip()
