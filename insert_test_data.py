"""
Insert test data for dashboard quality analytics.
Run: python insert_test_data.py

This generates data in all three partitioned tables (t_station_result_current,
t_station_detail_current, t_inspection_detail_current) with realistic-looking
defect patterns spread across multiple days, stations, product areas, and defects.
"""

import json
import random
from datetime import datetime, timedelta

import pymysql

CONN = {
    "host": "127.0.0.1",
    "port": 3306,
    "database": "aoi",
    "user": "root",
    "password": "123456",
    "charset": "utf8mb4",
    "autocommit": True,
}

# ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
# Configurable parameters
# ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――

DAYS_BACK = 30                      # how many days to go back
SN_TEMPLATES = [
    ("SN12345678901", "iPhone15", "WO-20260601"),
    ("SN12345678902", "iPhone15", "WO-20260601"),
    ("SN12345678903", "iPhone15", "WO-20260602"),
    ("SN12345678904", "iPhone14", "WO-20260601"),
    ("SN12345678905", "iPhone14", "WO-20260602"),
    ("SN12345678906", "iPhone16", "WO-20260601"),
    ("SN12345678907", "iPhone16", "WO-20260601"),
    ("SN12345678908", "iPhone15", "WO-20260602"),
    ("SN12345678909", "iPhone14", "WO-20260602"),
    ("SN12345678910", "iPhone16", "WO-20260602"),
    ("SN12345678911", "iPhone15", "WO-20260601"),
    ("SN12345678912", "iPhone15", "WO-20260602"),
    ("SN12345678913", "iPhone14", "WO-20260601"),
    ("SN12345678914", "iPhone15", "WO-20260601"),
    ("SN12345678915", "iPhone15", "WO-20260602"),
    ("SN12345678916", "iPhone16", "WO-20260601"),
    ("SN12345678917", "iPhone16", "WO-20260602"),
    ("SN12345678918", "iPhone14", "WO-20260601"),
    ("SN12345678919", "iPhone15", "WO-20260601"),
    ("SN12345678920", "iPhone15", "WO-20260602"),
]
# OK/NG ratio: 85% OK, 15% NG → realistic factory yield
OK_WEIGHT = 85
NG_WEIGHT = 15

# Each SN appears on average this many times in the full period
DAYS_PER_SN = 1.5  # each SN appears ~ every 2-3 days

DEFECT_TYPES = ["漏焊", "PET脱落", "PET翘起", "压伤", "脏污", "气泡", "划伤", "异物", "偏移", "缺胶"]

STATIONS = [
    ("ST01", "AOI-1号线", "AOI"),
    ("ST02", "AOI-2号线", "AOI"),
    ("ST03", "SPI-1号线", "SPI"),
    ("ST04", "SPI-2号线", "SPI"),
    ("ST05", "AXI-1号线", "AXI"),
]

PRODUCT_AREAS = ["主体区域", "焊接区域", "连接器区域", "边缘区域", "IC区域", "金手指区域", "BGA区域"]


def _make_defect_json(defect_name, product_area, img_w=2448, img_h=2048):
    """Build the Defects JSON array for an inspection detail row."""
    x = random.randint(10, img_w - 100)
    y = random.randint(10, img_h - 100)
    defect = {
        "DefectName": defect_name,
        "DefectType": "",
        "Level": "",
        "Count": 1,
        "Datas": [{
            "DefectName": defect_name,
            "DefectType": "",
            "Level": "",
            "ImageWidth": img_w,
            "ImageHeight": img_h,
            "AreaSize": round(random.uniform(100, 5000), 2),
            "CenterPoint": {"X": x, "Y": y},
            "BoundingRect": {"X": x - 20, "Y": y - 20, "Width": 40, "Height": 40},
            "ContourPoints": [],
            "NineGridArea": str(random.randint(1, 9)),
            "ProductArea": product_area,
            "AlgorithmVersion": "V4.2.0",
            "DefectImagePath": f"/images/{defect_name}_{random.randint(1000, 9999)}.jpg",
        }],
    }
    return defect


def _make_measurements_json():
    """Build an empty Measurements JSON array (rarely used by dashboards)."""
    return []


def _determine_final_result(defect_count):
    """1=OK, 2=NG, 0=Pending — NG if defect_count > 0."""
    return 1 if defect_count == 0 else 2


