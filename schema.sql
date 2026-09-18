-- 在 cPanel -> phpMyAdmin 選好你的資料庫後,貼上這段執行一次即可
CREATE TABLE IF NOT EXISTS broker_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_id VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    broker VARCHAR(100) NOT NULL,
    buy_avg DECIMAL(10,2) NOT NULL DEFAULT 0,
    sell_avg DECIMAL(10,2) NOT NULL DEFAULT 0,
    main_avg DECIMAL(10,2) NOT NULL DEFAULT 0,
    net_lots DECIMAL(12,1) NOT NULL DEFAULT 0,
    total_buy_lots DECIMAL(12,1) NOT NULL DEFAULT 0,
    total_sell_lots DECIMAL(12,1) NOT NULL DEFAULT 0,
    UNIQUE KEY uniq_stock_date_broker (stock_id, trade_date, broker),
    KEY idx_stock (stock_id),
    KEY idx_stock_date (stock_id, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
