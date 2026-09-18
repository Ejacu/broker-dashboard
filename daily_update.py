"""GitHub Actions 每日排程用:抓當天資料、彙總後推送到 Bluehost 的 upload.php。
不寫任何本機檔案,也不保留逐筆明細,只送出「已聚合」的券商買賣超數據。
"""
import os
import sys
from datetime import date

import requests
from FinMind.data import DataLoader

TEST_STOCK_IDS = ["2330", "2317", "2454"]

# Bluehost 的防護機制會擋掉 requests 預設的 User-Agent(python-requests/x.x),
# 偽裝成一般瀏覽器才不會被 WAF 判定成機器人擋掉(406 Not Acceptable)
UPLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def summarize(df, stock_id: str, trade_date: str) -> list:
    records = []
    for broker, group in df.groupby("securities_trader"):
        b_shares = group["buy"].sum()
        s_shares = group["sell"].sum()
        net_lots = (b_shares - s_shares) / 1000.0
        if net_lots == 0:
            continue

        b_amt = (group["price"] * group["buy"]).sum()
        s_amt = (group["price"] * group["sell"]).sum()
        buy_avg = (b_amt / b_shares) if b_shares > 0 else 0.0
        sell_avg = (s_amt / s_shares) if s_shares > 0 else 0.0
        main_avg = buy_avg if net_lots > 0 else (sell_avg if net_lots < 0 else (buy_avg or sell_avg))

        records.append({
            "stock_id": stock_id,
            "date": trade_date,
            "broker": broker,
            "buy_avg": round(buy_avg, 2),
            "sell_avg": round(sell_avg, 2),
            "main_avg": round(main_avg, 2),
            "net_lots": round(net_lots, 1),
            "total_buy_lots": round(b_shares / 1000.0, 1),
            "total_sell_lots": round(s_shares / 1000.0, 1),
        })
    return records


def main():
    token = os.environ["FINMIND_TOKEN"]
    upload_url = os.environ["UPLOAD_URL"]
    upload_token = os.environ["UPLOAD_TOKEN"]
    trade_date = os.environ.get("TRADE_DATE", date.today().strftime("%Y-%m-%d"))

    api = DataLoader()
    api.login_by_token(api_token=token)

    all_records = []
    for stock_id in TEST_STOCK_IDS:
        df = api.taiwan_stock_trading_daily_report(stock_id=stock_id, date=trade_date)
        if df.empty:
            print(f"{stock_id} {trade_date} 無資料(可能非交易日),略過")
            continue
        records = summarize(df, stock_id, trade_date)
        all_records.extend(records)
        print(f"{stock_id} {trade_date}: {len(records)} 筆券商彙總")

    if not all_records:
        print("今天沒有任何資料需要上傳,結束")
        return

    resp = requests.post(
        upload_url,
        json={"token": upload_token, "records": all_records},
        headers=UPLOAD_HEADERS,
        timeout=30,
    )
    print(f"上傳結果: {resp.status_code} {resp.text}")
    resp.raise_for_status()


if __name__ == "__main__":
    main()
