-- 在 phpMyAdmin 的 SQL 分頁執行這段(記得先在左側選到 sgqvwamy_BROKERDATA 資料庫再執行)
-- 幫 stock_price_daily 補上開高低量,原本只存了收盤價,畫 K 線圖需要這些欄位
ALTER TABLE stock_price_daily
    ADD COLUMN open_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    ADD COLUMN high_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    ADD COLUMN low_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    ADD COLUMN volume_lots DECIMAL(14,1) NOT NULL DEFAULT 0;
