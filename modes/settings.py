from enum import Enum
from dataclasses import dataclass
import json


class InteractionMode(Enum):
    IMAGE_FIRST = "image_first"
    REGION_FIRST = "region_first"


@dataclass
class RejudgeSettings:
    mode: InteractionMode = InteractionMode.IMAGE_FIRST
    remember_last_mode: bool = True
    show_region_highlight: bool = True
    auto_next_after_judge: bool = True

    def save(self, file_path: str):
        data = {
            "mode": self.mode.value,
            "remember_last_mode": self.remember_last_mode,
            "show_region_highlight": self.show_region_highlight,
            "auto_next_after_judge": self.auto_next_after_judge,
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load(cls, file_path: str) -> "RejudgeSettings":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(
                mode=InteractionMode(data.get("mode", "image_first")),
                remember_last_mode=data.get("remember_last_mode", True),
                show_region_highlight=data.get("show_region_highlight", True),
                auto_next_after_judge=data.get("auto_next_after_judge", True),
            )
        except Exception:
            return cls()
