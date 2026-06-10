from dataclasses import dataclass, field
from typing import Any, Dict
from PyQt5.QtCore import QObject, pyqtSignal


@dataclass
class DrillDownEvent:
    source: str
    filter_type: str
    value: Any
    extra: Dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        return f"DrillDownEvent({self.source}, {self.filter_type}={self.value})"


class DrillDownBus(QObject):
    signal = pyqtSignal(DrillDownEvent)

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = DrillDownBus()
        return cls._instance

    def emit(self, event: DrillDownEvent):
        self.signal.emit(event)


BUS = DrillDownBus.instance()
