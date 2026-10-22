
import json
from pathlib import Path
from datetime import datetime

SOURCE_DIR = Path("data/backfill_test")
OUTPUT_FILE = Path("data/stock_history/2891.json")

def to_number(value):
    value = str(value).replace(",", "").strip()
    if not value or value in {"--", "---"}:
        return None
    return float(value)

def convert_date(value):
    # 民國年 115/10/01 -> 西元 2026-10-01
    year, month, day = map(int, value.split("/"))
    return f"{year + 1911:04d}-{month:02d}-{day:02d}"

def main():
    rows = {}

    for file in sorted(SOURCE_DIR.glob("2891_*.json")):
        with file.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        if payload.get("stat") != "OK":
            print(f"略過資料異常：{file.name}")
            continue

        for item in payload.get("data", []):
            if len(item) < 9:
                continue

            date = convert_date(item[0])
            rows[date] = {
                "date": date,
                "code": "2891",
                "name": "中信金",
                "volume": int(item[1].replace(",", "")),
                "value": int(item[2].replace(",", "")),
                "open": to_number(item[3]),
                "high": to_number(item[4]),
                "low": to_number(item[5]),
                "close": to_number(item[6]),
                "change": to_number(item[7]),
                "transactions": int(item[8].replace(",", "")),
            }

    result = {
        "meta": {
            "code": "2891",
            "name": "中信金",
            "source": "臺灣證券交易所每日成交資訊",
            "row_count": len(rows),
        },
        "stocks": [rows[date] for date in sorted(rows)],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"轉換完成：{len(rows)} 筆交易日資料")
    print(f"輸出位置：{OUTPUT_FILE}")

if __name__ == "__main__":
    main()
