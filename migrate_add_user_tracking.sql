-- 在 phpMyAdmin 的 SQL 分頁執行這段(先選到 sgqvwamy_BROKERDATA 資料庫)
-- users 表只有個位數到十幾筆,這個 ALTER 是瞬間完成的,不會像 broker_summary 那樣逾時。
-- 補上「怎麼找到我們的、登入幾次、上次登入時間」這些之前完全沒記錄的欄位。

ALTER TABLE users
    ADD COLUMN signup_ip VARCHAR(45) NULL,
    ADD COLUMN signup_referrer VARCHAR(500) NULL,
    ADD COLUMN login_count INT UNSIGNED NOT NULL DEFAULT 0,
    ADD COLUMN last_login_at DATETIME NULL;
