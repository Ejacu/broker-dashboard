"""一次性匯入:把本機已下載好的 broker_data/raw/{股票代號}/{日期}.csv 全部彙總後,
灌進 Bluehost 上的 MySQL(透過 upload.php)。之後每天的新資料交給 daily_update.py 處理。

執行前,先在終端機設定:
    $env:UPLOAD_URL = "https://你的網域/broker/upload.php"
    $env:UPLOAD_TOKEN = "跟 config.php 裡 UPLOAD_TOKEN 一樣的值"
"""
import glob
import os
import time

import pandas as pd
import requests

from daily_update import summarize, UPLOAD_HEADERS

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "broker_data", "raw")
BATCH_SIZE = 10          # 每幾個檔案的彙總結果合併成一次 HTTP 請求送出
SLEEP_SECONDS = 0.3      # 每次請求(不是每個檔案)之間的間隔


def main():
    upload_url = os.environ["UPLOAD_URL"]
    upload_token = os.environ["UPLOAD_TOKEN"]

    csv_files = sorted(glob.glob(os.path.join(RAW_DIR, "**", "*.csv"), recursive=True))
    print(f"共 {len(csv_files)} 個檔案要匯入,每 {BATCH_SIZE} 個檔案合併送出一次")

    ok_files, failed_batches = 0, []
    batch_records = []
    batch_names = []

    def flush_batch():
        nonlocal ok_files, batch_records, batch_names
        if not batch_records:
            return
        try:
            resp = requests.post(
                upload_url,
                json={"token": upload_token, "records": batch_records},
                headers=UPLOAD_HEADERS,
                timeout=60,
            )
            resp.raise_for_status()
            ok_files += len(batch_names)
        except Exception as exc:
            print(f"  [失敗] 批次 {batch_names[0]}..{batch_names[-1]}: {exc}")
            failed_batches.append((batch_names[0], batch_names[-1], str(exc)))
        batch_records = []
        batch_names = []
        time.sleep(SLEEP_SECONDS)

    for i, filepath in enumerate(csv_files, start=1):
        stock_id = os.path.basename(os.path.dirname(filepath))
        trade_date = os.path.basename(filepath).replace(".csv", "")

        df = pd.read_csv(filepath, encoding="utf-8-sig")
        if not df.empty:
            records = summarize(df, stock_id, trade_date)
            batch_records.extend(records)
        batch_names.append(f"{stock_id}/{trade_date}")

        if len(batch_names) >= BATCH_SIZE:
            flush_batch()

        if i % 1000 == 0:
            print(f"進度 {i}/{len(csv_files)}")

    flush_batch()  # 收尾,送出最後不滿一批的資料

    print(f"完成。成功 {ok_files} 檔,失敗批次 {len(failed_batches)} 組")
    if failed_batches:
        print("失敗批次清單:", failed_batches)


if __name__ == "__main__":
    main()
