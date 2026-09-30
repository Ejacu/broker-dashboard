"""GitHub Actions 每日排程用:自動擴大股票覆蓋範圍。

每次執行,從「全市場清單」裡挑出資料庫還沒有的股票,取前 BATCH_SIZE 檔,
補齊 HISTORY_DAYS 天的彙總資料(氣泡圖+總表用)以及最近 DETAIL_DAYS 天的
明細資料(依分點/依成交價查詢用,跟現有 78 檔的政策一致,避免資料庫無限膨脹)。

跑完這批,這些股票就會出現在 stocks.php 裡,明天執行時會自動排除、繼續下一批,
直到全市場都涵蓋為止。
"""
import os
import time
from datetime import date, datetime, timedelta

from FinMind.data import DataLoader

from daily_update import summarize, summarize_price_detail, request_with_retry

BATCH_SIZE = 50
HISTORY_DAYS = 370   # 新股票要往前補多少天的彙總資料(略多於一年,涵蓋所有交易日)
DETAIL_DAYS = 30     # 新股票要往前補多少天的明細資料
SLEEP_SECONDS = 0.7  # 每次 FinMind 請求間隔,對齊 broker_pro.py 的節流設定
MAX_RETRY = 5
RATE_LIMIT_BACKOFF = 60

# 這些類別通常沒有券商分點資料(大盤指數等),先跳過避免浪費額度
EXCLUDE_INDUSTRY_CATEGORY = {"所有證券", "Index", "大盤"}
# ETF 的 industry_category 是「上市指數股票型基金(ETF)」這種帶中文前綴的完整字串,
# 用完全比對抓不到,要用「字串包含」比對
EXCLUDE_INDUSTRY_KEYWORDS = ["ETF"]


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d.strftime("%Y-%m-%d")
        d += timedelta(days=1)


def get_full_market_stock_ids(api: DataLoader) -> list:
    info = api.taiwan_stock_info()
    info = info[info["type"].isin(["twse", "tpex"])]
    info = info[~info["industry_category"].isin(EXCLUDE_INDUSTRY_CATEGORY)]
    for keyword in EXCLUDE_INDUSTRY_KEYWORDS:
        info = info[~info["industry_category"].str.contains(keyword, na=False)]
    return sorted(info["stock_id"].unique().tolist())


def get_tracked_stock_ids(stocks_url: str) -> set:
    resp = request_with_retry("GET", stocks_url, timeout=30)
    return set(resp.json())


def fetch_one(api: DataLoader, stock_id: str, trade_date: str):
    """單檔股票單日查詢,失敗時重試+退避,絕不靜默丟資料"""
    for attempt in range(1, MAX_RETRY + 1):
        try:
            return api.taiwan_stock_trading_daily_report(stock_id=stock_id, date=trade_date)
        except Exception as exc:
            msg = str(exc)
            is_rate_limit = any(k in msg for k in ("402", "429", "level", "Level"))
            wait = RATE_LIMIT_BACKOFF if is_rate_limit else 2
            print(f"    [重試 {attempt}/{MAX_RETRY}] {stock_id} {trade_date} 失敗: {msg[:120]} -> 等待 {wait}s")
            time.sleep(wait)
    return None


def main():
    token = os.environ["FINMIND_TOKEN"]
    upload_url = os.environ["UPLOAD_URL"]
    upload_token = os.environ["UPLOAD_TOKEN"]
    stocks_url = os.environ.get("STOCKS_URL", upload_url.replace("upload.php", "stocks.php"))

    api = DataLoader()
    api.login_by_token(api_token=token)

    full_market = get_full_market_stock_ids(api)
    tracked = get_tracked_stock_ids(stocks_url)
    untracked = [s for s in full_market if s not in tracked]

    print(f"全市場 {len(full_market)} 檔,已涵蓋 {len(tracked)} 檔,尚未涵蓋 {len(untracked)} 檔")

    if not untracked:
        print("全市場都已經涵蓋了,沒有新股票要補")
        return

    batch = untracked[:BATCH_SIZE]
    print(f"這次處理 {len(batch)} 檔: {batch}")

    today = date.today()
    history_start = today - timedelta(days=HISTORY_DAYS)
    detail_start = today - timedelta(days=DETAIL_DAYS)

    for stock_id in batch:
        ok_days, fail_days = 0, 0
        for d_str in daterange(history_start, today):
            df = fetch_one(api, stock_id, d_str)
            time.sleep(SLEEP_SECONDS)

            if df is None:
                fail_days += 1
                continue
            if df.empty:
                continue

            records = summarize(df, stock_id, d_str)
            d_date = datetime.strptime(d_str, "%Y-%m-%d").date()
            detail_records = summarize_price_detail(df, stock_id, d_str) if d_date >= detail_start else []

            if not records and not detail_records:
                # 當天所有券商淨部位剛好都是 0(常見於冷門 ETF/債券型商品),
                # 沒東西可存,直接跳過,不要對著空結果重試
                continue

            try:
                request_with_retry(
                    "POST",
                    upload_url,
                    json={"token": upload_token, "records": records, "detail_records": detail_records},
                    timeout=60,
                )
                ok_days += 1
            except Exception as exc:
                print(f"    [上傳失敗] {stock_id} {d_str}: {exc}")
                fail_days += 1

        print(f"{stock_id} 完成:成功 {ok_days} 天,失敗 {fail_days} 天")

    print("這批全部處理完畢")


if __name__ == "__main__":
    main()
