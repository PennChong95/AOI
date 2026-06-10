import os
from PyQt5.QtCore import pyqtSignal
from modes.mode_interface import IRejudgeMode


class RegionFirstMode(IRejudgeMode):
    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window
        self._current_region_id = ""

    def mode_name(self) -> str:
        return "region_first"

    def enter_mode(self):
        if not self._main_window:
            return
        mw = self._main_window
        mw._show_status("已切换到: 区域优先模式 — 请点击产品示意图上的区域")
        self._current_region_id = ""
        if mw._all_image_paths:
            mw.image_paths = list(mw._all_image_paths)
            mw.image_sources = [set(s) for s in mw._all_image_sources]
            mw.current_image_idx = 0 if mw.image_paths else 0
            mw._rebuild_thumbnails()
            mw._sync_defect_list_to_current_image()
            mw._refresh_image()
        elif hasattr(mw, '_refresh_image'):
            mw._refresh_image()
        mw._update_ng_regions(show_all=True)

    def exit_mode(self):
        self._current_region_id = ""
        if self._main_window:
            self._main_window.schematic.clear_selected_region()

    def on_defect_clicked(self, defect_id: str):
        pass

    def on_region_clicked(self, region_id: str):
        if not self._main_window:
            return
        for r in getattr(self._main_window, '_product_regions', []):
            if r.id == region_id:
                self._filter_by_region(r)
                return

    @staticmethod
    def _insp_has_region(insp, region_name):
        for m in insp.Measurements:
            for dd in m.DefectDatas:
                if (dd.ProductArea or "").strip() == region_name:
                    return True
        for a in insp.Defects:
            for dd in a.Datas:
                if (dd.ProductArea or "").strip() == region_name:
                    return True
        return False

    def _filter_by_region(self, region):
        mw = self._main_window
        self._current_region_id = region.id
        region_name = region.name

        insp_list = mw.inspection_details or []
        matching_indices = set()
        for idx, insp in enumerate(insp_list):
            if self._insp_has_region(insp, region_name):
                matching_indices.add(idx)

        if matching_indices:
            filtered_defects = [d for d in mw.defect_items if d.insp_index in matching_indices]
            mw.image_paths = []
            mw.image_sources = []
            seen = {}
            for i, url in enumerate(mw._all_image_paths):
                overlap = mw._all_image_sources[i] & matching_indices
                if overlap:
                    key = os.path.normpath(url).lower()
                    if key not in seen:
                        seen[key] = len(mw.image_paths)
                        mw.image_paths.append(url)
                        mw.image_sources.append(overlap)
                    else:
                        mw.image_sources[seen[key]] |= overlap
        else:
            filtered_defects = []
            mw.image_paths = []
            mw.image_sources = []

        mw.current_image_idx = 0 if mw.image_paths else 0
        mw._rebuild_thumbnails()
        mw._populate_defect_list(filtered_defects)
        mw._update_ng_regions(show_all=True)
        if matching_indices:
            mw.schematic.set_selected_region(region.id)
        mw._sync_defect_list_to_current_image()
        mw._refresh_image()
        mw._show_status(f"区域 [{region_name}]: {len(filtered_defects)} 个缺陷, {len(mw.image_paths)} 张图片")

    def move_next(self):
        if self._main_window and hasattr(self._main_window, 'defect_list'):
            row = self._main_window.defect_list.currentRow()
            if row < self._main_window.defect_list.count() - 1:
                self._main_window.defect_list.setCurrentRow(row + 1)

    def move_prev(self):
        if self._main_window and hasattr(self._main_window, 'defect_list'):
            row = self._main_window.defect_list.currentRow()
            if row > 0:
                self._main_window.defect_list.setCurrentRow(row - 1)
