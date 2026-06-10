from PyQt5.QtCore import pyqtSignal
from modes.mode_interface import IRejudgeMode


class ImageFirstMode(IRejudgeMode):
    def __init__(self, main_window=None):
        super().__init__()
        self._main_window = main_window

    def mode_name(self) -> str:
        return "image_first"

    def enter_mode(self):
        if not self._main_window:
            return
        mw = self._main_window
        mw._show_status("已切换到: 图片优先模式")
        mw.schematic.clear_selected_region()
        if mw._all_image_paths:
            mw._apply_image_filter()
        elif hasattr(mw, '_refresh_image'):
            mw._refresh_image()

    def exit_mode(self):
        pass

    def on_defect_clicked(self, defect_id: str):
        pass

    def on_region_clicked(self, region_id: str):
        pass

    def move_next(self):
        if self._main_window and hasattr(self._main_window, 'thumb_panel'):
            self._main_window.thumb_panel.go_next()

    def move_prev(self):
        if self._main_window and hasattr(self._main_window, 'thumb_panel'):
            self._main_window.thumb_panel.go_prev()
