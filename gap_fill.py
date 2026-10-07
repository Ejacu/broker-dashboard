"""本機手動維護用:跟 Bluehost 資料庫核對「每一檔股票實際缺哪幾天」,只把真正缺的部分
補上去,而不是整批重送。適合每次跑完 broker_pro.py 之後,拿來把新抓到的資料同步上網站。

執行前,先在終端機設定:
    $env:UPLOAD_URL = "https://sgq.vwa.mybluehost.me/broker/upload.php"
    $env:UPLOAD_TOKEN = "跟 Bluehost config.php 裡 UPLOAD_TOKEN 一樣的值"
    $env:FINMIND_TOKEN = "..."   # 選填,有設才會順便補收盤價
    $env:ONLY_STOCKS = "3551"    # 選填,只想處理特定股票(逗號分隔)時設定,不設就整批掃
"""
import glob
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import requests
from FinMind.data import DataLoader
from daily_update import summarize, summarize_price_detail, UPLOAD_HEADERS, update_price_range

UPLOAD_URL = os.environ["UPLOAD_URL"]
UPLOAD_TOKEN = os.environ["UPLOAD_TOKEN"]
# 收盤價要另外呼叫 FinMind 的 taiwan_stock_daily,需要登入 token;
# 沒設的話就跳過收盤價補齊(分點資料不受影響)
FINMIND_TOKEN = os.environ.get("FINMIND_TOKEN")
DATES_URL = UPLOAD_URL.replace("upload.php", "dates.php")
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "broker_data", "raw")
DETAIL_CUTOFF_DAYS = 30
PRICE_HISTORY_DAYS = 370
BATCH_SIZE = 5
SLEEP_SECONDS = 0.3


def post_with_retry(records, detail_records, max_retry: int = 3) -> bool:
    for attempt in range(1, max_retry + 1):
        try:
            resp = requests.post(
                UPLOAD_URL,
                json={"token": UPLOAD_TOKEN, "records": records, "detail_records": detail_records},
                headers=UPLOAD_HEADERS,
                timeout=90,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            print(f"    [重試 {attempt}/{max_retry}] {exc}")
            time.sleep(3)
    return False


def main():
    from datetime import date, timedelta
    detail_cutoff = (date.today() - timedelta(days=DETAIL_CUTOFF_DAYS)).strftime("%Y-%m-%d")

    api = None
    if FINMIND_TOKEN:
        api = DataLoader()
        api.login_by_token(api_token=FINMIND_TOKEN)
    else:
        print("沒設定 FINMIND_TOKEN,這次只補分點資料,不會補收盤價")

    stock_dirs = sorted(os.listdir(RAW_DIR)) if os.path.isdir(RAW_DIR) else []

    # 只想處理特定幾檔(例如剛用 broker_pro.py 新抓的股票)時,
    # 設定 ONLY_STOCKS 環境變數(逗號分隔)就不用整批重掃
    only_raw = os.environ.get("ONLY_STOCKS", "").strip()
    if only_raw:
        only_ids = {s.strip() for s in only_raw.split(",") if s.strip()}
        stock_dirs = [s for s in stock_dirs if s in only_ids]
        print(f"ONLY_STOCKS 篩選後,只處理: {stock_dirs}")

    print(f"共 {len(stock_dirs)} 檔股票要核對缺口")

    total_missing, total_fixed, total_still_failed = 0, 0, 0

    for si, stock_id in enumerate(stock_dirs, start=1):
        try:
            resp = requests.get(f"{DATES_URL}?stock={stock_id}", headers=UPLOAD_HEADERS, timeout=30)
            resp.raise_for_status()
            have_dates = set(resp.json())
        except Exception as exc:
            print(f"{stock_id}: 查詢既有日期失敗,跳過這檔: {exc}")
            continue

        if api:
            price_start = (date.today() - timedelta(days=PRICE_HISTORY_DAYS)).strftime("%Y-%m-%d")
            price_end = date.today().strftime("%Y-%m-%d")
            update_price_range(UPLOAD_URL, UPLOAD_TOKEN, api, stock_id, price_start, price_end)

        local_files = sorted(glob.glob(os.path.join(RAW_DIR, stock_id, "*.csv")))
        missing = [f for f in local_files if os.path.basename(f).replace(".csv", "") not in have_dates]

        if not missing:
            continue

        total_missing += len(missing)
        print(f"[{si}/{len(stock_dirs)}] {stock_id}: 缺 {len(missing)} 天,補送中...")

        batch_records, batch_detail, batch_count = [], [], 0
        for filepath in missing:
            trade_date = os.path.basename(filepath).replace(".csv", "")
            df = pd.read_csv(filepath, encoding="utf-8-sig")
            if not df.empty:
                batch_records.extend(summarize(df, stock_id, trade_date))
                if trade_date >= detail_cutoff:
                    batch_detail.extend(summarize_price_detail(df, stock_id, trade_date))
            batch_count += 1

            if batch_count >= BATCH_SIZE:
                if post_with_retry(batch_records, batch_detail):
                    total_fixed += batch_count
                else:
                    total_still_failed += batch_count
                    print(f"    仍然失敗: {stock_id} 這一批 {batch_count} 天")
                batch_records, batch_detail, batch_count = [], [], 0
                time.sleep(SLEEP_SECONDS)

        if batch_count > 0:
            if post_with_retry(batch_records, batch_detail):
                total_fixed += batch_count
            else:
                total_still_failed += batch_count
                print(f"    仍然失敗: {stock_id} 這一批 {batch_count} 天")
            time.sleep(SLEEP_SECONDS)

    print(f"完成。原本缺 {total_missing} 天,補上 {total_fixed} 天,仍然失敗 {total_still_failed} 天")


if __name__ == "__main__":
    main()
