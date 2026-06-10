import pymysql
import json
import time
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from database.models import (
    StationResult, StationDetail, InspectionDetailEntity,
    FINAL_RESULT_PENDING,
)
from database.router import TableRouter
from database.deserializer import Deserializer


class DBConnection:
    def __init__(self, source_name: str, host="127.0.0.1", port=3306, user="root", password="", database="aoi"):
        self.source_name = source_name
        self.config = {
            "host": host, "port": int(port), "user": user,
            "password": password, "database": database,
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
            "autocommit": True,
        }
        self.connection: Optional[pymysql.Connection] = None
        self.history_months: int = 6
        self.query_mode: str = "default"
        self.quick_days: int = 0
        self.query_start_time: Optional[datetime] = None
        self.query_end_time: Optional[datetime] = None
        self.router = TableRouter()
        self.deserializer = Deserializer()

    def connect(self) -> bool:
        try:
            self.connection = pymysql.connect(**self.config)
            self._init_tables()
            return True
        except pymysql.Error as e:
            self.connection = None
            raise ConnectionError(f"[{self.source_name}] 数据库连接失败: {e}")

    def disconnect(self):
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

    def is_connected(self) -> bool:
        if not self.connection:
            return False
        try:
            self.connection.ping(reconnect=False)
            return True
        except Exception:
            return False

    def _init_tables(self):
        sqls = [
            """CREATE TABLE IF NOT EXISTS `t_station_result_current` (
                `Id` INT AUTO_INCREMENT PRIMARY KEY,
                `User` VARCHAR(100) DEFAULT '',
                `Line` VARCHAR(50) DEFAULT '',
                `WorkOrder` VARCHAR(100) DEFAULT '',
                `MachineId` VARCHAR(50) DEFAULT '',
                `Sn` VARCHAR(200) NOT NULL,
                `PackCode` VARCHAR(200) DEFAULT '',
                `ProductType` VARCHAR(100) DEFAULT '',
                `FixNo` VARCHAR(50) DEFAULT '',
                `HoleNo` VARCHAR(50) DEFAULT '',
                `FinalResult` INT DEFAULT 0,
                `ReviewResult` INT DEFAULT 0,
                `ReviewRemark` VARCHAR(500) DEFAULT '',
                `ReviewUser` VARCHAR(50) DEFAULT '',
                `ReviewTime` DATETIME DEFAULT NULL,
                `CreateTime` DATETIME DEFAULT NULL,
                `UpdateTime` DATETIME DEFAULT NULL,
                INDEX `idx_sn` (`Sn`),
                INDEX `idx_sn_ctime` (`Sn`, `CreateTime`),
                INDEX `idx_final_ctime` (`FinalResult`, `CreateTime`),
                INDEX `idx_workorder_ctime` (`WorkOrder`, `CreateTime`),
                INDEX `idx_ctime` (`CreateTime`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            f"""CREATE TABLE IF NOT EXISTS `t_station_detail_current` (
                `Id` INT AUTO_INCREMENT PRIMARY KEY,
                `StationResultId` INT NOT NULL,
                `Sn` VARCHAR(200) DEFAULT '',
                `StationNo` VARCHAR(20) DEFAULT '',
                `StationName` VARCHAR(100) DEFAULT '',
                `StationType` VARCHAR(50) DEFAULT '',
                `StationResult` INT DEFAULT 0,
                `StartTime` DATETIME DEFAULT NULL,
                `EndTime` DATETIME DEFAULT NULL,
                `AllImageUrls` JSON,
                INDEX `idx_sn` (`Sn`),
                INDEX `idx_sn_station` (`Sn`, `StationNo`),
                INDEX `idx_station_rid` (`StationResultId`),
                INDEX `idx_start_time` (`StartTime`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
            f"""CREATE TABLE IF NOT EXISTS `t_inspection_detail_current` (
                `Id` INT AUTO_INCREMENT PRIMARY KEY,
                `StationResultId` INT NOT NULL,
                `StationDetailId` INT NOT NULL,
                `Sn` VARCHAR(200) DEFAULT '',
                `StationNo` VARCHAR(20) DEFAULT '',
                `Result` INT DEFAULT 0,
                `SingleImagePath` VARCHAR(500) DEFAULT '',
                `ImageWidth` INT DEFAULT 0,
                `ImageHeight` INT DEFAULT 0,
                `Measurements` JSON,
                `Defects` JSON,
                `Time` DATETIME DEFAULT NULL,
                INDEX `idx_sn` (`Sn`),
                INDEX `idx_sn_station` (`Sn`, `StationNo`),
                INDEX `idx_rid_did` (`StationResultId`, `StationDetailId`),
                INDEX `idx_result_time` (`Result`, `Time`),
                INDEX `idx_time` (`Time`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        ]
        for sql in sqls:
            self._execute(sql)

    def _ensure_connected(self):
        try:
            if self.connection:
                self.connection.ping(reconnect=True)
                return True
        except pymysql.Error:
            pass
        try:
            self.connect()
            return True
        except Exception:
            return False

    def _execute(self, sql: str, params: tuple = ()) -> int:
        if not self.connection:
            raise ConnectionError("数据库未连接")
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            self.connection.commit()
            return cursor.rowcount

    def _fetch_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        if not self.connection:
            raise ConnectionError("数据库未连接")
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def _fetch_all(self, sql: str, params: tuple = ()) -> List[dict]:
        if not self.connection:
            raise ConnectionError("数据库未连接")
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def _sync_router(self):
        if self.query_mode == "custom":
            self.router.set_time_range(self.query_start_time, self.query_end_time)
        else:
            self.router.set_time_range(None, None)
        self.router.set_history_months(self.history_months)

    def _search_one(self, table_prefix: str, sql_where: str, params: tuple, time_column: str = None) -> Optional[dict]:
        self._sync_router()
        where, pars = self._apply_time_range(sql_where, params, time_column)
        for table in self.router.build_table_list(table_prefix):
            row = self._try_fetch_one(table, where, pars)
            if row:
                return row
        return None

    def _search_all(self, table_prefix: str, sql_where: str, params: tuple, time_column: str = None) -> List[dict]:
        self._sync_router()
        where, pars = self._apply_time_range(sql_where, params, time_column)
        results = []
        for table in self.router.build_table_list(table_prefix):
            rows = self._try_fetch_all(table, where, pars)
            results.extend(rows)
        return results

    def _apply_time_range(self, sql_where: str, params: tuple, time_column: str = None):
        if self.query_mode == "default" or not time_column:
            return sql_where, params
        if self.query_mode == "quick":
            now = datetime.now()
            start = self._calc_quick_start(self.quick_days, now)
            where = sql_where + f" AND {time_column} BETWEEN %s AND %s"
            pars = params + (start, now)
            return where, pars
        if self.query_mode == "custom" and self.query_start_time and self.query_end_time:
            where = sql_where + f" AND {time_column} BETWEEN %s AND %s"
            pars = params + (self.query_start_time, self.query_end_time)
            return where, pars
        return sql_where, params

    def _calc_quick_start(self, days: int, now: datetime) -> datetime:
        if days == 0:
            return datetime(now.year, now.month, now.day, 0, 0, 0)
        elif days == -1:
            return datetime(now.year, now.month, 1, 0, 0, 0)
        else:
            d = now - timedelta(days=days)
            return datetime(d.year, d.month, d.day, 0, 0, 0)

    def _try_fetch_one(self, table_name: str, sql_where: str, params: tuple) -> Optional[dict]:
        try:
            return self._fetch_one(f"SELECT * FROM `{table_name}` {sql_where}", params)
        except pymysql.Error:
            if self._ensure_connected():
                try:
                    return self._fetch_one(f"SELECT * FROM `{table_name}` {sql_where}", params)
                except pymysql.Error:
                    return None
            return None

    def _try_fetch_all(self, table_name: str, sql_where: str, params: tuple) -> List[dict]:
        try:
            return self._fetch_all(f"SELECT * FROM `{table_name}` {sql_where}", params)
        except pymysql.Error:
            if self._ensure_connected():
                try:
                    return self._fetch_all(f"SELECT * FROM `{table_name}` {sql_where}", params)
                except pymysql.Error:
                    return []
            return []

    def _try_execute(self, table_name: str, sql_where: str, params: tuple) -> int:
        try:
            return self._execute(f"UPDATE `{table_name}` {sql_where}", params)
        except pymysql.Error:
            if self._ensure_connected():
                try:
                    return self._execute(f"UPDATE `{table_name}` {sql_where}", params)
                except pymysql.Error:
                    return 0
            return 0

    def query_station_result(self, sn: str) -> Optional['StationResult']:
        _t0 = time.perf_counter()
        row = self._search_one("t_station_result", "WHERE Sn = %s ORDER BY Id DESC LIMIT 1", (sn,), time_column="CreateTime")
        _t1 = time.perf_counter()
        if row:
            print(f"[PERF] query_station_result 命中: {(_t1-_t0)*1000:.1f}ms")
            return StationResult(**row)
        print(f"[PERF] query_station_result 未找到: {(_t1-_t0)*1000:.1f}ms")
        return None

    def query_station_result_by_id(self, result_id: int) -> Optional['StationResult']:
        row = self._search_one("t_station_result", "WHERE Id = %s", (result_id,))
        return StationResult(**row) if row else None

    def query_station_results_all(self, sn: str) -> List['StationResult']:
        rows = self._search_all("t_station_result", "WHERE Sn = %s ORDER BY Id DESC", (sn,), time_column="CreateTime")
        results = [StationResult(**r) for r in rows]
        results.sort(key=lambda r: r.Id, reverse=True)
        return results

    def query_station_details(self, result_id: int) -> List['StationDetail']:
        _t0 = time.perf_counter()
        rows = self._search_all("t_station_detail", "WHERE StationResultId = %s", (result_id,), time_column="StartTime")
        result = self._parse_station_details(rows)
        _t1 = time.perf_counter()
        print(f"[PERF] query_station_details: SQL+解析={(_t1-_t0)*1000:.1f}ms rows={len(rows)}")
        return result

    def query_inspection_details(self, result_id: int) -> List['InspectionDetailEntity']:
        _t0 = time.perf_counter()
        rows = self._search_all("t_inspection_detail", "WHERE StationResultId = %s", (result_id,), time_column="Time")
        result = self._parse_inspection_details(rows)
        _t1 = time.perf_counter()
        print(f"[PERF] query_inspection_details: SQL+解析={(_t1-_t0)*1000:.1f}ms rows={len(rows)}")
        return result

    def query_details_batch(self, result_id: int) -> Tuple[List['StationDetail'], List['InspectionDetailEntity']]:
        """Query both station_details and inspection_details."""
        _t0 = time.perf_counter()
        sd = self.query_station_details(result_id)
        insp = self.query_inspection_details(result_id)
        _t1 = time.perf_counter()
        print(f"[PERF] query_details_batch total: {(_t1-_t0)*1000:.1f}ms")
        return sd, insp

    def _parse_station_details(self, rows: List[dict]) -> List['StationDetail']:
        return self.deserializer.parse_station_details(rows)

    def _parse_inspection_details(self, rows: List[dict]) -> List['InspectionDetailEntity']:
        return self.deserializer.parse_inspection_details(rows)

    def update_review(self, sn: str, review_result: int, review_user: str, review_remark: str = ""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        set_clause = "SET ReviewResult = %s, ReviewUser = %s, ReviewTime = %s, ReviewRemark = %s, UpdateTime = %s WHERE Sn = %s ORDER BY Id DESC LIMIT 1"
        params = (review_result, review_user, now, review_remark, now, sn)
        self._sync_router()
        for table in self.router.build_table_list("t_station_result"):
            affected = self._try_execute(table, set_clause, params)
            if affected:
                return


class DBManager:
    def __init__(self, db_configs: list = None):
        self.connections: List[DBConnection] = []
        self._active_sources: List[str] = []
        if db_configs:
            for cfg in db_configs:
                if cfg.get("enabled", True):
                    conn = DBConnection(
                        source_name=cfg.get("name", "未命名"),
                        host=cfg.get("host", "127.0.0.1"),
                        port=int(cfg.get("port", 3306)),
                        user=cfg.get("user", "root"),
                        password=cfg.get("password", ""),
                        database=cfg.get("database", "aoi"),
                    )
                    self.connections.append(conn)
                    self._active_sources.append(cfg.get("name", "未命名"))

    def connect_all(self) -> Tuple[bool, List[str]]:
        errors = []
        for conn in self.connections:
            try:
                conn.connect()
            except Exception as e:
                errors.append(str(e))
        ok = len(errors) < len(self.connections)
        return ok, errors

    def disconnect_all(self):
        for conn in self.connections:
            conn.disconnect()

    @property
    def active_sources(self) -> List[str]:
        return self._active_sources

    def get_connection(self, source_name: str) -> Optional[DBConnection]:
        for conn in self.connections:
            if conn.source_name == source_name:
                return conn
        return None

    def set_history_query_months(self, months: int):
        for conn in self.connections:
            conn.history_months = months

    def set_query_time_range(self, mode: str, start_str: str = "", end_str: str = "", quick_days: int = 0):
        for conn in self.connections:
            conn.query_mode = mode
            conn.quick_days = quick_days
            try:
                conn.query_start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S") if start_str else None
                conn.query_end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S") if end_str else None
            except Exception:
                conn.query_start_time = None
                conn.query_end_time = None

    def get_first_connected(self) -> Optional[DBConnection]:
        for conn in self.connections:
            if conn.is_connected():
                return conn
        return None

    def query_station_result(self, sn: str) -> List[Tuple[Optional['StationResult'], str]]:
        results = []
        for conn in self.connections:
            if not conn.is_connected():
                continue
            try:
                sr = conn.query_station_result(sn)
                if sr:
                    results.append((sr, conn.source_name))
            except Exception:
                pass
        return results

    def query_station_results_all(self, sn: str) -> List[Tuple['StationResult', str]]:
        results = []
        for conn in self.connections:
            if not conn.is_connected():
                continue
            try:
                rows = conn.query_station_results_all(sn)
                for r in rows:
                    results.append((r, conn.source_name))
            except Exception:
                pass
        return results

    def query_station_details(self, result_id: int, source_name: str = "") -> List['StationDetail']:
        conn = self.get_connection(source_name) if source_name else self.get_first_connected()
        if conn and conn.is_connected():
            return conn.query_station_details(result_id)
        return []

    def query_inspection_details(self, result_id: int, source_name: str = "") -> List['InspectionDetailEntity']:
        conn = self.get_connection(source_name) if source_name else self.get_first_connected()
        if conn and conn.is_connected():
            return conn.query_inspection_details(result_id)
        return []

    def query_details_batch(self, result_id: int, source_name: str = "") -> Tuple[List['StationDetail'], List['InspectionDetailEntity']]:
        conn = self.get_connection(source_name) if source_name else self.get_first_connected()
        if conn and conn.is_connected():
            return conn.query_details_batch(result_id)
        return [], []

    def update_review(self, sn: str, review_result: int, review_user: str, review_remark: str = "", source_name: str = ""):
        conn = self.get_connection(source_name) if source_name else self.get_first_connected()
        if conn and conn.is_connected():
            conn.update_review(sn, review_result, review_user, review_remark)

    def get_repository(self, source_name: str = ""):
        from services.station_repo import StationRepository
        conn = self.get_connection(source_name) if source_name else self.get_first_connected()
        if conn:
            return StationRepository(conn)
        return None
