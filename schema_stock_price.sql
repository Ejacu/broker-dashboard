-- 在 phpMyAdmin 的 SQL 分頁執行這段(記得先在左側選到 sgqvwamy_BROKERDATA 資料庫再執行)
-- 存官方日收盤價(來自 FinMind taiwan_stock_daily),跟分點資料是分開的兩件事。
CREATE TABLE IF NOT EXISTS stock_price_daily (
    stock_id VARCHAR(12) NOT NULL,
    trade_date DATE NOT NULL,
    close_price DECIMAL(12,4) NOT NULL,
    change_val DECIMAL(12,4) NOT NULL,
    change_pct DECIMAL(8,4) NOT NULL,
    PRIMARY KEY (stock_id, trade_date),
    KEY idx_stock (stock_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
