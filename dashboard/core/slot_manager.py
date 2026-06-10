from dataclasses import dataclass
from typing import Optional, List
from PyQt5.QtCore import QObject, pyqtSignal


@dataclass
class DashboardSlot:
    """槽位数据模型（纯数据，与UI无关）"""
    slot_id: int
    card_id: Optional[str] = None
    is_activated: bool = False
    is_maximized: bool = False


class SlotManager(QObject):
    """槽位管理器，纯逻辑层"""

    slot_added = pyqtSignal(int)
    slot_removed = pyqtSignal(int)
    slot_card_changed = pyqtSignal(int, str)
    slot_activated = pyqtSignal(int)
    layout_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.slots: List[DashboardSlot] = []
        self._slot_counter = 0
        self._activated_slot_id: Optional[int] = None

    def add_slot(self) -> int:
        slot_id = self._slot_counter
        self._slot_counter += 1
        slot = DashboardSlot(slot_id=slot_id)
        self.slots.append(slot)
        self.slot_added.emit(slot_id)
        self.layout_changed.emit()
        return slot_id

    def remove_slot(self, slot_id: int):
        for i, slot in enumerate(self.slots):
            if slot.slot_id == slot_id:
                self.slots.pop(i)
                self.slot_removed.emit(slot_id)
                self.layout_changed.emit()
                if self._activated_slot_id == slot_id and self.slots:
                    self.activate_slot(self.slots[0].slot_id)
                break

    def set_slot_card(self, slot_id: int, card_id: Optional[str]):
        for slot in self.slots:
            if slot.slot_id == slot_id:
                slot.card_id = card_id
                self.slot_card_changed.emit(slot_id, card_id or "")
                break

    def activate_slot(self, slot_id: int):
        for slot in self.slots:
            slot.is_activated = slot.slot_id == slot_id
        for slot in self.slots:
            if slot.slot_id == slot_id:
                self._activated_slot_id = slot_id
                self.slot_activated.emit(slot_id)
                break

    def get_activated_slot(self) -> Optional[DashboardSlot]:
        for slot in self.slots:
            if slot.slot_id == self._activated_slot_id:
                return slot
        return None

    def get_empty_slot(self) -> Optional[DashboardSlot]:
        for slot in self.slots:
            if slot.card_id is None:
                return slot
        return None

    def get_slot_by_card(self, card_id: str) -> Optional[DashboardSlot]:
        for slot in self.slots:
            if slot.card_id == card_id:
                return slot
        return None

    def save_layout(self) -> dict:
        return {
            "version": "2.0",
            "slots": [
                {"slot_id": s.slot_id, "card_id": s.card_id, "is_activated": s.is_activated}
                for s in self.slots
            ],
            "activated_slot_id": self._activated_slot_id,
        }

    def load_layout(self, config: dict):
        self.slots.clear()
        self._slot_counter = 0
        for sc in config.get("slots", []):
            sid = self.add_slot()
            self.set_slot_card(sid, sc.get("card_id"))
        aid = config.get("activated_slot_id")
        if aid is not None:
            self.activate_slot(aid)
