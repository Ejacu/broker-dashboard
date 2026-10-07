"""GitHub Actions 每日排程用:抓當天資料、彙總後推送到 Bluehost 的 upload.php。
不寫任何本機檔案,也不保留逐筆明細,只送出「已聚合」的券商買賣超數據。
"""
import os
import sys
import time
from datetime import date, timedelta

import requests
from FinMind.data import DataLoader

# 沒有另外設定 STOCK_IDS 環境變數時的預設值(僅供本機測試用)
FALLBACK_STOCK_IDS = ["2330", "2317", "2454"]

# 每次執行都檢查最近幾天有沒有缺口並補上,而不是只看「今天」——
# 這樣排程偶爾失敗個幾天,下次成功執行時會自動追上,不需要人工介入
LOOKBACK_DAYS = 10

# Bluehost 的防護機制會擋掉 requests 預設的 User-Agent(python-requests/x.x),
# 偽裝成一般瀏覽器才不會被 WAF 判定成機器人擋掉(406 Not Acceptable)
UPLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

HTTP_MAX_RETRY = 8
HTTP_RETRY_BACKOFF = 20  # 秒,每次重試遞增(20, 40, 60...),拉長是因為 Bluehost 擋 GitHub IP 有時會持續好幾分鐘


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


def get_existing_dates(dates_url: str, stock_id: str) -> set:
    resp = request_with_retry("GET", dates_url, params={"stock": stock_id}, timeout=30)
    return set(resp.json())


def recent_dates(lookback_days: int) -> list:
    """最近 N 天,排除週末——週末永遠不會有交易資料,不用每次都白問一次"""
    today = date.today()
    days = [today - timedelta(days=i) for i in range(lookback_days)]
    return [d.strftime("%Y-%m-%d") for d in days if d.weekday() < 5]


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


def summarize_price(df) -> list:
    """官方日 OHLC + 漲跌(來自 taiwan_stock_daily,跟分點資料是不同的 dataset)。
    這個 dataset 支援一次查一段日期範圍,不用像分點資料那樣逐日查。"""
    records = []
    if df.empty:
        return records
    df = df.sort_values("date")
    has_spread = "spread" in df.columns
    has_ohlc = "open" in df.columns and "max" in df.columns and "min" in df.columns
    has_volume = "Trading_Volume" in df.columns
    prev_close = None
    for _, row in df.iterrows():
        close = float(row["close"])
        open_p = float(row["open"]) if has_ohlc else close
        high_p = float(row["max"]) if has_ohlc else close
        low_p = float(row["min"]) if has_ohlc else close
        volume_lots = (float(row["Trading_Volume"]) / 1000.0) if has_volume else 0.0
        if has_spread:
            change_val = float(row["spread"])
        elif prev_close is not None:
            change_val = close - prev_close
        else:
            change_val = 0.0
        base = close - change_val
        change_pct = (change_val / base * 100.0) if base else 0.0
        records.append({
            "stock_id": str(row["stock_id"]),
            "date": str(row["date"]),
            "open": round(open_p, 2),
            "high": round(high_p, 2),
            "low": round(low_p, 2),
            "close": round(close, 2),
            "volume": round(volume_lots, 1),
            "change": round(change_val, 2),
            "change_pct": round(change_pct, 2),
        })
        prev_close = close
    return records


def update_price_range(upload_url: str, upload_token: str, api: DataLoader, stock_id: str, start_date: str, end_date: str) -> None:
    try:
        df = api.taiwan_stock_daily(stock_id=stock_id, start_date=start_date, end_date=end_date)
    except Exception as exc:
        print(f"{stock_id} 收盤價查詢失敗 {start_date}~{end_date}: {exc}")
        return
    if df.empty:
        return
    price_records = summarize_price(df)
    if not price_records:
        return
    resp = request_with_retry(
        "POST",
        upload_url,
        json={"token": upload_token, "records": [], "detail_records": [], "price_records": price_records},
        timeout=60,
    )
    print(f"{stock_id} 收盤價 {start_date}~{end_date}: {len(price_records)} 筆 -> {resp.status_code}")


def update_one(upload_url: str, upload_token: str, api: DataLoader, stock_id: str, trade_date: str) -> None:
    df = api.taiwan_stock_trading_daily_report(stock_id=stock_id, date=trade_date)
    if df.empty:
        print(f"{stock_id} {trade_date} 無資料(可能非交易日),略過")
        return

    records = summarize(df, stock_id, trade_date)
    detail_records = summarize_price_detail(df, stock_id, trade_date)

    if not records and not detail_records:
        print(f"{stock_id} {trade_date}: 淨部位皆為 0,沒東西可存,略過")
        return

    resp = request_with_retry(
        "POST",
        upload_url,
        json={"token": upload_token, "records": records, "detail_records": detail_records},
        timeout=60,
    )
    print(f"{stock_id} {trade_date}: 彙總 {len(records)} 筆、明細 {len(detail_records)} 筆 -> {resp.status_code}")


def main():
    token = os.environ["FINMIND_TOKEN"]
    upload_url = os.environ["UPLOAD_URL"]
    upload_token = os.environ["UPLOAD_TOKEN"]
    stocks_url = os.environ.get("STOCKS_URL", upload_url.replace("upload.php", "stocks.php"))
    dates_url = os.environ.get("DATES_URL", upload_url.replace("upload.php", "dates.php"))
    override_date = os.environ.get("TRADE_DATE")

    api = DataLoader()
    api.login_by_token(api_token=token)

    stock_ids = get_current_stock_ids(stocks_url)
    print(f"依資料庫既有清單,共 {len(stock_ids)} 檔股票")

    # 每檔股票各自送一次請求,避免單一請求塞進上萬筆明細導致 PHP 執行逾時
    for stock_id in stock_ids:
        if override_date:
            # 手動指定日期時(除錯/補特定一天用),不做缺口檢查,就只抓這一天
            target_dates = [override_date]
            price_start, price_end = override_date, override_date
        else:
            # 正常排程:檢查最近 LOOKBACK_DAYS 天裡,資料庫還缺哪幾天,自動補上
            existing = get_existing_dates(dates_url, stock_id)
            all_recent = recent_dates(LOOKBACK_DAYS)
            target_dates = [d for d in all_recent if d not in existing]
            price_start, price_end = (min(all_recent), max(all_recent)) if all_recent else (None, None)

        for trade_date in target_dates:
            update_one(upload_url, upload_token, api, stock_id, trade_date)

        # 收盤價一次查一段範圍就好,不用像分點資料那樣逐日查缺口,
        # 每天都重查一次最近這段範圍,自動蓋掉舊值,成本只有多一次 API 呼叫
        if price_start and price_end:
            update_price_range(upload_url, upload_token, api, stock_id, price_start, price_end)


if __name__ == "__main__":
    main()
