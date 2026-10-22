
import json
import time
from pathlib import Path

import requests

# 先測試一檔股票、一個月份，確認資料來源可用
STOCK_CODE = "2891"
YEAR = 2026
MONTH = 9

URL = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"


def main():
    params = {
        "date": f"{YEAR}{MONTH:02d}01",
        "stockNo": STOCK_CODE,
        "response": "json",
    }

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        URL,
        params=params,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if result.get("stat") != "OK":
        raise RuntimeError(
            f"證交所沒有回傳有效資料：{result.get('stat')}"
        )

    output_dir = Path("data/backfill_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{STOCK_CODE}_{YEAR}{MONTH:02d}.json"

    output_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"測試成功，資料已寫入：{output_file}")
    print(f"取得 {len(result.get('data', []))} 筆資料")


if __name__ == "__main__":
    main()
