import os


def export_to_excel(path: str, headers: list, rows: list):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        _export_csv(path, headers, rows)
    else:
        _export_xlsx(path, headers, rows)


def _export_csv(path: str, headers: list, rows: list):
    import csv
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def _export_xlsx(path: str, headers: list, rows: list):
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for row in rows:
            ws.append(row)
        wb.save(path)
    except ImportError:
        # Fallback to CSV if openpyxl not available
        import csv
        csv_path = path.replace(".xlsx", ".csv")
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        raise ImportError("openpyxl 未安装，已导出为 CSV 文件")