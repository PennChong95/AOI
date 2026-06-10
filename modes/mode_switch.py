from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal
from modes.mode_interface import IRejudgeMode
from modes.image_first_mode import ImageFirstMode
from modes.region_first_mode import RegionFirstMode
from modes.settings import InteractionMode


class ModeSwitchManager(QObject):
    mode_switched = pyqtSignal(InteractionMode)

    def __init__(self, main_window=None):
        super().__init__()
        self.current_mode: Optional[IRejudgeMode] = None
        self._main_window = main_window

    def switch_mode(self, mode: InteractionMode):
        if self.current_mode:
            self.current_mode.exit_mode()

        if mode == InteractionMode.IMAGE_FIRST:
            self.current_mode = ImageFirstMode(self._main_window)
        elif mode == InteractionMode.REGION_FIRST:
            self.current_mode = RegionFirstMode(self._main_window)

        if self.current_mode:
            self.current_mode.enter_mode()

        self.mode_switched.emit(mode)

    @property
    def current(self) -> Optional[IRejudgeMode]:
        return self.current_mode
