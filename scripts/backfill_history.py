import json
import time
from pathlib import Path

import requests

# 測試股票：中信金
STOCK_CODE = "2891"

# 下載最近 12 個月份
MONTHS_TO_DOWNLOAD = 12

URL = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
OUTPUT_DIR = Path("data/backfill_test")


def fetch_month(session, year, month):
    params = {
        "date": f"{year}{month:02d}01",
        "stockNo": STOCK_CODE,
        "response": "json",
    }

    response = session.get(URL, params=params, timeout=30)
    response.raise_for_status()

    result = response.json()

    if result.get("stat") != "OK":
        raise RuntimeError(
            f"{STOCK_CODE} {year}-{month:02d} 下載失敗："
            f"{result.get('stat')}"
        )

    return result


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    # 從目前月份往前計算 12 個月份
    from datetime import date

    today = date.today()
    months = []

    year = today.year
    month = today.month

    for _ in range(MONTHS_TO_DOWNLOAD):
        months.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    months.reverse()

    success_count = 0

    for year, month in months:
        output_file = OUTPUT_DIR / (
            f"{STOCK_CODE}_{year}{month:02d}.json"
        )

        # 已存在的檔案就跳過，方便重新執行
        if output_file.exists():
            print(f"跳過已存在檔案：{output_file}")
            success_count += 1
            continue

        try:
            result = fetch_month(session, year, month)

            output_file.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            row_count = len(result.get("data", []))
            print(
                f"成功：{year}-{month:02d}，"
                f"取得 {row_count} 筆資料"
            )

            success_count += 1

        except Exception as exc:
            print(f"錯誤：{year}-{month:02d}：{exc}")
            raise

        # 降低連續請求頻率
        time.sleep(3)

    print(
        f"完成！成功保存 {success_count}/{MONTHS_TO_DOWNLOAD} 個月份。"
    )


if __name__ == "__main__":
    main()
