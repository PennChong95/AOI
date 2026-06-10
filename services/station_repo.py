from typing import Optional, List, Tuple
from datetime import datetime
from database.manager import DBConnection
from database.models import StationResult, StationDetail, InspectionDetailEntity


class StationRepository:
    def __init__(self, connection: DBConnection):
        self.conn = connection

    def find_by_sn(self, sn: str) -> Optional[StationResult]:
        return self.conn.query_station_result(sn)

    def find_by_id(self, result_id: int) -> Optional[StationResult]:
        return self.conn.query_station_result_by_id(result_id)

    def find_all_by_sn(self, sn: str) -> List[StationResult]:
        return self.conn.query_station_results_all(sn)

    def find_details(self, result_id: int) -> List[StationDetail]:
        return self.conn.query_station_details(result_id)

    def find_inspections(self, result_id: int) -> List[InspectionDetailEntity]:
        return self.conn.query_inspection_details(result_id)

    def find_details_batch(self, result_id: int) -> Tuple[List[StationDetail], List[InspectionDetailEntity]]:
        return self.conn.query_details_batch(result_id)

    def update_review(self, sn: str, review_result: int, review_user: str, review_remark: str = ""):
        self.conn.update_review(sn, review_result, review_user, review_remark)
