
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

    # 部分股票的漲跌價差可能包含特殊字元
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--codes",
        nargs="+",
        required=True,
        help="股票代號，例如 2891 2330 2317",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        for code in args.codes:
            records = {}

            for year, month in get_months():
                try:
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
                except Exception as exc:
                    print(f"{code} {year}-{month:02d} 失敗：{exc}")
                    raise

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

            path = OUTPUT_DIR / f"{code}.json"
            path.write_text(
                json.dumps(output, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            print(f"{code} 完成：{len(records)} 個交易日，存至 {path}")


if __name__ == "__main__":
    main()
