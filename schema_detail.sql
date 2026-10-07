-- 在 phpMyAdmin 的 SQL 分頁執行這段,新增一張存「各價位明細」的表
CREATE TABLE IF NOT EXISTS broker_price_detail (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    broker VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    buy_lots DECIMAL(12,1) NOT NULL DEFAULT 0,
    sell_lots DECIMAL(12,1) NOT NULL DEFAULT 0,
    UNIQUE KEY uniq_detail (stock_id, trade_date, broker, price),
    KEY idx_stock_date (stock_id, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
