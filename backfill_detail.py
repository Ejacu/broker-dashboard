"""一次性匯入「價位明細」:只回填最近 N 天(避免資料量太大灌爆 Bluehost 資料庫)。
彙總數據(broker_summary)已經灌過了,這支只補 broker_price_detail。

執行前,先在終端機設定:
    $env:UPLOAD_URL = "https://你的網域/broker/upload.php"
    $env:UPLOAD_TOKEN = "跟 config.php 裡 UPLOAD_TOKEN 一樣的值"
"""
import glob
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import requests

from daily_update import summarize_price_detail, UPLOAD_HEADERS

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "broker_data", "raw")
DAYS_BACK = 30
BATCH_SIZE = 5    # 明細資料量大,每批檔案數放少一點,避免單次 PHP 執行過久
SLEEP_SECONDS = 0.3


def main():
    upload_url = os.environ["UPLOAD_URL"]
    upload_token = os.environ["UPLOAD_TOKEN"]

    cutoff = datetime.now() - timedelta(days=DAYS_BACK)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    all_files = glob.glob(os.path.join(RAW_DIR, "**", "*.csv"), recursive=True)
    csv_files = sorted(f for f in all_files if os.path.basename(f).replace(".csv", "") >= cutoff_str)
    print(f"共 {len(all_files)} 個檔案,篩選最近 {DAYS_BACK} 天(>= {cutoff_str})後剩 {len(csv_files)} 個要匯入")

    ok_files, failed_batches = 0, []
    batch_records = []
    batch_names = []

    def flush_batch():
        nonlocal ok_files, batch_records, batch_names
        if not batch_names:
            return
        try:
            resp = requests.post(
                upload_url,
                json={"token": upload_token, "records": [], "detail_records": batch_records},
                headers=UPLOAD_HEADERS,
                timeout=90,
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
            batch_records.extend(summarize_price_detail(df, stock_id, trade_date))
        batch_names.append(f"{stock_id}/{trade_date}")

        if len(batch_names) >= BATCH_SIZE:
            flush_batch()

        if i % 200 == 0:
            print(f"進度 {i}/{len(csv_files)}")

    flush_batch()

    print(f"完成。成功 {ok_files} 檔,失敗批次 {len(failed_batches)} 組")
    if failed_batches:
        print("失敗批次清單:", failed_batches)


if __name__ == "__main__":
    main()
