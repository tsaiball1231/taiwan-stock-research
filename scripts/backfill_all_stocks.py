
import json
import time
import argparse
from datetime import date
from pathlib import Path

import requests

URL = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
OUTPUT_DIR = Path("data/stock_history")
MONTHS_TO_DOWNLOAD = 12

STOCK_LIST_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"


def get_stock_list():
    response = requests.get(
        STOCK_LIST_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    codes = []
    for item in data:
        code = str(item.get("公司代號", "")).strip()
        if code.isdigit() and len(code) == 4:
            codes.append(code)

    return sorted(set(codes))


def to_roc_date(value):
    year, month, day = map(int, value.split("/"))
    return f"{year + 1911:04d}-{month:02d}-{day:02d}"


def to_number(value):
    value = str(value).replace(",", "").strip()

    if not value or value in {"--", "---"}:
        return None

    if value.startswith("X"):
        value = value[1:]

    try:
        return float(value)
    except ValueError:
        return None


def fetch_month(session, code, year, month):
    response = session.get(
        URL,
        params={
            "date": f"{year}{month:02d}01",
            "stockNo": code,
            "response": "json",
        },
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if result.get("stat") != "OK":
        raise RuntimeError(
            f"{code} {year}-{month:02d}：{result.get('stat')}"
        )

    return result


def get_months():
    today = date.today()
    months = []
    year, month = today.year, today.month

    for _ in range(MONTHS_TO_DOWNLOAD):
        months.append((year, month))
        month -= 1

        if month == 0:
            month = 12
            year -= 1

    return list(reversed(months))


def is_complete_file(path, code):
    """確認既有檔案是否看起來已包含完整的一年資料。"""
    if not path.exists():
        return False

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        stocks = data.get("stocks", [])
        meta = data.get("meta", {})

        return (
            meta.get("code") == code
            and meta.get("months_requested") == MONTHS_TO_DOWNLOAD
            and len(stocks) > 0
            and all(row.get("code") == code for row in stocks)
        )
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


def main():
    parser = argparse.ArgumentParser(
        description="分批下載上市股票近一年歷史資料"
    )
    parser.add_argument(
        "--codes",
        nargs="+",
        default=None,
        help="指定股票代號，例如 2891 2330 2317",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="從股票清單的第幾檔開始，從 0 計算",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="本次最多處理幾檔股票，預設 20 檔",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="重新下載已存在的股票資料",
    )
    args = parser.parse_args()
    print("程式啟動，準備處理股票資料", flush=True)

    if args.start < 0:
        parser.error("--start 不可小於 0")

    if args.limit <= 0:
        parser.error("--limit 必須大於 0")

    if args.codes:
        codes = sorted(set(args.codes))
    else:
        print("正在取得上市股票清單……")
        codes = get_stock_list()
        print(f"共取得 {len(codes)} 檔上市股票")

    batch_codes = codes[args.start:args.start + args.limit]

    if not batch_codes:
        print("這個範圍沒有股票可處理。")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(
        f"本次處理清單位置：{args.start}，"
        f"共 {len(batch_codes)} 檔"
    )

    completed = 0
    skipped = 0
    failed = []

    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        for code in batch_codes:
            path = OUTPUT_DIR / f"{code}.json"

            if not args.overwrite and is_complete_file(path, code):
                print(f"{code} 已有資料，跳過")
                skipped += 1
                continue

            records = {}

            try:
                months = get_months()

                for index, (year, month) in enumerate(months, start=1):
                    print(
                        f"[{code}] 正在下載第 {index}/{len(months)} 個月份："
                        f"{year}-{month:02d}",
                        flush=True,
                    )

                    result = fetch_month(session, code, year, month)

                    for row in result.get("data", []):
                        if len(row) < 9:
                            continue

                        day = to_roc_date(row[0])

                        records[day] = {
                            "date": day,
                            "code": code,
                            "volume": int(row[1].replace(",", "")),
                            "value": int(row[2].replace(",", "")),
                            "open": to_number(row[3]),
                            "high": to_number(row[4]),
                            "low": to_number(row[5]),
                            "close": to_number(row[6]),
                            "change": to_number(row[7]),
                            "transactions": int(
                                row[8].replace(",", "")
                            ),
                        }

                    print(f"{code} {year}-{month:02d} 完成")
                    time.sleep(3)

                output = {
                    "meta": {
                        "code": code,
                        "row_count": len(records),
                        "months_requested": MONTHS_TO_DOWNLOAD,
                    },
                    "stocks": [
                        records[day] for day in sorted(records)
                    ],
                }

                path.write_text(
                    json.dumps(output, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                print(
                    f"{code} 完成：{len(records)} 個交易日，"
                    f"存至 {path}"
                )
                completed += 1

            except Exception as exc:
                print(f"{code} 下載失敗：{exc}")
                failed.append(code)

                # 遇到錯誤先停止，避免持續對 API 發出請求。
                break

    print("\n本批次結果")
    print(f"成功下載：{completed} 檔")
    print(f"跳過既有資料：{skipped} 檔")
    print(f"失敗：{failed}")

    if failed:
        print("請確認錯誤原因，再重新執行失敗的股票。")


if __name__ == "__main__":
    main()
