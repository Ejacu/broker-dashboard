"""本機執行用:產生網站的會員/資料覆蓋報告,不用登入 Bluehost phpMyAdmin。

跟 check_completeness.py 用同一套 service_token 機制,打的是後端新增的
report.php(只做 COUNT/GROUP BY 這種彙總查詢,不會像整表匯出那樣逾時)。
"""
import os

import requests

UPLOAD_URL = os.environ.get("UPLOAD_URL", "https://sgq.vwa.mybluehost.me/broker/upload.php")
UPLOAD_TOKEN = os.environ["UPLOAD_TOKEN"]
REPORT_URL = os.environ.get("REPORT_URL", UPLOAD_URL.replace("upload.php", "report.php"))
STOCKS_URL = os.environ.get("STOCKS_URL", UPLOAD_URL.replace("upload.php", "stocks.php"))

# Bluehost 的防護機制會擋掉 requests 預設的 User-Agent(python-requests/x.x),
# 偽裝成一般瀏覽器才不會被 WAF 判定成機器人擋掉(406 Not Acceptable)——跟 daily_update.py 一致
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def main():
    resp = requests.get(REPORT_URL, params={"service_token": UPLOAD_TOKEN}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    r = resp.json()

    print("=" * 40)
    print("SM籌碼 網站報告")
    print("=" * 40)
    print(f"會員總數: {r['total_users']}")
    print(f"  近 7 天新增: {r['new_users_7d']}")
    print(f"  近 30 天新增: {r['new_users_30d']}")
    print(f"  方案分布: {r['users_by_plan']}")
    print()
    print("近 30 天每日新增會員:")
    for row in r["daily_signups_30d"]:
        print(f"  {row['date']}: {row['count']}")
    print()
    print("會員清冊(新到舊):")
    for m in r["members"]:
        print(f"  {m['created_at']}  {m['email']}  ({m['plan']})")
        print(f"      登入次數: {m['login_count']}  上次登入: {m['last_login_at'] or '-'}  最近活躍: {m['last_active_at'] or '-'}")
        print(f"      註冊 IP: {m['signup_ip'] or '-'}  來源: {m['signup_referrer'] or '(無,通常是直接輸入網址或 app 內開啟)'}")

    print()
    stocks_resp = requests.get(STOCKS_URL, headers=HEADERS, timeout=30)
    stocks_resp.raise_for_status()
    print(f"目前追蹤股票數: {len(stocks_resp.json())}")
    print("=" * 40)


if __name__ == "__main__":
    main()
