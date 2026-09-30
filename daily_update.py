"""GitHub Actions 每日排程用:抓當天資料、彙總後推送到 Bluehost 的 upload.php。
不寫任何本機檔案,也不保留逐筆明細,只送出「已聚合」的券商買賣超數據。
"""
import os
import sys
import time
from datetime import date

import requests
from FinMind.data import DataLoader

# 沒有另外設定 STOCK_IDS 環境變數時的預設值(僅供本機測試用)
FALLBACK_STOCK_IDS = ["2330", "2317", "2454"]

# Bluehost 的防護機制會擋掉 requests 預設的 User-Agent(python-requests/x.x),
# 偽裝成一般瀏覽器才不會被 WAF 判定成機器人擋掉(406 Not Acceptable)
UPLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

HTTP_MAX_RETRY = 5
HTTP_RETRY_BACKOFF = 10  # 秒,每次重試遞增(10, 20, 30...)


def request_with_retry(method: str, url: str, max_retry: int = HTTP_MAX_RETRY, **kwargs) -> requests.Response:
    """GitHub Actions 的雲端 IP 偶爾會被 Bluehost 的防護機制擋下(403/409 等),
    多數情況下重試幾次就能通過,不是真的永久封鎖。"""
    last_exc = None
    for attempt in range(1, max_retry + 1):
        try:
            resp = requests.request(method, url, headers=UPLOAD_HEADERS, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            wait = HTTP_RETRY_BACKOFF * attempt
            print(f"    [HTTP 重試 {attempt}/{max_retry}] {method} {url} 失敗: {exc} -> 等待 {wait}s")
            time.sleep(wait)
    raise last_exc


def get_current_stock_ids(stocks_url: str) -> list:
    """跟資料庫既有的股票清單同步,避免每天只更新固定幾檔,新加的股票也要繼續追蹤"""
    resp = request_with_retry("GET", stocks_url, timeout=30)
    stock_ids = resp.json()
    return stock_ids if stock_ids else FALLBACK_STOCK_IDS


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


def summarize_price_detail(df, stock_id: str, trade_date: str) -> list:
    """各券商在各價位的買賣張數明細(氣泡圖點進去看價位分布用)"""
    records = []
    grouped = df.groupby(["securities_trader", "price"])[["buy", "sell"]].sum().reset_index()
    for _, row in grouped.iterrows():
        buy_lots = row["buy"] / 1000.0
        sell_lots = row["sell"] / 1000.0
        if buy_lots == 0 and sell_lots == 0:
            continue
        records.append({
            "stock_id": stock_id,
            "date": trade_date,
            "broker": row["securities_trader"],
            "price": round(float(row["price"]), 2),
            "buy_lots": round(buy_lots, 1),
            "sell_lots": round(sell_lots, 1),
        })
    return records


def main():
    token = os.environ["FINMIND_TOKEN"]
    upload_url = os.environ["UPLOAD_URL"]
    upload_token = os.environ["UPLOAD_TOKEN"]
    stocks_url = os.environ.get("STOCKS_URL", upload_url.replace("upload.php", "stocks.php"))
    trade_date = os.environ.get("TRADE_DATE", date.today().strftime("%Y-%m-%d"))

    api = DataLoader()
    api.login_by_token(api_token=token)

    stock_ids = get_current_stock_ids(stocks_url)
    print(f"依資料庫既有清單,今天要更新 {len(stock_ids)} 檔股票")

    # 每檔股票各自送一次請求,避免單一請求塞進上萬筆明細導致 PHP 執行逾時
    for stock_id in stock_ids:
        df = api.taiwan_stock_trading_daily_report(stock_id=stock_id, date=trade_date)
        if df.empty:
            print(f"{stock_id} {trade_date} 無資料(可能非交易日),略過")
            continue

        records = summarize(df, stock_id, trade_date)
        detail_records = summarize_price_detail(df, stock_id, trade_date)

        if not records and not detail_records:
            print(f"{stock_id} {trade_date}: 淨部位皆為 0,沒東西可存,略過")
            continue

        resp = request_with_retry(
            "POST",
            upload_url,
            json={"token": upload_token, "records": records, "detail_records": detail_records},
            timeout=60,
        )
        print(f"{stock_id} {trade_date}: 彙總 {len(records)} 筆、明細 {len(detail_records)} 筆 -> {resp.status_code}")


if __name__ == "__main__":
    main()
