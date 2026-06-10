import os
from typing import Optional
from utils.config_manager import ConfigManager


class AppSettings:
    def __init__(self):
        self._raw = ConfigManager.load()

    @property
    def defect_box_scale(self) -> float:
        return float(self._raw.get("defect_box_scale", 1.2))

    @property
    def defect_box_color(self) -> str:
        return self._raw.get("defect_box_color", "#00FF00")

    @property
    def defect_line_width(self) -> int:
        return int(self._raw.get("defect_line_width", 2))

    @property
    def nine_grid_line_color(self) -> str:
        return self._raw.get("nine_grid_line_color", "#64C8FF")

    @property
    def nine_grid_highlight_color(self) -> str:
        return self._raw.get("nine_grid_highlight_color", "#64C8FF")

    @property
    def nine_grid_line_width(self) -> int:
        return int(self._raw.get("nine_grid_line_width", 1))

    @property
    def nine_grid_highlight_width(self) -> int:
        return int(self._raw.get("nine_grid_highlight_width", 2))

    @property
    def show_defect_box(self) -> bool:
        return bool(self._raw.get("show_defect_box", True))

    @property
    def show_ok_images(self) -> bool:
        return bool(self._raw.get("show_ok_images", False))

    @property
    def history_query_months(self) -> int:
        return int(self._raw.get("history_query_months", 6))

    @property
    def session_timeout_minutes(self) -> int:
        return int(self._raw.get("session_timeout_minutes", 30))

    @property
    def session_reauthenticate_seconds(self) -> int:
        return int(self._raw.get("session_reauthenticate_seconds", 60))

    @property
    def query_start_time(self) -> str:
        return self._raw.get("query_start_time", "")

    @property
    def query_end_time(self) -> str:
        return self._raw.get("query_end_time", "")

    @property
    def review_constraint_measurement_enabled(self) -> bool:
        return bool(self._raw.get("review_constraint_measurement_enabled", True))

    @property
    def review_constraint_appearance_names(self) -> list:
        return list(self._raw.get("review_constraint_appearance_names", []))

    @property
    def last_product_name(self) -> str:
        return self._raw.get("last_product_name", "")

    @last_product_name.setter
    def last_product_name(self, value: str):
        self._raw["last_product_name"] = value

    def save(self):
        ConfigManager.save(self._raw)

    def raw(self) -> dict:
        return self._raw
