"""本機執行用:檢查資料庫裡所有股票,最近一段時間有沒有缺交易日。

用 2330(免費試看股,資料來源最穩定)的交易日清單當「正確答案」,
逐一比對其他股票同一段時間內缺哪幾天——國定假日、颱風假這些非交易日,
2330 本身就不會有,所以不用自己維護假日清單,也不會誤判成「缺資料」。
"""
import os

import requests

UPLOAD_URL = os.environ.get("UPLOAD_URL", "https://sgq.vwa.mybluehost.me/broker/upload.php")
UPLOAD_TOKEN = os.environ["UPLOAD_TOKEN"]
STOCKS_URL = os.environ.get("STOCKS_URL", UPLOAD_URL.replace("upload.php", "stocks.php"))
DATES_URL = os.environ.get("DATES_URL", UPLOAD_URL.replace("upload.php", "dates.php"))

# 檢查最近幾天,預設 30 天,想檢查更久以前可以用環境變數覆蓋
CHECK_WINDOW_DAYS = int(os.environ.get("CHECK_WINDOW_DAYS", "30"))


def get_dates(stock_id: str) -> set:
    resp = requests.get(DATES_URL, params={"stock": stock_id, "service_token": UPLOAD_TOKEN}, timeout=30)
    resp.raise_for_status()
    return set(resp.json())


def main():
    stocks = requests.get(STOCKS_URL, params={"service_token": UPLOAD_TOKEN}, timeout=30).json()
    print(f"資料庫目前共 {len(stocks)} 檔股票")

    canonical_all = sorted(get_dates("2330"), reverse=True)
    canonical = set(canonical_all[:CHECK_WINDOW_DAYS])
    if not canonical:
        print("2330 本身沒有資料,無法當基準,中止")
        return
    print(f"以 2330 為交易日基準,檢查範圍: {min(canonical)} ~ {max(canonical)}({len(canonical)} 個交易日)\n")

    complete, incomplete = [], []
    for stock_id in stocks:
        existing = get_dates(stock_id)
        missing = sorted(canonical - existing)
        if missing:
            incomplete.append((stock_id, missing))
        else:
            complete.append(stock_id)

    print(f"完整: {len(complete)} 檔")
    print(f"有缺: {len(incomplete)} 檔\n")
    for stock_id, missing in incomplete:
        print(f"  {stock_id}: 缺 {missing}")


if __name__ == "__main__":
    main()
