"""本機一次性執行用:幫「這次改版之前就已經在追蹤」的股票補官方收盤價歷史。
daily_update.py / expand_universe.py 只會覆蓋最近幾天 / 新加入的股票,
既有股票的收盤價歷史需要這支腳本補一次,之後就交給前兩支程式自動維護。

執行前,先在終端機設定:
    $env:FINMIND_TOKEN = "..."
    $env:UPLOAD_URL = "https://sgq.vwa.mybluehost.me/broker/upload.php"
    $env:UPLOAD_TOKEN = "..."
"""
import os
import sys
import time
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

import requests
from FinMind.data import DataLoader
from daily_update import UPLOAD_HEADERS, update_price_range

HISTORY_DAYS = 370
SLEEP_SECONDS = 0.5


def get_all_stock_ids(stocks_url: str) -> list:
    resp = requests.get(stocks_url, headers=UPLOAD_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main():
    token = os.environ["FINMIND_TOKEN"]
    upload_url = os.environ["UPLOAD_URL"]
    upload_token = os.environ["UPLOAD_TOKEN"]
    stocks_url = upload_url.replace("upload.php", "stocks.php")

    api = DataLoader()
    api.login_by_token(api_token=token)

    stock_ids = get_all_stock_ids(stocks_url)
    print(f"共 {len(stock_ids)} 檔股票要補收盤價")

    today = date.today()
    start = (today - timedelta(days=HISTORY_DAYS)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    for i, stock_id in enumerate(stock_ids, 1):
        print(f"[{i}/{len(stock_ids)}] {stock_id}")
        update_price_range(upload_url, upload_token, api, stock_id, start, end)
        time.sleep(SLEEP_SECONDS)

    print("全部補完")


if __name__ == "__main__":
    main()
