from datetime import datetime, timedelta
from typing import Optional, List


class TableRouter:
    def __init__(self, hot_days: int = 30):
        self.hot_days = hot_days
        self.query_start: Optional[datetime] = None
        self.query_end: Optional[datetime] = None
        self.history_months: int = 6

    def set_time_range(self, start: Optional[datetime], end: Optional[datetime]):
        self.query_start = start
        self.query_end = end

    def set_history_months(self, months: int):
        self.history_months = months

    def get_station_tables(self) -> List[str]:
        return self._build_table_list("t_station_result")

    def get_detail_tables(self) -> List[str]:
        return self._build_table_list("t_station_detail")

    def get_inspection_tables(self) -> List[str]:
        return self._build_table_list("t_inspection_detail")

    def build_table_list(self, prefix: str) -> List[str]:
        return self._build_table_list(prefix)

    def _build_table_list(self, prefix: str) -> List[str]:
        now = datetime.now()
        hot_begin = now - timedelta(days=self.hot_days)
        tables = []

        if self.query_start and self.query_end:
            end = self.query_end
            start = self.query_start
        else:
            end = now
            start = now

        if end >= hot_begin:
            tables.append(f"{prefix}_current")

        yr, mo = start.year, start.month
        while True:
            month_start = datetime(yr, mo, 1)
            if month_start > end:
                break
            if month_start < hot_begin:
                tables.append(f"{prefix}_history_{yr}{mo:02d}")
            mo += 1
            if mo > 12:
                mo = 1
                yr += 1
        return tables
