"""
Generate local MySQL test data for the AOI review system.

Default behavior:
  - 90 days of production data, ending today.
  - 1000-1500 products per day.
  - 5 stations maximum.
  - 6 defect names maximum.
  - Both OK and NG data.
  - SN format: AOI-YYYYMMDD-0001.
  - Image paths use remote HTTP URLs.

Run:
  python generate_review_test_data.py

Useful options:
  python generate_review_test_data.py --clear-test-data
  python generate_review_test_data.py --host 127.0.0.1 --user root --password 123456 --database aoi
  python generate_review_test_data.py --seed 20260610
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, time, timedelta
from typing import Iterable

import pymysql

try:
    from utils.config_manager import ConfigManager
except Exception:
    ConfigManager = None


HOT_DAYS = 30
DEFAULT_DAYS = 90
DEFAULT_DAILY_MIN = 1000
DEFAULT_DAILY_MAX = 1500
DEFAULT_SN_PREFIX = "AOI"
IMAGE_HOSTS = ["http://192.168.10.21:8080", "http://192.168.10.22:8080", "http://192.168.10.23:8080"]

PRODUCT_TYPE = "3915焊接"
PACK_CODE = "PKG-3915-AOI"
LINE_NAMES = ["L1", "L2", "L3"]
REVIEW_USERS = ["质检员01", "质检员02", "reviewer01"]

STATIONS = [
    ("ST01", "上料外观检查", "AOI"),
    ("ST02", "焊点检查", "AOI"),
    ("ST03", "连接器检查", "AOI"),
    ("ST04", "丝印检查", "AOI"),
    ("ST05", "出料复检", "AOI"),
]

DEFECT_TYPES = [
    ("漏焊", "焊接", "Critical"),
    ("虚焊", "焊接", "Major"),
    ("偏移", "装配", "Major"),
    ("脏污", "外观", "Minor"),
    ("划伤", "外观", "Minor"),
    ("异物", "外观", "Major"),
]

PRODUCT_AREAS = ["A区", "B区", "C区", "D区", "焊接区", "连接器区", "边缘区"]
MEASUREMENT_ITEMS = [
    ("焊盘间距", "0.50", "0.56", "0.44", "mm"),
    ("器件高度", "1.20", "1.35", "1.05", "mm"),
    ("锡膏宽度", "0.32", "0.38", "0.26", "mm"),
    ("偏移量X", "0.00", "0.08", "-0.08", "mm"),
    ("偏移量Y", "0.00", "0.08", "-0.08", "mm"),
    ("焊点面积", "1.80", "2.40", "1.20", "mm2"),
]


DDL = {
    "t_station_result": """
        CREATE TABLE IF NOT EXISTS `{table}` (
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "t_station_detail": """
        CREATE TABLE IF NOT EXISTS `{table}` (
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "t_inspection_detail": """
        CREATE TABLE IF NOT EXISTS `{table}` (
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate AOI review-system test data.")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--database", default=None)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--daily-min", type=int, default=DEFAULT_DAILY_MIN)
    parser.add_argument("--daily-max", type=int, default=DEFAULT_DAILY_MAX)
    parser.add_argument("--sn-prefix", default=DEFAULT_SN_PREFIX)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--clear-test-data", action="store_true", help="Delete rows whose SN matches the chosen prefix before inserting.")
    return parser.parse_args()


def load_db_config(args: argparse.Namespace) -> dict:
    cfg = {
        "host": "127.0.0.1",
        "port": 3306,
        "user": "root",
        "password": "",
        "database": "aoi",
    }
    if ConfigManager:
        app_cfg = ConfigManager.load()
        db_cfg = ConfigManager.get_db_config(app_cfg)
        cfg.update({
            "host": db_cfg.get("host", cfg["host"]),
            "port": int(db_cfg.get("port", cfg["port"])),
            "user": db_cfg.get("user", cfg["user"]),
            "password": db_cfg.get("password", cfg["password"]),
            "database": db_cfg.get("database", cfg["database"]),
        })
    for key in ("host", "port", "user", "password", "database"):
        value = getattr(args, key)
        if value is not None:
            cfg[key] = value
    return cfg


def table_for_day(prefix: str, day: date, now: datetime) -> str:
    hot_begin = now - timedelta(days=HOT_DAYS)
    if datetime.combine(day, time.max) >= hot_begin:
        return f"{prefix}_current"
    return f"{prefix}_history_{day:%Y%m}"


def iter_months(start_day: date, end_day: date) -> Iterable[date]:
    cursor = date(start_day.year, start_day.month, 1)
    while cursor <= end_day:
        yield cursor
        next_month = cursor.month + 1
        next_year = cursor.year
        if next_month == 13:
            next_month = 1
            next_year += 1
        cursor = date(next_year, next_month, 1)


def ensure_tables(cur, start_day: date, end_day: date, now: datetime) -> None:
    table_names = set()
    for prefix in DDL:
        table_names.add(f"{prefix}_current")
        for month in iter_months(start_day, end_day):
            sample_day = min(max(start_day, month), end_day)
            if table_for_day(prefix, sample_day, now).endswith(f"{month:%Y%m}"):
                table_names.add(f"{prefix}_history_{month:%Y%m}")

    for table in sorted(table_names):
        prefix = table.rsplit("_current", 1)[0] if table.endswith("_current") else table.rsplit("_history_", 1)[0]
        cur.execute(DDL[prefix].format(table=table))


def all_target_tables(start_day: date, end_day: date, now: datetime) -> list[str]:
    tables = set()
    for day_offset in range((end_day - start_day).days + 1):
        day = start_day + timedelta(days=day_offset)
        for prefix in DDL:
            tables.add(table_for_day(prefix, day, now))
    return sorted(tables)


def max_id(cur, tables: list[str]) -> int:
    max_value = 0
    for table in tables:
        cur.execute(f"SELECT COALESCE(MAX(Id), 0) FROM `{table}`")
        max_value = max(max_value, int(cur.fetchone()[0]))
    return max_value


def clear_test_data(cur, tables: list[str], sn_prefix: str) -> None:
    for table in tables:
        cur.execute(f"DELETE FROM `{table}` WHERE Sn LIKE %s", (f"{sn_prefix}-%",))


def make_defect_detail(sn: str, station_no: str, defect: tuple[str, str, str]) -> dict:
    name, defect_type, level = defect
    img_w, img_h = 2448, 2048
    width = random.randint(30, 180)
    height = random.randint(30, 180)
    x = random.randint(0, img_w - width - 1)
    y = random.randint(0, img_h - height - 1)
    center_x = x + width // 2
    center_y = y + height // 2
    return {
        "DefectName": name,
        "DefectType": defect_type,
        "Level": level,
        "Count": 1,
        "Datas": [{
            "DefectName": name,
            "DefectType": defect_type,
            "Level": level,
            "ImageWidth": img_w,
            "ImageHeight": img_h,
            "AreaSize": round(width * height * random.uniform(0.45, 0.9), 2),
            "CenterPoint": {"X": center_x, "Y": center_y},
            "BoundingRect": {"X": x, "Y": y, "Width": width, "Height": height},
            "ContourPoints": [
                {"X": x, "Y": y},
                {"X": x + width, "Y": y},
                {"X": x + width, "Y": y + height},
                {"X": x, "Y": y + height},
            ],
            "NineGridArea": str(random.randint(1, 9)),
            "ProductArea": random.choice(PRODUCT_AREAS),
            "AlgorithmVersion": "v4.1-test",
            "DefectImagePath": make_image_url(sn, station_no, "defect", random.randint(1, 9999)),
            "Sn": sn,
            "StationNo": station_no,
        }],
    }


def make_image_url(sn: str, station_no: str, image_type: str, seq: int) -> str:
    host = IMAGE_HOSTS[seq % len(IMAGE_HOSTS)]
    return f"{host}/aoi/images/{sn}/{station_no}/{image_type}_{seq:04d}.jpg"


def make_measurements(station_is_ng: bool, station_no: str) -> list[dict]:
    count = random.randint(2, 4)
    selected = random.sample(MEASUREMENT_ITEMS, count)
    measurements = []
    force_ng_index = random.randrange(count) if station_is_ng and random.random() < 0.35 else -1
    for idx, (name, target, ucl, lcl, units) in enumerate(selected):
        target_value = float(target)
        ucl_value = float(ucl)
        lcl_value = float(lcl)
        tolerance = max(abs(ucl_value - target_value), abs(target_value - lcl_value))
        if idx == force_ng_index:
            value = ucl_value + random.uniform(tolerance * 0.2, tolerance * 0.8)
            status = "NG"
            errors = [{"errorCode": "MEASURE_OUT_OF_SPEC", "actionCode": "REVIEW"}]
        else:
            value = random.uniform(lcl_value, ucl_value)
            status = "OK"
            errors = []
        measurements.append({
            "Reference": f"{station_no}-{name}",
            "Type": "dimension",
            "Status": status,
            "MeasureTarget": target,
            "MeasureValue": f"{value:.3f}",
            "MeasureUcl": ucl,
            "MeausreLcl": lcl,
            "MeasureTolP": f"{ucl_value - target_value:.3f}",
            "MeasureTolN": f"{target_value - lcl_value:.3f}",
            "Units": units,
            "Errors": errors,
            "DefectDatas": [],
        })
    return measurements


def insert_station_result(cur, table: str, row: tuple) -> None:
    cur.execute(
        f"""
        INSERT INTO `{table}`
        (Id, User, Line, WorkOrder, MachineId, Sn, PackCode, ProductType, FixNo, HoleNo,
         FinalResult, ReviewResult, ReviewRemark, ReviewUser, ReviewTime, CreateTime, UpdateTime)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        row,
    )


def insert_station_detail(cur, table: str, row: tuple) -> None:
    cur.execute(
        f"""
        INSERT INTO `{table}`
        (Id, StationResultId, Sn, StationNo, StationName, StationType, StationResult,
         StartTime, EndTime, AllImageUrls)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        row,
    )


def insert_inspection_detail(cur, table: str, row: tuple) -> None:
    cur.execute(
        f"""
        INSERT INTO `{table}`
        (Id, StationResultId, StationDetailId, Sn, StationNo, Result, SingleImagePath,
         ImageWidth, ImageHeight, Measurements, Defects, Time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        row,
    )


def generate_data(args: argparse.Namespace) -> None:
    if args.daily_min > args.daily_max:
        raise ValueError("--daily-min cannot be greater than --daily-max")
    if args.days <= 0:
        raise ValueError("--days must be greater than 0")
    if args.seed is not None:
        random.seed(args.seed)

    now = datetime.now()
    end_day = now.date()
    start_day = end_day - timedelta(days=args.days - 1)
    db_cfg = load_db_config(args)

    conn = pymysql.connect(
        host=db_cfg["host"],
        port=int(db_cfg["port"]),
        user=db_cfg["user"],
        password=db_cfg["password"],
        database=db_cfg["database"],
        charset="utf8mb4",
        autocommit=False,
    )

    totals = {"results": 0, "details": 0, "inspections": 0, "ok": 0, "ng": 0}
    try:
        with conn.cursor() as cur:
            ensure_tables(cur, start_day, end_day, now)
            tables = all_target_tables(start_day, end_day, now)
            if args.clear_test_data:
                clear_test_data(cur, tables, args.sn_prefix)

            result_id = max_id(cur, [t for t in tables if t.startswith("t_station_result")])
            detail_id = max_id(cur, [t for t in tables if t.startswith("t_station_detail")])
            inspection_id = max_id(cur, [t for t in tables if t.startswith("t_inspection_detail")])

            for day_index in range(args.days):
                current_day = start_day + timedelta(days=day_index)
                daily_count = random.randint(args.daily_min, args.daily_max)
                day_base = datetime.combine(current_day, time(hour=8))
                work_order = f"WO-{current_day:%Y%m%d}"

                result_table = table_for_day("t_station_result", current_day, now)
                detail_table = table_for_day("t_station_detail", current_day, now)
                inspection_table = table_for_day("t_inspection_detail", current_day, now)

                for seq in range(1, daily_count + 1):
                    sn = f"{args.sn_prefix}-{current_day:%Y%m%d}-{seq:04d}"
                    create_time = day_base + timedelta(seconds=int(seq * 36000 / daily_count))
                    is_ng = random.random() < 0.14
                    final_result = 2 if is_ng else 1
                    review_result = random.choices(
                        [0, 1, 2],
                        weights=[18, 68, 14] if final_result == 1 else [15, 25, 60],
                        k=1,
                    )[0]
                    review_user = random.choice(REVIEW_USERS) if review_result else ""
                    review_time = create_time + timedelta(minutes=random.randint(5, 240)) if review_result else None
                    review_remark = "" if review_result == 0 else ("复判OK" if review_result == 1 else "复判NG")

                    result_id += 1
                    insert_station_result(cur, result_table, (
                        result_id,
                        f"OP{seq % 8 + 1:02d}",
                        LINE_NAMES[seq % len(LINE_NAMES)],
                        work_order,
                        f"AOI-{seq % 5 + 1:02d}",
                        sn,
                        PACK_CODE,
                        PRODUCT_TYPE,
                        f"FIX{seq % 12 + 1:02d}",
                        f"H{seq % 16 + 1:02d}",
                        final_result,
                        review_result,
                        review_remark,
                        review_user,
                        review_time,
                        create_time,
                        review_time or create_time,
                    ))
                    totals["results"] += 1
                    totals["ng" if is_ng else "ok"] += 1

                    ng_station_indexes = set()
                    if is_ng:
                        ng_station_indexes = set(random.sample(range(len(STATIONS)), random.randint(1, 2)))

                    for station_idx, (station_no, station_name, station_type) in enumerate(STATIONS):
                        station_start = create_time + timedelta(minutes=station_idx * 2, seconds=random.randint(0, 45))
                        station_end = station_start + timedelta(seconds=random.randint(30, 120))
                        station_is_ng = station_idx in ng_station_indexes
                        station_result = 2 if station_is_ng else 1

                        detail_id += 1
                        insert_station_detail(cur, detail_table, (
                            detail_id,
                            result_id,
                            sn,
                            station_no,
                            station_name,
                            station_type,
                            station_result,
                            station_start,
                            station_end,
                            json.dumps([
                                make_image_url(sn, station_no, "full", station_idx * 2 + 1),
                                make_image_url(sn, station_no, "full", station_idx * 2 + 2),
                            ], ensure_ascii=False),
                        ))
                        totals["details"] += 1

                        defects = []
                        if station_is_ng:
                            defect_count = random.randint(1, 3)
                            for defect in random.sample(DEFECT_TYPES, defect_count):
                                defects.append(make_defect_detail(sn, station_no, defect))

                        inspection_id += 1
                        insert_inspection_detail(cur, inspection_table, (
                            inspection_id,
                            result_id,
                            detail_id,
                            sn,
                            station_no,
                            station_result,
                            make_image_url(sn, station_no, "single", inspection_id),
                            2448,
                            2048,
                            json.dumps(make_measurements(station_is_ng, station_no), ensure_ascii=False),
                            json.dumps(defects, ensure_ascii=False),
                            station_start + timedelta(seconds=random.randint(3, 20)),
                        ))
                        totals["inspections"] += 1

                print(f"{current_day:%Y-%m-%d}: {daily_count} pcs -> {result_table}")
                conn.commit()

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\nDone.")
    print(f"Date range: {start_day:%Y-%m-%d} to {end_day:%Y-%m-%d}")
    print(f"SN rule: {args.sn_prefix}-YYYYMMDD-0001")
    print(f"Defect types: {', '.join(name for name, _, _ in DEFECT_TYPES)}")
    print(f"Stations: {len(STATIONS)}")
    print(f"Products: {totals['results']} total, OK={totals['ok']}, NG={totals['ng']}")
    print(f"Station detail rows: {totals['details']}")
    print(f"Inspection detail rows: {totals['inspections']}")


def main() -> None:
    generate_data(parse_args())


if __name__ == "__main__":
    main()
