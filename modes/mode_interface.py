from PyQt5.QtCore import QObject, pyqtSignal


class IRejudgeMode(QObject):
    mode_switched = pyqtSignal(str)

    def mode_name(self) -> str:
        raise NotImplementedError

    def enter_mode(self):
        raise NotImplementedError

    def exit_mode(self):
        raise NotImplementedError

    def on_defect_clicked(self, defect_id: str):
        raise NotImplementedError

    def on_region_clicked(self, region_id: str):
        raise NotImplementedError

    def move_next(self):
        raise NotImplementedError

    def move_prev(self):
        raise NotImplementedError