def _pick_weighted(items, weights=None):
    """Pick a random item, optionally weighted."""
    if weights is None:
        return random.choice(items)
    return random.choices(items, weights=weights, k=1)[0]


def main():
    print(f"Connecting to {CONN['host']}:{CONN['port']}/{CONN['database']} ...")
    db = pymysql.connect(**CONN)
    cur = db.cursor()
    now = datetime.now()

    # Ensure partitioned tables exist (they should be auto-created)
    # We just write to _current since our data is within the last 30 days.

    print(f"Inserting test data over {DAYS_BACK} days ...")

    cur.execute("SELECT COALESCE(MAX(Id),0) FROM t_station_result_current")
    result_id = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(MAX(Id),0) FROM t_station_detail_current")
    detail_id = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(MAX(Id),0) FROM t_inspection_detail_current")
    inspec_id = cur.fetchone()[0]
    print(f"  Existing max IDs: result={result_id}, detail={detail_id}, inspection={inspec_id}")

    total_results = 0
    total_details = 0
    total_inspections = 0

    for day_offset in reversed(range(DAYS_BACK)):
        day = now - timedelta(days=day_offset)
        day_start = day.replace(hour=8, minute=0, second=0, microsecond=0)

        # On each day, process ~70% of SNs (some pass every day, some skip)
        daily_sn_count = int(len(SN_TEMPLATES) * 0.7)
        daily_sns = random.sample(SN_TEMPLATES, daily_sn_count)

        for sn_idx, (sn, product, wo) in enumerate(daily_sns):
            weight_total = OK_WEIGHT + NG_WEIGHT
            is_ok = random.choices([True, False], weights=[OK_WEIGHT, NG_WEIGHT], k=1)[0]

            if is_ok:
                n_defects = 0
                n_stations = 1
            else:
                n_defects = random.randint(1, 4)
                n_stations = random.randint(1, 2)

            create_time = day_start + timedelta(
                hours=sn_idx % 10, minutes=sn_idx * 13 % 60, seconds=sn_idx * 7 % 60
            )
            final_result = _determine_final_result(n_defects)
            review_result = 0 if day_offset > 2 else (1 if final_result == 1 else 2)
            review_user = "operator1" if review_result > 0 else ""

            result_id += 1
            rev_time = create_time if review_result > 0 else create_time
            row = (
                result_id, "", "L" + str(sn_idx % 3 + 1), wo, f"MCH{sn_idx % 5 + 1}",
                sn, f"PK{sn_idx % 20 + 1:04d}", product, f"FIX{sn_idx % 4 + 1:02d}",
                f"H{sn_idx % 8 + 1:02d}", final_result, review_result,
                "", review_user,
                rev_time,
                create_time, create_time,
            )
            sql_result = (
                "INSERT INTO t_station_result_current "
                "(Id,User,Line,WorkOrder,MachineId,Sn,PackCode,ProductType,FixNo,HoleNo,"
                "FinalResult,ReviewResult,ReviewRemark,ReviewUser,ReviewTime,CreateTime,UpdateTime) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )
            cur.execute(sql_result, row)
            total_results += 1

            used_stations = random.sample(STATIONS, n_stations) if n_stations > 0 else []

            for st_no, st_name, st_type in used_stations:
                detail_id += 1
                station_result = 2 if n_defects > 0 else 1
                start_time = create_time + timedelta(minutes=random.randint(1, 30))
                end_time = start_time + timedelta(minutes=random.randint(1, 5))
                all_image_urls = json.dumps([
                    f"http://camera/{sn}/{st_no}/img_{i}.jpg" for i in range(random.randint(2, 6))
                ])
                sql_detail = (
                    "INSERT INTO t_station_detail_current "
                    "(Id,StationResultId,Sn,StationNo,StationName,StationType,"
                    "StationResult,StartTime,EndTime,AllImageUrls) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                )
                cur.execute(sql_detail, (
                    detail_id, result_id, sn, st_no, st_name, st_type,
                    station_result, start_time, end_time, all_image_urls,
                ))
                total_details += 1

                if n_defects == 0:
                    defect_list = []
                else:
                    if n_stations == 1:
                        chosen_defects = random.sample(DEFECT_TYPES, min(n_defects, len(DEFECT_TYPES)))
                    else:
                        half = n_defects // n_stations
                        st_idx = list(used_stations).index((st_no, st_name, st_type))
                        start_idx = st_idx * half
                        end_idx = start_idx + half if st_idx < n_stations - 1 else n_defects
                        chosen_defects = random.sample(DEFECT_TYPES, min(end_idx - start_idx, len(DEFECT_TYPES)))

                    defect_list = []
                    for df in chosen_defects:
                        area = random.choice(PRODUCT_AREAS)
                        defect_list.append(_make_defect_json(df, area))

                defects_json = json.dumps(defect_list, ensure_ascii=False)
                measurements_json = json.dumps(_make_measurements_json())

                inspec_id += 1
                result_val = 2 if len(defect_list) > 0 else 1
                ins_time = start_time + timedelta(seconds=random.randint(5, 120))
                sql_inspec = (
                    "INSERT INTO t_inspection_detail_current "
                    "(Id,StationResultId,StationDetailId,Sn,StationNo,Result,"
                    "SingleImagePath,ImageWidth,ImageHeight,Measurements,Defects,Time) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                )
                cur.execute(sql_inspec, (
                    inspec_id, result_id, detail_id, sn, st_no, result_val,
                    f"/images/{sn}/{st_no}/{inspec_id}.jpg",
                    2448, 2048, measurements_json, defects_json, ins_time,
                ))
                total_inspections += 1

        if day_offset % 5 == 0:
            print(f"  ... processed day -{day_offset}")

    # Also insert a few more NG data specifically for SN 12345678907
    # (ensure it appears on heatmap and defect charts)
    print("  ... adding extra defect data for SN12345678907 ...")
    extra_sn = "SN12345678907"
    extra_product = "iPhone16"
    extra_wo = "WO-20260601"
    recent = now - timedelta(hours=random.randint(1, 12))
    result_id += 1
    cur.execute(
        "INSERT INTO t_station_result_current "
        "(Id,User,Line,WorkOrder,MachineId,Sn,PackCode,ProductType,FixNo,HoleNo,"
        "FinalResult,ReviewResult,ReviewRemark,ReviewUser,ReviewTime,CreateTime,UpdateTime) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (result_id, "", "L1", extra_wo, "MCH2", extra_sn,
         "PK0025", extra_product, "FIX01", "H01",
         2, 2, "", "reviewer1", recent, recent, recent)
    )
    for st_idx, (st_no, st_name, st_type) in enumerate(STATIONS[:3]):
        detail_id += 1
        start_time = recent + timedelta(minutes=st_idx * 5)
        end_time = start_time + timedelta(minutes=2)
        cur.execute(
            "INSERT INTO t_station_detail_current "
            "(Id,StationResultId,Sn,StationNo,StationName,StationType,"
            "StationResult,StartTime,EndTime,AllImageUrls) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (detail_id, result_id, extra_sn, st_no, st_name, st_type,
             2, start_time, end_time, "[]")
        )
        # Insert 2-3 defects per station for this specific SN
        for df in random.sample(DEFECT_TYPES, min(3, len(DEFECT_TYPES))):
            area = random.choice(PRODUCT_AREAS)
            defect_item = _make_defect_json(df, area)
            defects_json = json.dumps([defect_item], ensure_ascii=False)
            inspec_id += 1
            cur.execute(
                "INSERT INTO t_inspection_detail_current "
                "(Id,StationResultId,StationDetailId,Sn,StationNo,Result,"
                "SingleImagePath,ImageWidth,ImageHeight,Measurements,Defects,Time) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (inspec_id, result_id, detail_id, extra_sn, st_no, 2,
                 f"/images/{extra_sn}/{st_no}/{inspec_id}.jpg",
                 2448, 2048, "[]", defects_json, start_time + timedelta(seconds=30))
            )

    db.commit()
    cur.close()
    db.close()

    print(f"\nDone! Inserted:")
    print(f"  t_station_result_current:     {total_results} rows")
    print(f"  t_station_detail_current:     {total_details} rows")
    print(f"  t_inspection_detail_current:  {total_inspections} rows")
    print(f"  Extra for SN {extra_sn}:       {len(STATIONS[:3])} detail rows + defects")
    print(f"\nData spans the last {DAYS_BACK} days.")
    print("Launch the app and click '质量看板' to see the dashboard charts.")


if __name__ == "__main__":
    main()
